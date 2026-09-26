from abc import ABC, abstractmethod
from typing import List

from app.domain.entities.Raza import Raza


class ListarRazasPort(ABC):
    @abstractmethod
    def ejecutar(self) -> List[Raza]: ...