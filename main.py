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


# ======================================================
# HTTP EXCEPTION
# ======================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "about:blank",
            "title": TITULOS_HTTP.get(
                exc.status_code,
                "Error",
            ),
            "status": exc.status_code,
            "detail": str(exc.detail),
            "instance": request.url.path,
        },
        media_type="application/problem+json",
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

    print(
        "ERROR NO CONTROLADO:",
        repr(exc),
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

app.include_router(
    auth_controller.router
)


# ======================================================
# RAZAS
# ======================================================

app.include_router(
    controller.razas_router,
    prefix="/api/v1",
)


# ======================================================
# CABALLOS
# ======================================================

app.include_router(
    controller.caballos_router,
    prefix="/api/v1",
)


# ======================================================
# PUBLICACIONES
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

        raise HTTPException(
            status_code=500,
            detail=(
                "No fue posible conectar "
                "con la base de datos"
            ),
        )