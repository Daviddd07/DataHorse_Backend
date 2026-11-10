import logging
import os
import time
from contextlib import asynccontextmanager
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

from starlette.concurrency import run_in_threadpool

from app.domain.exceptions import DominioError

from app.application.use_cases.admin_inicial_use_case import DatosAdminInicial

from app.config.dependencies import get_crear_admin_inicial_use_case

from app.config.validar_configuracion import validar_configuracion

from app.infraestructure.adaptadores.inbound.rest import (
    admin_controller,
    auth_controller,
    caballo_controller,
    compatibilidad_controller,
    conversacion_controller,
    cuenta_controller,
    documento_controller,
    favorito_controller,
    foto_controller,
    log_controller,
    publicacion_controller,
    raza_controller,
    usuario_publico_controller,
)

from app.infraestructure.adaptadores.inbound.rest.errores import (
    estado_http,
)

from app.infraestructure.adaptadores.inbound.websocket import (
    conversacion_ws,
    notificaciones_ws,
)

from app.infraestructure.adaptadores.outbound.persistence.db_conexion import (
    engine,
)

from app.infraestructure.adaptadores.outbound.persistence.technical_log_service import (
    guardar_log_tecnico,
)

from app.config.settings import (
    ORIGENES_PERMITIDOS,
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

# ======================================================
# PRIMER ADMINISTRADOR (desde el .env)
# ======================================================

def crear_admin_inicial() -> None:
    """Crea el admin de ADMIN_CORREO / ADMIN_CONTRASENA si aún no existe.

    Sin esas variables no hace nada. Un fallo aquí (datos inválidos, base
    caída) se registra en el log pero no impide que la API arranque.
    """
    correo = os.getenv("ADMIN_CORREO", "").strip()
    contrasena = os.getenv("ADMIN_CONTRASENA", "")

    if not correo or not contrasena:
        logger.info("Admin inicial omitido: ADMIN_CORREO / ADMIN_CONTRASENA no están definidos")
        return

    try:
        creado = get_crear_admin_inicial_use_case().ejecutar(
            DatosAdminInicial(
                correo=correo,
                contrasena=contrasena,
                nombre=os.getenv("ADMIN_NOMBRE", "Administrador"),
            )
        )
    except DominioError as e:
        logger.error("Admin inicial no creado: %s", e.mensaje)
        return
    except Exception:
        logger.exception("Admin inicial no creado: error inesperado")
        return

    if creado:
        logger.info("Admin inicial creado | id_usuario=%s | correo=%s", creado.id_usuario, creado.correo)
    else:
        logger.info("Admin inicial ya existe | correo=%s", correo.lower())


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    # Primero: sin secretos válidos la API no debe arrancar
    validar_configuracion()
    crear_admin_inicial()
    yield


app = FastAPI(
    title="DataHorse API",
    version="0.1.0",
    lifespan=ciclo_de_vida,
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

        # La escritura en MySQL es síncrona: en un hilo aparte para no congelar
        # el servidor (este middleware es async y corre en el bucle de eventos).
        await run_in_threadpool(
            guardar_log_tecnico,
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

        await run_in_threadpool(
            guardar_log_tecnico,
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
] or ORIGENES_PERMITIDOS  # sin ALLOWED_ORIGINS en el .env se usan los de settings.py

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
    documento_controller.router,
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
# MI CUENTA
# ======================================================

app.include_router(
    cuenta_controller.router,
    prefix="/api/v1",
)


# ======================================================
# ADMINISTRACIÓN
# ======================================================

app.include_router(
    admin_controller.router,
    prefix="/api/v1",
)


# ======================================================
# COMPATIBILIDAD (IA)
# ======================================================

app.include_router(
    compatibilidad_controller.router,
    prefix="/api/v1",
)


# ======================================================
# CONVERSACIONES (REST + WebSocket en tiempo real)
# ======================================================

app.include_router(
    conversacion_controller.router,
    prefix="/api/v1",
)

# Estrellas (reseñas) de cualquier usuario, para mostrarlas en chat y publicaciones
app.include_router(
    usuario_publico_controller.router,
    prefix="/api/v1",
)

app.include_router(
    conversacion_ws.router
)

app.include_router(
    notificaciones_ws.router
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
