from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, ConfigDict

# --- AUTH & USUARIOS ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    nombre: str
    telefono: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    nombre: str
    telefono: Optional[str] = None
    rol: str
    model_config = ConfigDict(from_attributes=True)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class AddressCreate(BaseModel):
    calle: str
    ciudad: str
    estado: str
    cp: str
    es_predeterminada: bool = False

class AddressOut(AddressCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class PaymentMethodCreate(BaseModel):
    stripe_payment_id: str
    ultimos_4_digitos: str
    marca: str

class PaymentMethodOut(PaymentMethodCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

# --- CATÁLOGO ---
class CategoryOut(BaseModel):
    id: int
    nombre: str
    slug: str
    parent_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class BrandOut(BaseModel):
    id: int
    nombre: str
    model_config = ConfigDict(from_attributes=True)

class ProductOut(BaseModel):
    id: str
    nombre: str
    descripcion: Optional[str] = None
    precio: float
    stock: int
    imagen_url: str
    atributos: dict[str, Any]
    category: CategoryOut
    brand: Optional[BrandOut] = None
    model_config = ConfigDict(from_attributes=True)

# --- ÓRDENES ---
class OrderItemCreate(BaseModel):
    product_id: str
    cantidad: int

class OrderCreate(BaseModel):
    address_id: Optional[int] = None
    items: list[OrderItemCreate]

class OrderItemOut(BaseModel):
    id: int
    product_id: str
    precio_comprado: float
    cantidad: int
    product: ProductOut
    model_config = ConfigDict(from_attributes=True)

class OrderOut(BaseModel):
    id: int
    total: float
    estado: str
    fecha: datetime
    items: list[OrderItemOut]
    model_config = ConfigDict(from_attributes=True)

# --- SERVICIOS Y CITAS ---
class ServiceOut(BaseModel):
    id: int
    tipo: str
    nombre: str
    descripcion: Optional[str] = None
    precio: float
    duracion_minutos: int
    model_config = ConfigDict(from_attributes=True)

class AppointmentCreate(BaseModel):
    service_id: int
    nombre_mascota: str
    fecha_hora: datetime

class AppointmentOut(BaseModel):
    id: int
    nombre_mascota: str
    fecha_hora: datetime
    estado: str
    service: ServiceOut
    model_config = ConfigDict(from_attributes=True)

# --- ADOPCIONES ---
class AdoptionOut(BaseModel):
    id: int
    nombre: str
    especie: str
    raza: str
    edad: str
    descripcion: str
    estado: str
    fotos: list[str]
    model_config = ConfigDict(from_attributes=True)

class AdoptionRequestCreate(BaseModel):
    motivo: str

class AdoptionRequestOut(BaseModel):
    id: int
    adoption_id: int
    motivo: str
    estado: str
    fecha: datetime
    adoption: AdoptionOut
    model_config = ConfigDict(from_attributes=True)