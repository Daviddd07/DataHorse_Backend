from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Iterable, Optional


class EnLineaPort(ABC):
    """Quién tiene la app abierta ahora mismo (lo sabe el canal de avisos en tiempo real)."""

    @abstractmethod
    def esta_en_linea(self, id_usuario: int) -> bool: ...


class UltimaConexionRepositoryPort(ABC):
    @abstractmethod
    def registrar(self, id_usuario: int, momento: datetime) -> None: ...

    @abstractmethod
    def obtener(self, ids_usuario: Iterable[int]) -> Dict[int, Optional[datetime]]: ...
