from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.database import engine, Base, get_db
from app import models, schemas
from app.routers import auth_profile, orders, services_adoptions

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="PetMarket API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montamos los routers modulares
app.include_router(auth_profile.router)
app.include_router(orders.router)
app.include_router(services_adoptions.router)

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT 1"))
    return {"database": "connected", "result": result.scalar()}

@app.post("/seed")
async def seed_database(db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(models.Product).limit(1))
    if existing.scalar_one_or_none():
        return {"message": "La base de datos ya contiene datos iniciales"}

    # 1. Categorías y Subcategorías
    cat_animales = models.Category(nombre="Animales", slug="animales")
    db.add(cat_animales)
    await db.flush()

    cat_perros = models.Category(nombre="Perros", slug="perros", parent_id=cat_animales.id)
    cat_gatos = models.Category(nombre="Gatos", slug="gatos", parent_id=cat_animales.id)
    cat_aves = models.Category(nombre="Aves", slug="aves", parent_id=cat_animales.id)
    cat_reptiles = models.Category(nombre="Reptiles", slug="reptiles", parent_id=cat_animales.id)
    cat_farmacia = models.Category(nombre="Farmacia", slug="farmacia")
    db.add_all([cat_perros, cat_gatos, cat_aves, cat_reptiles, cat_farmacia])
    await db.flush()

    # 2. Marcas
    brand_proplan = models.Brand(nombre="ProPlan")
    brand_nexgard = models.Brand(nombre="NexGard")
    brand_kong = models.Brand(nombre="KONG")
    db.add_all([brand_proplan, brand_nexgard, brand_kong])
    await db.flush()

    # 3. Productos
    productos = [
        models.Product(
            id="prod-1",
            nombre="Croquetas ProPlan Adulto Raza Mediana 13kg",
            descripcion="Alimento super premium formulado por veterinarios con carne fresca de pollo.",
            precio=1450.00,
            stock=25,
            imagen_url="https://placehold.co/600x600/e2e8f0/475569?text=Croquetas+ProPlan",
            atributos={"peso": "13kg", "sabor": "Pollo", "etapa": "Adulto"},
            category_id=cat_perros.id,
            brand_id=brand_proplan.id,
        ),
        models.Product(
            id="prod-2",
            nombre="Arena Scoop Away Multigato 19kg",
            descripcion="Arena aglutinante con control de olores garantizado por 7 días.",
            precio=520.50,
            stock=40,
            imagen_url="https://placehold.co/600x600/e2e8f0/475569?text=Arena+Gatos",
            atributos={"peso": "19kg", "aroma": "Fresco", "aglutinante": True},
            category_id=cat_gatos.id,
        ),
        models.Product(
            id="prod-3",
            nombre="NexGard Spectra Antipulgas 10-25kg",
            descripcion="Tableta masticable sabor a carne contra pulgas, garrapatas y parásitos.",
            precio=485.00,
            stock=15,
            imagen_url="https://placehold.co/600x600/e2e8f0/475569?text=NexGard",
            atributos={"dosis_peso": "10-25kg", "requiere_receta": False, "duracion_dias": 30},
            category_id=cat_farmacia.id,
            brand_id=brand_nexgard.id,
        ),
        models.Product(
            id="prod-4",
            nombre="Juguete KONG Classic Interactivo Talla L",
            descripcion="Hecho de goma natural ultra resistente para masticación intensa.",
            precio=350.00,
            stock=30,
            imagen_url="https://placehold.co/600x600/e2e8f0/475569?text=KONG",
            atributos={"talla": "L", "material": "Caucho natural", "rellenable": True},
            category_id=cat_perros.id,
            brand_id=brand_kong.id,
        ),
    ]

    # 4. Servicios
    servicios = [
        models.Service(tipo="veterinaria", nombre="Consulta General y Vacunación", descripcion="Revisión física completa y esquema de vacunación.", precio=450.00, duracion_minutos=45),
        models.Service(tipo="estetica", nombre="Baño, Corte y Limpieza Dental", descripcion="Estética completa con shampoo hipoalergénico.", precio=380.00, duracion_minutos=90),
        models.Service(tipo="adiestramiento", nombre="Sesión de Obediencia Básica", descripcion="Entrenamiento en positivo para cachorros y adultos.", precio=500.00, duracion_minutos=60),
    ]

    # 5. Mascotas en Adopción
    adopciones = [
        models.Adoption(
            nombre="Max",
            especie="Perro",
            raza="Labrador Mestizo",
            edad="2 años",
            descripcion="Juguetón, vacunado y esterilizado. Ideal para familias activas.",
            fotos=["https://placehold.co/600x600/e2e8f0/475569?text=Max+Adopcion"],
        ),
        models.Adoption(
            nombre="Luna",
            especie="Gato",
            raza="Doméstico Pelo Corto",
            edad="8 meses",
            descripcion="Cariñosa, tranquila y acostumbrada a usar arenero.",
            fotos=["https://placehold.co/600x600/e2e8f0/475569?text=Luna+Adopcion"],
        ),
    ]

    db.add_all(productos + servicios + adopciones)
    await db.commit()
    return {"message": "Catálogo, servicios y adopciones cargados en PostgreSQL"}

@app.get("/categories", response_model=list[schemas.CategoryOut])
async def get_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Category))
    return result.scalars().all()

@app.get("/products", response_model=list[schemas.ProductOut])
async def get_products(categoria: str | None = None, db: AsyncSession = Depends(get_db)):
    query = select(models.Product).options(
        selectinload(models.Product.category),
        selectinload(models.Product.brand),
    )
    if categoria:
        query = query.join(models.Category).where(models.Category.slug == categoria.lower())

    result = await db.execute(query)
    return result.scalars().all()

@app.get("/products/{product_id}", response_model=schemas.ProductOut)
async def get_product(product_id: str, db: AsyncSession = Depends(get_db)):
    query = (
        select(models.Product)
        .options(selectinload(models.Product.category), selectinload(models.Product.brand))
        .where(models.Product.id == product_id)
    )
    result = await db.execute(query)
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product