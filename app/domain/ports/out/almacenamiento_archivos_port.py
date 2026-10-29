from abc import ABC, abstractmethod


class AlmacenamientoArchivosPort(ABC):
    @abstractmethod
    def guardar(self, extension: str, contenido: bytes) -> str:
        """Guarda el archivo con un nombre único y devuelve su ruta relativa."""

    @abstractmethod
    def eliminar(self, ruta_relativa: str) -> None: ...
