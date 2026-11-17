from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(tags=["Servicios y Adopciones"])

# --- SERVICIOS Y CITAS ---
@router.get("/services", response_model=list[schemas.ServiceOut])
async def list_services(tipo: str | None = None, db: AsyncSession = Depends(get_db)):
    query = select(models.Service)
    if tipo:
        query = query.where(models.Service.tipo == tipo.lower())
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/appointments", response_model=schemas.AppointmentOut)
async def book_appointment(
    data: schemas.AppointmentCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    appointment = models.Appointment(user_id=current_user.id, **data.model_dump())
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

# --- ADOPCIONES ---
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
    pet_res = await db.execute(select(models.Adoption).where(models.Adoption.id == adoption_id))
    pet = pet_res.scalar_one_or_none()
    if not pet or pet.estado != "disponible":
        raise HTTPException(status_code=400, detail="La mascota no está disponible para adopción")

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