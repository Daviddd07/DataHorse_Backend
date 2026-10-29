from abc import ABC, abstractmethod
from typing import Optional


class AgregarFavoritoPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int, id_caballo: int) -> Optional[int]:
        """Devuelve el id del favorito creado, o None si ya existía."""


class QuitarFavoritoPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int, id_caballo: int) -> bool:
        """Devuelve True si se quitó, False si el caballo no estaba en favoritos."""
