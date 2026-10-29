from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from app.domain.entities.foto_caballo import FotoCaballo


@dataclass(frozen=True)
class ArchivoSubido:
    nombre: str
    content_type: str
    contenido: bytes


class SubirFotosPort(ABC):
    @abstractmethod
    def ejecutar(
        self,
        id_caballo: int,
        id_usuario: int,
        archivos: List[ArchivoSubido],
    ) -> List[FotoCaballo]: ...


class EliminarFotoPort(ABC):
    @abstractmethod
    def ejecutar(self, id_caballo: int, id_foto: int, id_usuario: int) -> None: ...
