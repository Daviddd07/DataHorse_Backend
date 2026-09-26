from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities.Raza import Raza


class RazaRepositoryPort(ABC):
    @abstractmethod
    def find_all(self) -> List[Raza]: ...

    @abstractmethod
    def find_by_id(self, id_raza: int) -> Optional[Raza]: ...

    @abstractmethod
    def create(self, raza: Raza) -> Raza: ...