import logging
import os
import time
from uuid import uuid4

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
)

from fastapi.exceptions import (
    RequestValidationError,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from fastapi.responses import (
    JSONResponse,
)

from fastapi.staticfiles import (
    StaticFiles,
)

from sqlalchemy import text

from app.domain.exceptions import DominioError

from app.infraestructure.adaptadores.inbound.rest import (
    auth_controller,
    caballo_controller,
    favorito_controller,
    foto_controller,
    log_controller,
    publicacion_controller,
    raza_controller,
)

from app.infraestructure.adaptadores.inbound.rest.errores import (
    estado_http,
)

from app.infraestructure.adaptadores.outbound.persistence.db_conexion import (
    engine,
)

from app.infraestructure.adaptadores.outbound.persistence.technical_log_service import (
    guardar_log_tecnico,
)

from app.config.settings import (
    UPLOAD_DIR,
)

from app.config.logging_config import configurar_logging


# ======================================================
# LOGGING TÉCNICO
# ======================================================

configurar_logging()

logger = logging.getLogger("datahorse")


# ======================================================
# APLICACIÓN
# ======================================================

app = FastAPI(
    title="DataHorse API",
    version="0.1.0",
)


# ======================================================
# LOGGING DE SOLICITUDES HTTP
# ======================================================

@app.middleware("http")
async def registrar_solicitud_http(
    request: Request,
    call_next,
):
    request_id = str(uuid4())
    inicio = time.perf_counter()

    try:
        response = await call_next(request)

        duracion_ms = round(
            (time.perf_counter() - inicio) * 1000,
            2,
        )

        response.headers["X-Request-ID"] = request_id

        mensaje = (
            f"Solicitud HTTP | request_id={request_id} | "
            f"método={request.method} | "
            f"ruta={request.url.path} | "
            f"estado={response.status_code} | "
            f"duración_ms={duracion_ms}"
        )

        logger.info("%s", mensaje)

        guardar_log_tecnico(
            nivel="INFO",
            modulo="http",
            mensaje=mensaje,
            request_id=request_id,
            metodo_http=request.method,
            ruta=request.url.path,
            estado_http=response.status_code,
            duracion_ms=duracion_ms,
        )

        return response

    except Exception:
        duracion_ms = round(
            (time.perf_counter() - inicio) * 1000,
            2,
        )

        mensaje = (
            f"Error durante solicitud HTTP | "
            f"request_id={request_id} | "
            f"método={request.method} | "
            f"ruta={request.url.path} | "
            f"duración_ms={duracion_ms}"
        )

        logger.exception("%s", mensaje)

        guardar_log_tecnico(
            nivel="ERROR",
            modulo="http",
            mensaje=mensaje,
            request_id=request_id,
            metodo_http=request.method,
            ruta=request.url.path,
            duracion_ms=duracion_ms,
            excepcion="Error durante el procesamiento de la solicitud HTTP",
        )

        raise


# ======================================================
# RESPUESTAS EXITOSAS ESTANDARIZADAS
# ======================================================

def success_response(
    data=None,
    message="Operación realizada correctamente",
    status_code=200,
):
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "status": status_code,
            "message": message,
            "data": data,
        },
        media_type="application/json",
    )


# ======================================================
# NORMALIZACIÓN DE ERRORES
# ======================================================

TITULOS_HTTP = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
}


def problem_response(
    request: Request,
    status_code: int,
    detail: str,
):
    return JSONResponse(
        status_code=status_code,
        content={
            "type": "about:blank",
            "title": TITULOS_HTTP.get(
                status_code,
                "Error",
            ),
            "status": status_code,
            "detail": detail,
            "instance": request.url.path,
        },
        media_type="application/problem+json",
    )


# ======================================================
# HTTP EXCEPTION
# ======================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    return problem_response(
        request,
        exc.status_code,
        str(exc.detail),
    )


# ======================================================
# ERRORES DE NEGOCIO
# ======================================================

@app.exception_handler(DominioError)
async def dominio_exception_handler(
    request: Request,
    exc: DominioError,
):
    return problem_response(
        request,
        estado_http(exc),
        exc.mensaje,
    )


# ======================================================
# ERROR DE VALIDACIÓN
# ======================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    errores = exc.errors()

    mensaje = (
        errores[0].get(
            "msg",
            "Datos de entrada inválidos",
        )
        if errores
        else "Datos de entrada inválidos"
    )

    return JSONResponse(
        status_code=422,
        content={
            "type": "about:blank",
            "title": "Unprocessable Entity",
            "status": 422,
            "detail": mensaje,
            "instance": request.url.path,
        },
        media_type="application/problem+json",
    )


# ======================================================
# ERROR INTERNO NO CONTROLADO
# ======================================================

@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Error interno no controlado | método=%s | ruta=%s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "Ocurrió un error interno en el servidor",
            "instance": request.url.path,
        },
        media_type="application/problem+json",
    )


# ======================================================
# ARCHIVOS / FOTOS
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

origenes_permitidos = os.getenv(
    "ALLOWED_ORIGINS",
    "",
).split(",")

origenes_permitidos = [
    origen.strip()
    for origen in origenes_permitidos
    if origen.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origenes_permitidos,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================================================
# AUTENTICACIÓN
# ======================================================

app.include_router(
    auth_controller.router
)


# ======================================================
# RAZAS
# ======================================================

app.include_router(
    raza_controller.router,
    prefix="/api/v1",
)


# ======================================================
# CABALLOS
# ======================================================

# El router de caballos va primero: declara /mios antes que /{id_caballo}.
for router_caballos in (
    caballo_controller.router,
    foto_controller.router,
    favorito_controller.router,
):
    app.include_router(
        router_caballos,
        prefix="/api/v1",
    )


# ======================================================
# PUBLICACIONES
# ======================================================

app.include_router(
    publicacion_controller.router
)


# ======================================================
# LOGS
# ======================================================

app.include_router(
    log_controller.logs_router,
    prefix="/api/v1",
)


# ======================================================
# RUTA PRINCIPAL
# ======================================================

@app.get("/")
def root():
    return success_response(
        message="DataHorse API funcionando correctamente",
        data={
            "service": "DataHorse API",
            "version": "0.1.0",
        },
    )


# ======================================================
# PING
# ======================================================

@app.get("/api/v1/ping")
def ping():
    return success_response(
        message="Conexión exitosa con FastAPI",
        data={
            "status": "ok",
        },
    )


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

        return success_response(
            message="Conexión exitosa con MySQL",
            data={
                "status": "ok",
                "base_datos": "datahorse2",
            },
        )

    except Exception:
        logger.exception(
            "Falló la comprobación de conexión con MySQL"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "No fue posible conectar "
                "con la base de datos"
            ),
        )
