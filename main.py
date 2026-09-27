from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sqlalchemy import text

from app.infraestructure.adaptadores.inbound.rest import (
    controller,
    auth_controller,
)

from app.infraestructure.adaptadores.outbound.persistence.db_conexion import (
    engine,
)

from app.config.settings import (
    UPLOAD_DIR,
)


# ======================================================
# APLICACIÓN
# ======================================================

app = FastAPI(
    title="DataHorse API",
    version="0.1.0",
)


# ======================================================
# CARPETA DE ARCHIVOS / FOTOS
# ======================================================

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

app.mount(
    "/uploads",
    StaticFiles(
        directory=str(UPLOAD_DIR)
    ),
    name="uploads",
)


# ======================================================
# CORS
# ======================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ======================================================
# AUTENTICACIÓN
# ======================================================
#
# Nuevo sistema de autenticación:
#
# /auth/register
# /auth/verify-email
# /auth/resend-code
# /auth/login
# /auth/google
# /auth/forgot-password
# /auth/reset-password
# /auth/me
# /auth/logout
#
# IMPORTANTE:
# NO registramos controller.router porque contiene
# el sistema de autenticación viejo.
# ======================================================

app.include_router(
    auth_controller.router
)


# ======================================================
# RAZAS
# ======================================================
#
# GET /api/v1/razas
# ======================================================

app.include_router(
    controller.razas_router,
    prefix="/api/v1",
)


# ======================================================
# CABALLOS
# ======================================================
#
# POST /api/v1/caballos
#
# Favoritos:
# POST   /api/v1/caballos/{id}/favorito
# DELETE /api/v1/caballos/{id}/favorito
# ======================================================

app.include_router(
    controller.caballos_router,
    prefix="/api/v1",
)


# ======================================================
# PUBLICACIONES
# ======================================================
#
# ESTE ROUTER FALTABA.
#
# El controller ya tiene:
#
# publicaciones_router = APIRouter(
#     prefix="/publicaciones"
# )
#
# Por lo tanto:
#
# GET /publicaciones
#
# ======================================================

app.include_router(
    controller.publicaciones_router
)


# ======================================================
# RUTA PRINCIPAL
# ======================================================

@app.get("/")
def root():

    return {
        "status": "ok",
        "mensaje": "DataHorse API funcionando",
    }


# ======================================================
# PING
# ======================================================

@app.get("/api/v1/ping")
def ping():

    return {
        "mensaje": "Conexión exitosa con FastAPI",
    }


# ======================================================
# PRUEBA BASE DE DATOS
# ======================================================

@app.get("/api/v1/test-db")
def test_database():

    try:

        with engine.connect() as connection:

            connection.execute(
                text("SELECT 1")
            )


        return {
            "status": "ok",
            "mensaje": "Conexión exitosa con MySQL",
            "base_datos": "datahorse2",
        }


    except Exception as e:

        return {
            "status": "error",
            "mensaje": str(e),
        }