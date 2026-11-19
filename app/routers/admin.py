import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import (
    User, Product, Category, Brand,
    Adoption, AdoptionRequest, Appointment, Service, Notification
)
# Ajusta esta importación al nombre de tu dependencia actual que obtiene el usuario del JWT
from app.routers.auth_profile import get_current_user

router = APIRouter(tags=["Admin y Notificaciones"])


# --- DEPENDENCIA DE AUTORIZACIÓN ADMIN ---
async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: se requieren permisos de administrador",
        )
    return current_user


# --- ESQUEMAS PYDANTIC ---
class ProductCreateAdmin(BaseModel):
    nombre: str
    descripcion: Optional[str] = ""
    precio: float
    stock: int = 10
    imagen_url: str
    category_id: int
    brand_id: Optional[int] = None
    atributos: dict = {}


class StockUpdate(BaseModel):
    stock: int


class AdoptionCreateAdmin(BaseModel):
    nombre: str
    especie: str
    raza: str = "Mestizo"
    edad: str
    descripcion: str
    foto_url: str


class AdoptionApprovePayload(BaseModel):
    modalidad_entrega: str  # "sucursal" | "domicilio"
    mensaje_personalizado: str


class AppointmentConfirmPayload(BaseModel):
    mensaje_confirmacion: Optional[str] = None

class AppointmentCancelPayload(BaseModel):
    motivo_cancelacion: Optional[str] = None

class ProductMetaUpdate(BaseModel):
    category_id: Optional[int] = None
    brand_id: Optional[int] = None

class BrandCreateAdmin(BaseModel):
    nombre: str
    logo_url: Optional[str] = None

class ProductUpdateAdmin(BaseModel):
    nombre: str
    descripcion: Optional[str] = ""
    precio: float
    stock: int
    imagen_url: str
    category_id: int
    brand_id: Optional[int] = None
    atributos: dict = {}

class AdoptionUpdateAdmin(BaseModel):
    nombre: str
    especie: str
    raza: str = "Mestizo"
    edad: str
    descripcion: str
    estado: str = "disponible"
    foto_url: str


@router.post("/admin/brands", status_code=201)
async def admin_create_brand(
    payload: BrandCreateAdmin,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    nombre_limpio = payload.nombre.strip()
    if not nombre_limpio:
        raise HTTPException(status_code=400, detail="El nombre de la marca es obligatorio")

    existente = await db.execute(select(Brand).where(Brand.nombre.ilike(nombre_limpio)))
    if existente.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"La marca '{nombre_limpio}' ya está registrada")

    nueva_marca = Brand(
        nombre=nombre_limpio,
        logo_url=payload.logo_url.strip() if payload.logo_url else None,
    )
    db.add(nueva_marca)
    await db.commit()
    await db.refresh(nueva_marca)
    return {"id": nueva_marca.id, "nombre": nueva_marca.nombre, "logo_url": nueva_marca.logo_url}


@router.patch("/admin/products/{product_id}/meta")
async def admin_update_product_meta(
    product_id: str,
    payload: ProductMetaUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    prod = result.scalar_one_or_none()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if payload.category_id is not None:
        prod.category_id = payload.category_id
    prod.brand_id = payload.brand_id
    await db.commit()
    return {"status": "ok"}

# ==========================================
# 1. ENDPOINTS DE NOTIFICACIONES (USUARIO)
# ==========================================
@router.get("/users/me/notifications")
async def get_my_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.creado_en.desc())
    )
    return result.scalars().all()


@router.patch("/users/me/notifications/{notif_id}/read")
async def mark_notification_read(
    notif_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.user_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")

    notif.leida = True
    await db.commit()
    return {"status": "ok"}


# ==========================================
# 2. CATÁLOGO Y RE-STOCK (ADMIN)
# ==========================================
@router.get("/admin/products")
async def admin_list_products(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.category), selectinload(Product.brand))
        .order_by(Product.stock.asc())
    )
    products = result.scalars().all()
    return [
        {
            "id": p.id,
            "nombre": p.nombre,
            "descripcion": p.descripcion or "",
            "precio": p.precio,
            "stock": p.stock,
            "requiere_restock": p.stock <= 5,
            "imagen_url": p.imagen_url,
            "category_id": p.category_id,
            "brand_id": p.brand_id,
            "categoria": p.category.nombre if p.category else "Sin categoría",
            "marca": p.brand.nombre if p.brand else None,
            "atributos": p.atributos or {},
        }
        for p in products
    ]




@router.put("/admin/products/{product_id}")
async def admin_update_product(
    product_id: str,
    payload: ProductUpdateAdmin,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    prod = result.scalar_one_or_none()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    prod.nombre = payload.nombre.strip()
    prod.descripcion = payload.descripcion or ""
    prod.precio = payload.precio
    prod.stock = max(0, payload.stock)
    prod.imagen_url = payload.imagen_url.strip()
    prod.category_id = payload.category_id
    prod.brand_id = payload.brand_id
    prod.atributos = payload.atributos or {}

    await db.commit()
    await db.refresh(prod)
    return {"status": "ok", "id": prod.id}

@router.post("/admin/products", status_code=201)
async def admin_create_product(
    payload: ProductCreateAdmin,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    nuevo = Product(
        id=f"prod-{uuid.uuid4().hex[:8]}",
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        precio=payload.precio,
        stock=payload.stock,
        imagen_url=payload.imagen_url,
        category_id=payload.category_id,
        brand_id=payload.brand_id,
        atributos=payload.atributos,
    )
    db.add(nuevo)
    await db.commit()
    await db.refresh(nuevo)
    return nuevo


@router.patch("/admin/products/{product_id}/stock")
async def admin_update_stock(
    product_id: str,
    payload: StockUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    prod = result.scalar_one_or_none()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    prod.stock = max(0, payload.stock)
    await db.commit()
    return {"id": prod.id, "stock": prod.stock, "requiere_restock": prod.stock <= 5}


@router.get("/admin/catalog-meta")
async def admin_catalog_meta(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    cats = (await db.execute(select(Category))).scalars().all()
    brands = (await db.execute(select(Brand))).scalars().all()
    return {
        "categories": [{"id": c.id, "nombre": c.nombre} for c in cats],
        "brands": [{"id": b.id, "nombre": b.nombre} for b in brands],
    }


# ==========================================
# 3. ADOPCIONES Y SOLICITUDES (ADMIN)
# ==========================================
@router.post("/admin/adoptions", status_code=201)
async def admin_create_adoption(
    payload: AdoptionCreateAdmin,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    nueva_mascota = Adoption(
        nombre=payload.nombre,
        especie=payload.especie,
        raza=payload.raza,
        edad=payload.edad,
        descripcion=payload.descripcion,
        estado="disponible",
        fotos=[payload.foto_url] if payload.foto_url else [],
    )
    db.add(nueva_mascota)
    await db.commit()
    await db.refresh(nueva_mascota)
    return nueva_mascota


@router.get("/admin/adoptions/requests")
async def admin_list_adoption_requests(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(AdoptionRequest)
        .options(
            selectinload(AdoptionRequest.user),
            selectinload(AdoptionRequest.adoption),
        )
        .order_by(AdoptionRequest.fecha.desc())
    )
    reqs = result.scalars().all()
    return [
        {
            "id": r.id,
            "motivo": r.motivo,
            "estado": r.estado,
            "fecha": r.fecha,
            "usuario": {
                "id": r.user.id,
                "nombre": r.user.nombre,
                "email": r.user.email,
                "telefono": r.user.telefono,
            },
            "mascota": {
                "id": r.adoption.id,
                "nombre": r.adoption.nombre,
                "especie": r.adoption.especie,
                "raza": r.adoption.raza,
                "estado": r.adoption.estado,
                "foto": r.adoption.fotos[0] if r.adoption.fotos else None,
            },
        }
        for r in reqs
    ]



@router.get("/admin/adoptions")
async def admin_list_adoptions(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Adoption).order_by(Adoption.id.desc()))
    mascotas = result.scalars().all()
    return [
        {
            "id": m.id,
            "nombre": m.nombre,
            "especie": m.especie,
            "raza": m.raza,
            "edad": m.edad,
            "descripcion": m.descripcion,
            "estado": m.estado,
            "fotos": m.fotos or [],
        }
        for m in mascotas
    ]


@router.put("/admin/adoptions/{adoption_id}")
async def admin_update_adoption(
    adoption_id: int,
    payload: AdoptionUpdateAdmin,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Adoption).where(Adoption.id == adoption_id))
    mascota = result.scalar_one_or_none()
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")

    mascota.nombre = payload.nombre.strip()
    mascota.especie = payload.especie.strip()
    mascota.raza = payload.raza.strip() or "Mestizo"
    mascota.edad = payload.edad.strip()
    mascota.descripcion = payload.descripcion.strip()
    mascota.estado = payload.estado
    if payload.foto_url.strip():
        mascota.fotos = [payload.foto_url.strip()]

    await db.commit()
    await db.refresh(mascota)
    return {"status": "ok", "id": mascota.id}


@router.post("/admin/adoptions/requests/{request_id}/approve")
async def admin_approve_adoption_request(
    request_id: int,
    payload: AdoptionApprovePayload,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(AdoptionRequest)
        .options(selectinload(AdoptionRequest.adoption), selectinload(AdoptionRequest.user))
        .where(AdoptionRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if req.adoption.estado == "adoptado":
        raise HTTPException(status_code=400, detail="Esta mascota ya fue dada en adopción a otro usuario")

    if req.estado != "pendiente":
        raise HTTPException(status_code=400, detail="Esta solicitud ya fue procesada anteriormente")

    # 1. Buscar las otras solicitudes pendientes para esta misma mascota antes de modificar el estado
    otras_res = await db.execute(
        select(AdoptionRequest).where(
            AdoptionRequest.adoption_id == req.adoption_id,
            AdoptionRequest.id != req.id,
            AdoptionRequest.estado == "pendiente",
        )
    )
    otras_solicitudes = otras_res.scalars().all()

    # 2. Aprobar la solicitud elegida y ocultar la mascota del catálogo público
    req.estado = "aprobada"
    req.adoption.estado = "adoptado"

    # 3. Rechazar automáticamente las demás solicitudes y notificar a esos usuarios
    for otra in otras_solicitudes:
        otra.estado = "rechazada"
        db.add(
            Notification(
                user_id=otra.user_id,
                tipo="adopcion",
                titulo=f"Actualización sobre tu solicitud por {req.adoption.nombre}",
                mensaje=f"Agradecemos mucho tu interés en adoptar a {req.adoption.nombre}. En esta ocasión ya fue asignado a otro hogar, pero tenemos más mascotas esperando familia en la sección de Adopciones.",
            )
        )

    # 4. Enviar notificación de aprobación al adoptante seleccionado
    modalidad_txt = (
        "Recolección en sucursal PetMarket"
        if payload.modalidad_entrega == "sucursal"
        else "Entrega coordinada a domicilio"
    )
    db.add(
        Notification(
            user_id=req.user_id,
            tipo="adopcion",
            titulo=f"¡Solicitud aprobada para adoptar a {req.adoption.nombre}!",
            mensaje=f"Modalidad: {modalidad_txt}. {payload.mensaje_personalizado}",
        )
    )

    await db.commit()
    return {"status": "aprobada", "mascota_estado": req.adoption.estado}


# ==========================================
# 4. CITAS SEMANALES E HISTORIAL (ADMIN)
# ==========================================
@router.get("/admin/appointments")
async def admin_list_appointments(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.user), selectinload(Appointment.service))
        .order_by(Appointment.fecha_hora.asc())
    )
    appts = result.scalars().all()

    ahora = datetime.now(timezone.utc)
    inicio_semana = ahora - timedelta(days=ahora.weekday())
    inicio_semana = inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0)
    fin_semana = inicio_semana + timedelta(days=7)

    semanales = []
    historial = []

    for a in appts:
        fecha_cita = a.fecha_hora if a.fecha_hora.tzinfo else a.fecha_hora.replace(tzinfo=timezone.utc)
        item = {
            "id": a.id,
            "nombre_mascota": a.nombre_mascota,
            "fecha_hora": a.fecha_hora,
            "estado": a.estado,
            "servicio": a.service.nombre if a.service else "Servicio",
            "tipo": a.service.tipo if a.service else "estetica",
            "cliente": {
                "id": a.user.id,
                "nombre": a.user.nombre,
                "email": a.user.email,
                "telefono": a.user.telefono,
            },
        }
        if inicio_semana <= fecha_cita <= fin_semana and a.estado != "cancelada":
            semanales.append(item)
        else:
            historial.append(item)

    # Ordenar historial de la más reciente a la más antigua
    historial.sort(key=lambda x: x["fecha_hora"], reverse=True)
    return {"semanales": semanales, "historial": historial}


@router.post("/admin/appointments/{appointment_id}/confirm")
async def admin_confirm_appointment(
    appointment_id: int,
    payload: AppointmentConfirmPayload,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.service))
        .where(Appointment.id == appointment_id)
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    appt.estado = "confirmada"
    fecha_fmt = appt.fecha_hora.strftime("%d/%m/%Y a las %H:%M hrs")
    detalle_extra = f" Nota del equipo: {payload.mensaje_confirmacion}" if payload.mensaje_confirmacion else ""

    notificacion = Notification(
        user_id=appt.user_id,
        tipo="cita",
        titulo=f"Cita confirmada para {appt.nombre_mascota}",
        mensaje=f"Tu cita de {appt.service.nombre} quedó confirmada para el {fecha_fmt}.{detalle_extra}",
    )
    db.add(notificacion)
    await db.commit()
    return {"status": "confirmada"}

@router.post("/admin/appointments/{appointment_id}/cancel")
async def admin_cancel_appointment(
    appointment_id: int,
    payload: AppointmentCancelPayload,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.service))
        .where(Appointment.id == appointment_id)
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    appt.estado = "cancelada"
    fecha_fmt = appt.fecha_hora.strftime("%d/%m/%Y a las %H:%M hrs")
    motivo_txt = (
        payload.motivo_cancelacion
        or "No contamos con disponibilidad en ese horario. Por favor agenda una nueva fecha."
    )

    notificacion = Notification(
        user_id=appt.user_id,
        tipo="cita",
        titulo=f"Cita cancelada para {appt.nombre_mascota}",
        mensaje=f"Tu solicitud de {appt.service.nombre} programada para el {fecha_fmt} fue cancelada. Motivo: {motivo_txt}",
    )
    db.add(notificacion)
    await db.commit()
    return {"status": "cancelada"}