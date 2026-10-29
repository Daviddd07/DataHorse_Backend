from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.domain.entities.Caballo import Caballo


@dataclass(frozen=True)
class NuevaPublicacion:
    titulo: str
    descripcion: str
    precio_referencia: float
    fecha_publicacion: date
    estado: str = "Activa"


@dataclass(frozen=True)
class CambiosPublicacion:
    titulo: str
    descripcion: str
    precio_referencia: float


@dataclass(frozen=True)
class CaballoRegistrado:
    id_caballo: int
    id_raza: int
    id_publicacion: Optional[int]


class CaballoRepositoryPort(ABC):
    """Escritura y lectura del agregado Caballo. Cada método es una transacción."""

    @abstractmethod
    def existe(self, id_caballo: int) -> bool: ...

    @abstractmethod
    def obtener_de_propietario(self, id_caballo: int, id_usuario: int) -> Optional[Caballo]:
        """Devuelve el caballo (incluidos los eliminados) solo si pertenece al usuario."""

    @abstractmethod
    def registrar(
        self,
        caballo: Caballo,
        raza_nueva: Optional[str],
        publicacion: Optional[NuevaPublicacion],
    ) -> CaballoRegistrado:
        """Crea la raza (si es nueva), el caballo y su publicación en una sola transacción."""

    @abstractmethod
    def actualizar(
        self,
        caballo: Caballo,
        raza_nueva: Optional[str],
        publicacion: Optional[CambiosPublicacion],
    ) -> None:
        """Actualiza el caballo (y su publicación activa) en una sola transacción."""

    @abstractmethod
    def eliminar(self, id_caballo: int) -> None:
        """Borra la publicación y marca el caballo como 'Eliminado'."""
