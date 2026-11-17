"""Almacenamiento de archivos en un bucket S3 (producción).

Misma interfaz y mismas rutas relativas que AlmacenamientoLocal: la clave del objeto en S3
es la ruta que se guarda en la base (p. ej. "uploads/caballos/<uuid>.jpg" o "documentos/<uuid>.pdf"),
así que cambiar de disco a S3 no cambia la base de datos ni el frontend.
El bucket es privado: las fotos públicas las entrega el backend por /uploads (ver archivos_publicos_controller).
"""
import mimetypes
import uuid
from pathlib import PurePosixPath

from botocore.exceptions import ClientError

from app.domain.ports.out.almacenamiento_archivos_port import AlmacenamientoArchivosPort

# Códigos con los que S3 indica que el objeto no existe
_NO_EXISTE = {"NoSuchKey", "404", "NotFound"}


class AlmacenamientoS3(AlmacenamientoArchivosPort):
    """Guarda archivos en S3 bajo un prefijo y devuelve la ruta relativa (= clave del objeto)."""

    def __init__(self, cliente_s3, bucket: str, prefijo: str):
        self._s3 = cliente_s3
        self._bucket = bucket
        self._prefijo = prefijo.strip("/")

    def _clave(self, ruta_relativa: str) -> str:
        # Igual que en local: solo se usa el nombre del archivo, nunca se sale del prefijo.
        return f"{self._prefijo}/{PurePosixPath(ruta_relativa).name}"

    def guardar(self, extension: str, contenido: bytes) -> str:
        ruta = f"{self._prefijo}/{uuid.uuid4().hex}{extension}"
        tipo = mimetypes.guess_type(ruta)[0] or "application/octet-stream"
        self._s3.put_object(Bucket=self._bucket, Key=ruta, Body=contenido, ContentType=tipo)
        return ruta

    def eliminar(self, ruta_relativa: str) -> None:
        # En S3 borrar algo que no existe no es un error (igual que en local).
        self._s3.delete_object(Bucket=self._bucket, Key=self._clave(ruta_relativa))

    def leer(self, ruta_relativa: str) -> bytes:
        try:
            respuesta = self._s3.get_object(Bucket=self._bucket, Key=self._clave(ruta_relativa))
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in _NO_EXISTE:
                raise FileNotFoundError(ruta_relativa) from e
            raise
        return respuesta["Body"].read()
