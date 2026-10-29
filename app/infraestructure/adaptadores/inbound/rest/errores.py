"""Traducción de errores de negocio a respuestas HTTP (solo vive en el adaptador REST)."""
import logging
from contextlib import contextmanager

from fastapi import HTTPException

from app.domain.exceptions import (
    AccesoDenegadoError,
    ConflictoError,
    DatosInvalidosError,
    DemasiadosIntentosError,
    DominioError,
    NoAutenticadoError,
    RecursoNoEncontradoError,
    ServicioExternoError,
    SolicitudInvalidaError,
)

logger = logging.getLogger("datahorse")

# Para soportar un error nuevo basta con agregarlo aquí.
ESTADOS_HTTP: dict[type[DominioError], int] = {
    SolicitudInvalidaError: 400,
    NoAutenticadoError: 401,
    AccesoDenegadoError: 403,
    RecursoNoEncontradoError: 404,
    ConflictoError: 409,
    DatosInvalidosError: 422,
    DemasiadosIntentosError: 429,
    ServicioExternoError: 502,
}


def estado_http(error: DominioError) -> int:
    for clase in type(error).__mro__:
        if clase in ESTADOS_HTTP:
            return ESTADOS_HTTP[clase]
    return 500


@contextmanager
def error_interno(mensaje: str):
    """Convierte fallos inesperados (p. ej. de la BD) en un 500 con un mensaje legible.

    Los errores de negocio y los HTTPException pasan intactos.
    """
    try:
        yield
    except (HTTPException, DominioError):
        raise
    except Exception as e:
        logger.exception(mensaje)
        raise HTTPException(status_code=500, detail=mensaje) from e
