from abc import ABC, abstractmethod
from typing import List

from app.domain.entities.log_frontend import LogFrontend


class LogRepositoryPort(ABC):
    @abstractmethod
    def guardar_lote(self, logs: List[LogFrontend]) -> int:
        """Guarda todos los logs en una sola transacción y devuelve cuántos se guardaron."""
