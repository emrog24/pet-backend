from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app import models, schemas
from app.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(tags=["Auth & Perfil"])

@router.post("/auth/signup", response_model=schemas.TokenOut, status_code=status.HTTP_201_CREATED)
async def signup(data: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(models.User).where(models.User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    user = models.User(
        email=data.email,
        password_hash=hash_password(data.password),
        nombre=data.nombre,
        telefono=data.telefono,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return {"access_token": token, "user": user}

@router.post("/auth/login", response_model=schemas.TokenOut)
async def login(data: schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    token = create_access_token(user.id)
    return {"access_token": token, "user": user}

@router.get("/users/me", response_model=schemas.UserOut)
async def get_profile(current_user: models.User = Depends(get_current_user)):
    return current_user

# --- DIRECCIONES ---
@router.get("/users/me/addresses", response_model=list[schemas.AddressOut])
async def list_addresses(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(models.Address).where(models.Address.user_id == current_user.id))
    return result.scalars().all()

@router.post("/users/me/addresses", response_model=schemas.AddressOut)
async def add_address(
    data: schemas.AddressCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    address = models.Address(user_id=current_user.id, **data.model_dump())
    db.add(address)
    await db.commit()
    await db.refresh(address)
    return address

# --- MÉTODOS DE PAGO ---
@router.get("/users/me/payments", response_model=list[schemas.PaymentMethodOut])
async def list_payments(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(models.PaymentMethod).where(models.PaymentMethod.user_id == current_user.id))
    return result.scalars().all()

@router.post("/users/me/payments", response_model=schemas.PaymentMethodOut)
async def add_payment(
    data: schemas.PaymentMethodCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payment = models.PaymentMethod(user_id=current_user.id, **data.model_dump())
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment

# --- FAVORITOS ---
@router.get("/users/me/favorites", response_model=list[schemas.ProductOut])
async def list_favorites(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(models.Product)
        .join(models.Favorite)
        .options(selectinload(models.Product.category), selectinload(models.Product.brand))
        .where(models.Favorite.user_id == current_user.id)
    )
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/users/me/favorites/{product_id}")
async def toggle_favorite(
    product_id: str,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(models.Favorite).where(
            models.Favorite.user_id == current_user.id,
            models.Favorite.product_id == product_id,
        )
    )
    fav = existing.scalar_one_or_none()
    if fav:
        await db.delete(fav)
        await db.commit()
        return {"status": "removed"}

    db.add(models.Favorite(user_id=current_user.id, product_id=product_id))
    await db.commit()
    return {"status": "added"}