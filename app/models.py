from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

# --- MÓDULO DE USUARIOS Y PERFIL ---

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    telefono: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    rol: Mapped[str] = mapped_column(String(20), default="cliente")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    addresses: Mapped[list["Address"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    payment_methods: Mapped[list["PaymentMethod"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="user")
    adoption_requests: Mapped[list["AdoptionRequest"]] = relationship(back_populates="user")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")

class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    calle: Mapped[str] = mapped_column(String(200), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(100), nullable=False)
    estado: Mapped[str] = mapped_column(String(100), nullable=False)
    cp: Mapped[str] = mapped_column(String(10), nullable=False)
    es_predeterminada: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="addresses")

class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    stripe_payment_id: Mapped[str] = mapped_column(String(100), nullable=False)
    ultimos_4_digitos: Mapped[str] = mapped_column(String(4), nullable=False)
    marca: Mapped[str] = mapped_column(String(30), nullable=False)

    user: Mapped["User"] = relationship(back_populates="payment_methods")

# --- MÓDULO DE CATÁLOGO ---

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)

    products: Mapped[list["Product"]] = relationship(back_populates="category")

class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    products: Mapped[list["Product"]] = relationship(back_populates="brand")

class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    precio: Mapped[float] = mapped_column(Float, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=10)
    imagen_url: Mapped[str] = mapped_column(String(500), nullable=False)
    atributos: Mapped[dict] = mapped_column(JSONB, default=dict)

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    brand_id: Mapped[Optional[int]] = mapped_column(ForeignKey("brands.id"), nullable=True)

    category: Mapped["Category"] = relationship(back_populates="products")
    brand: Mapped[Optional["Brand"]] = relationship(back_populates="products")

class Favorite(Base):
    __tablename__ = "favorites"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), primary_key=True)

    user: Mapped["User"] = relationship(back_populates="favorites")
    product: Mapped["Product"] = relationship()

# --- MÓDULO DE ÓRDENES Y VENTAS ---

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    address_id: Mapped[Optional[int]] = mapped_column(ForeignKey("addresses.id"), nullable=True)
    total: Mapped[float] = mapped_column(Float, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), default="pagado")
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), nullable=False)
    precio_comprado: Mapped[float] = mapped_column(Float, nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()

# --- MÓDULO DE SERVICIOS Y CITAS ---

class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipo: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # veterinaria, estetica, adiestramiento
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    precio: Mapped[float] = mapped_column(Float, nullable=False)
    duracion_minutos: Mapped[int] = mapped_column(Integer, default=60)

class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)
    nombre_mascota: Mapped[str] = mapped_column(String(100), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), default="agendada")

    user: Mapped["User"] = relationship(back_populates="appointments")
    service: Mapped["Service"] = relationship()

# --- MÓDULO DE ADOPCIONES ---

class Adoption(Base):
    __tablename__ = "adoptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    especie: Mapped[str] = mapped_column(String(50), nullable=False)
    raza: Mapped[str] = mapped_column(String(100), default="Mestizo")
    edad: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), default="disponible")  # disponible, en_proceso, adoptado
    fotos: Mapped[list] = mapped_column(JSONB, default=list)

class AdoptionRequest(Base):
    __tablename__ = "adoption_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    adoption_id: Mapped[int] = mapped_column(ForeignKey("adoptions.id"), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), default="pendiente")
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="adoption_requests")
    adoption: Mapped["Adoption"] = relationship()

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), default="sistema")
    leida: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="notifications")