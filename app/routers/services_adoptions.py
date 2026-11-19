from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

# Zona horaria de México para comparar correctamente la hora actual con la cita
MX_TZ = ZoneInfo("America/Mexico_City")

# Cupo máximo de citas activas por día según el tipo de servicio
DAILY_LIMITS_BY_TYPE: dict[str, int] = {
    "estetica": 3,
    "veterinaria": 7,
    "adiestramiento": 5,
}

router = APIRouter(tags=["Servicios y Adopciones"])


# ==========================================
# 1. SERVICIOS Y DISPONIBILIDAD
# ==========================================
@router.get("/services", response_model=list[schemas.ServiceOut])
async def list_services(tipo: str | None = None, db: AsyncSession = Depends(get_db)):
    query = select(models.Service)
    if tipo:
        query = query.where(models.Service.tipo == tipo.lower())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/services/availability")
async def get_service_availability(
    tipo: str = Query(..., description="estetica, veterinaria o adiestramiento"),
    year: int = Query(..., ge=2024, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
):
    tipo_norm = tipo.strip().lower()
    limite = DAILY_LIMITS_BY_TYPE.get(tipo_norm, 5)

    # Rango completo del mes consultado
    inicio_mes = datetime(year, month, 1, 0, 0, 0, tzinfo=MX_TZ)
    if month == 12:
        fin_mes = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=MX_TZ)
    else:
        fin_mes = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=MX_TZ)

    # Consultar todas las citas no canceladas de esa categoría en el mes
    result = await db.execute(
        select(models.Appointment.fecha_hora)
        .join(models.Service, models.Appointment.service_id == models.Service.id)
        .where(
            func.lower(models.Service.tipo) == tipo_norm,
            models.Appointment.estado != "cancelada",
            models.Appointment.fecha_hora >= inicio_mes,
            models.Appointment.fecha_hora < fin_mes,
        )
    )
    fechas = result.scalars().all()

    # Contar cuántas citas hay por cada día (YYYY-MM-DD)
    conteo_por_dia: dict[str, int] = {}
    for fh in fechas:
        fh_mx = fh.replace(tzinfo=MX_TZ) if fh.tzinfo is None else fh.astimezone(MX_TZ)
        dia_str = fh_mx.strftime("%Y-%m-%d")
        conteo_por_dia[dia_str] = conteo_por_dia.get(dia_str, 0) + 1

    dias = {}
    for dia_str, ocupadas in conteo_por_dia.items():
        dias[dia_str] = {
            "ocupadas": ocupadas,
            "disponibles": max(0, limite - ocupadas),
            "lleno": ocupadas >= limite,
        }

    return {
        "tipo": tipo_norm,
        "limite_diario": limite,
        "dias": dias,
    }


# ==========================================
# 2. RESERVA Y CONSULTA DE CITAS
# ==========================================
@router.post("/appointments", response_model=schemas.AppointmentOut)
async def book_appointment(
    data: schemas.AppointmentCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Paso 1: Validar que la fecha y hora elegidas sean posteriores a este momento
    ahora_mx = datetime.now(MX_TZ)
    if data.fecha_hora.tzinfo is None:
        fecha_mx = data.fecha_hora.replace(tzinfo=MX_TZ)
    else:
        fecha_mx = data.fecha_hora.astimezone(MX_TZ)

    if fecha_mx <= ahora_mx:
        raise HTTPException(
            status_code=400,
            detail="No puedes agendar una cita en una fecha u hora que ya pasó.",
        )

    # Paso 2: Buscar el servicio para conocer su categoría y su cupo máximo diario
    service_res = await db.execute(
        select(models.Service).where(models.Service.id == data.service_id)
    )
    service = service_res.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    tipo_norm = service.tipo.strip().lower()
    limite_diario = DAILY_LIMITS_BY_TYPE.get(tipo_norm, 5)

    # Paso 3: Contar cuántas citas activas (no canceladas) existen ese día en esa categoría
    inicio_dia = fecha_mx.replace(hour=0, minute=0, second=0, microsecond=0)
    fin_dia = inicio_dia + timedelta(days=1)

    count_res = await db.execute(
        select(func.count(models.Appointment.id))
        .join(models.Service, models.Appointment.service_id == models.Service.id)
        .where(
            func.lower(models.Service.tipo) == tipo_norm,
            models.Appointment.estado != "cancelada",
            models.Appointment.fecha_hora >= inicio_dia,
            models.Appointment.fecha_hora < fin_dia,
        )
    )
    citas_ocupadas = count_res.scalar() or 0

    if citas_ocupadas >= limite_diario:
        raise HTTPException(
            status_code=400,
            detail=f"Cupo lleno para {service.tipo} en esta fecha (máximo {limite_diario} citas por día). Por favor elige otro día.",
        )

    # Paso 4: Guardar la cita y devolverla con la relación `service` cargada
    appointment = models.Appointment(
        user_id=current_user.id,
        service_id=data.service_id,
        nombre_mascota=data.nombre_mascota.strip(),
        fecha_hora=fecha_mx,
    )
    db.add(appointment)
    await db.commit()

    query = (
        select(models.Appointment)
        .options(selectinload(models.Appointment.service))
        .where(models.Appointment.id == appointment.id)
    )
    result = await db.execute(query)
    return result.scalar_one()


@router.get("/appointments", response_model=list[schemas.AppointmentOut])
async def my_appointments(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(models.Appointment)
        .options(selectinload(models.Appointment.service))
        .where(models.Appointment.user_id == current_user.id)
        .order_by(models.Appointment.fecha_hora.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()


# ==========================================
# 3. ADOPCIONES
# ==========================================
@router.get("/adoptions", response_model=list[schemas.AdoptionOut])
async def list_adoptions(especie: str | None = None, db: AsyncSession = Depends(get_db)):
    query = select(models.Adoption).where(models.Adoption.estado == "disponible")
    if especie:
        query = query.where(models.Adoption.especie.ilike(especie))
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/adoptions/{adoption_id}/apply", response_model=schemas.AdoptionRequestOut)
async def apply_adoption(
    adoption_id: int,
    data: schemas.AdoptionRequestCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pet_res = await db.execute(
        select(models.Adoption).where(models.Adoption.id == adoption_id)
    )
    pet = pet_res.scalar_one_or_none()
    if not pet or pet.estado != "disponible":
        raise HTTPException(
            status_code=400, detail="La mascota no está disponible para adopción"
        )

    req = models.AdoptionRequest(
        user_id=current_user.id,
        adoption_id=adoption_id,
        motivo=data.motivo,
    )
    db.add(req)
    await db.commit()

    query = (
        select(models.AdoptionRequest)
        .options(selectinload(models.AdoptionRequest.adoption))
        .where(models.AdoptionRequest.id == req.id)
    )
    result = await db.execute(query)
    return result.scalar_one()