from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/orders", tags=["Órdenes"])

@router.post("", response_model=schemas.OrderOut)
async def create_order(
    data: schemas.OrderCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not data.items:
        raise HTTPException(status_code=400, detail="El carrito está vacío")

    total = 0.0
    order_items = []

    for item in data.items:
        result = await db.execute(select(models.Product).where(models.Product.id == item.product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail=f"Producto {item.product_id} no encontrado")
        if product.stock < item.cantidad:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para {product.nombre}")

        # Descuento de inventario y cálculo de total desde el backend
        product.stock -= item.cantidad
        total += product.precio * item.cantidad
        order_items.append(
            models.OrderItem(
                product_id=product.id,
                precio_comprado=product.precio,
                cantidad=item.cantidad,
            )
        )

    order = models.Order(
        user_id=current_user.id,
        address_id=data.address_id,
        total=total,
        items=order_items,
    )
    db.add(order)
    await db.commit()

    # Recargamos la orden con sus relaciones para devolverla completa
    query = (
        select(models.Order)
        .options(
            selectinload(models.Order.items)
            .selectinload(models.OrderItem.product)
            .selectinload(models.Product.category),
            selectinload(models.Order.items)
            .selectinload(models.OrderItem.product)
            .selectinload(models.Product.brand),
        )
        .where(models.Order.id == order.id)
    )
    saved_order = await db.execute(query)
    return saved_order.scalar_one()

@router.get("", response_model=list[schemas.OrderOut])
async def get_order_history(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(models.Order)
        .options(
            selectinload(models.Order.items)
            .selectinload(models.OrderItem.product)
            .selectinload(models.Product.category),
            selectinload(models.Order.items)
            .selectinload(models.OrderItem.product)
            .selectinload(models.Product.brand),
        )
        .where(models.Order.user_id == current_user.id)
        .order_by(models.Order.fecha.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()