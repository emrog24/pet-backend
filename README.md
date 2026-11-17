# PetMarket — Backend API

API REST asíncrona para la plataforma de comercio electrónico, servicios veterinarios/grooming y adopciones **PetMarket**. Construida con **FastAPI**, **SQLAlchemy 2.0** y **PostgreSQL 16**.

---

## Tecnologías y Herramientas Utilizadas

* **Lenguaje:** Python 3.10+
* **Framework Web:** FastAPI + Uvicorn (servidor ASGI)
* **Base de Datos:** PostgreSQL 16 (con soporte nativo para columnas `JSONB`)
* **ORM y Driver Asíncrono:** SQLAlchemy 2.0 (`asyncio`) + `asyncpg`
* **Validación de Esquemas:** Pydantic v2
* **Seguridad y Autenticación:** JWT (JSON Web Tokens) + cifrado de contraseñas con `bcrypt`
* **Contenedores:** Docker y Docker Compose

---

## Prerrequisitos (Qué necesitas descargar)

Para ejecutar este proyecto en local necesitas tener instalados:
1. **Git** (para clonar el repositorio).
2. **Python 3.10 o superior**, `pip` y el módulo de entornos virtuales (`venv`).
3. **Docker Engine y Docker Compose** (para levantar la base de datos PostgreSQL 16).
4. **curl** (opcional, para ejecutar la carga inicial de datos desde terminal).

---

## Cómo verificar si ya tienes las herramientas instaladas

Abre una terminal y ejecuta los siguientes comandos:

```bash
git --version
python3 --version
python3 -m venv --help > /dev/null && echo "venv OK"
docker --version
docker compose version
```

* Si cada comando devuelve un número de versión (o `venv OK`), ya cuentas con todo lo necesario y puedes pasar directo a la sección **Cómo correr el proyecto**.
* Si alguno muestra `command not found` o un error, sigue los pasos de instalación a continuación.

---

## Cómo descargar e instalar los prerrequisitos

### En Ubuntu / Debian
1. Actualiza los paquetes del sistema e instala **Git**, **Python**, **pip**, **venv** y **curl**:
   ```bash
   sudo apt update
   sudo apt install -y git python3 python3-pip python3-venv curl
   ```

2. Instala **Docker** y **Docker Compose**:
   ```bash
   sudo apt install -y docker.io docker-compose-v2
   sudo systemctl enable --now docker
   sudo usermod -aG docker $USER
   ```
   > **Nota:** Cierra tu sesión de usuario y vuelve a iniciarla (o ejecuta `newgrp docker`) para poder correr comandos `docker` sin `sudo`.

### En Windows o macOS
* **Git:** Descárgalo desde [git-scm.com](https://git-scm.com/).
* **Python 3.10+:** Descárgalo desde [python.org](https://www.python.org/downloads/) (en Windows, marca la casilla *"Add Python to PATH"* durante la instalación).
* **Docker Desktop:** Descárgalo e instálalo desde [docker.com](https://www.docker.com/products/docker-desktop/).

---

## Cómo correr el proyecto

### 1. Clonar el repositorio
```bash
git clone https://github.com/emrog24/pet-backend
cd pet-backend
```

### 2. Crear y activar el entorno virtual e instalar dependencias
```bash
python3 -m venv venv
source venv/bin/activate        # En Windows PowerShell: .\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
Crea tu archivo `.env` a partir de la plantilla `.env.example`:
```bash
cp .env.example .env
```

Verifica que contenga las siguientes variables:
```env
DATABASE_URL=postgresql+asyncpg://pet_admin:pet_password_123@localhost:5433/petmarket_db
SECRET_KEY=cambia_esta_clave_secreta_en_produccion
FRONTEND_URL=http://localhost:3000
```

### 4. Levantar la base de datos PostgreSQL con Docker
```bash
docker compose up -d
```
Puedes comprobar que el contenedor está activo ejecutando `docker ps` (debe aparecer `petmarket_postgres` escuchando en el puerto `5433`).

### 5. Iniciar el servidor de FastAPI
Con el entorno virtual `(venv)` activo, ejecuta:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Al arrancar por primera vez, SQLAlchemy creará automáticamente las 13 tablas en PostgreSQL.

### 6. Poblar la base de datos (Seed inicial)
En una **segunda terminal**, ejecuta el endpoint `/seed` para insertar las categorías, marcas, productos, servicios y mascotas en adopción:
```bash
curl -X POST http://localhost:8000/seed
```

La API quedará disponible en `http://localhost:8000` y su documentación interactiva (Swagger UI) en `http://localhost:8000/docs`.
