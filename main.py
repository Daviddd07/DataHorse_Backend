from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.infraestructure.adaptadores.inbound.rest import controller
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import engine


app = FastAPI(title="DataHorse API")


# Permitir conexión con Angular
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rutas de autenticación
app.include_router(controller.router)


@app.get("/")
def root():
    return {
        "status": "ok",
        "mensaje": "DataHorse API funcionando"
    }


@app.get("/api/v1/ping")
def ping():
    return {
        "mensaje": "Conexión exitosa con FastAPI"
    }


@app.get("/api/v1/test-db")
def test_database():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "ok",
            "mensaje": "Conexión exitosa con MySQL",
            "base_datos": "datahorse2"
        }

    except Exception as e:
        return {
            "status": "error",
            "mensaje": str(e)
        }