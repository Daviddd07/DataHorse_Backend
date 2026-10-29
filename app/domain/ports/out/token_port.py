from abc import ABC, abstractmethod
from typing import Optional


class TokenPort(ABC):
    @abstractmethod
    def crear(self, id_usuario: int) -> str: ...

    @abstractmethod
    def decodificar(self, token: str) -> Optional[str]:
        """Devuelve el id del usuario (como texto) o None si el token no es válido."""
