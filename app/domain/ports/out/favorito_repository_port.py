from abc import ABC, abstractmethod
from datetime import date


class FavoritoRepositoryPort(ABC):
    @abstractmethod
    def existe(self, id_usuario: int, id_caballo: int) -> bool: ...

    @abstractmethod
    def agregar(self, id_usuario: int, id_caballo: int, fecha: date) -> int:
        """Devuelve el id del favorito creado."""

    @abstractmethod
    def quitar(self, id_usuario: int, id_caballo: int) -> int:
        """Devuelve cuántas filas se eliminaron."""
