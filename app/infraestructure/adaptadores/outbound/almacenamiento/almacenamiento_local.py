import uuid
from pathlib import Path

from app.domain.ports.out.almacenamiento_archivos_port import AlmacenamientoArchivosPort


class AlmacenamientoLocal(AlmacenamientoArchivosPort):
    """Guarda archivos en disco y devuelve la ruta relativa que sirve /uploads."""

    def __init__(self, directorio: Path, prefijo_url: str):
        self._directorio = directorio
        self._prefijo = prefijo_url.strip("/")

    def guardar(self, extension: str, contenido: bytes) -> str:
        nombre = f"{uuid.uuid4().hex}{extension}"
        self._directorio.mkdir(parents=True, exist_ok=True)
        (self._directorio / nombre).write_bytes(contenido)
        return f"{self._prefijo}/{nombre}"

    def eliminar(self, ruta_relativa: str) -> None:
        # Solo se usa el nombre del archivo para impedir rutas fuera del directorio.
        ruta_fisica = self._directorio / Path(ruta_relativa).name

        if ruta_fisica.exists():
            ruta_fisica.unlink()
