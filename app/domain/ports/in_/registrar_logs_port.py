from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities.log_frontend import LogFrontend


class RegistrarLogsPort(ABC):
    @abstractmethod
    def ejecutar(self, logs: List[LogFrontend], id_usuario: Optional[int]) -> int: ...
