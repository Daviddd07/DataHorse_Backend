"""Fotos públicas (/uploads/caballos/... y /uploads/perfiles/...) cuando se guardan en S3.

Con ALMACENAMIENTO=local las sirve StaticFiles desde el disco (main.py). Con ALMACENAMIENTO=s3 el bucket
es privado y este endpoint las entrega con la MISMA URL de siempre, así que el frontend no cambia.
Los documentos no pasan por aquí: son privados y solo se descargan con sesión (documento_controller).
"""
import mimetypes

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.config.dependencies import get_almacenamientos_publicos
from app.domain.exceptions import RecursoNoEncontradoError

router = APIRouter(tags=["Archivos"])

# Los nombres son únicos (uuid): el archivo nunca cambia, así que el navegador puede guardarlo en caché
_CACHE = "public, max-age=31536000, immutable"


@router.get("/uploads/{carpeta}/{nombre}", include_in_schema=False)
def obtener_archivo_publico(
    carpeta: str,
    nombre: str,
    almacenamientos: dict = Depends(get_almacenamientos_publicos),
) -> Response:
    almacenamiento = almacenamientos.get(carpeta)
    if almacenamiento is None:
        raise RecursoNoEncontradoError("Archivo no encontrado")

    try:
        contenido = almacenamiento.leer(f"uploads/{carpeta}/{nombre}")
    except FileNotFoundError as e:
        raise RecursoNoEncontradoError("Archivo no encontrado") from e

    tipo = mimetypes.guess_type(nombre)[0] or "application/octet-stream"
    return Response(
        content=contenido,
        media_type=tipo,
        headers={"Cache-Control": _CACHE, "X-Content-Type-Options": "nosniff"},
    )
