from abc import ABC, abstractmethod
from typing import List

from app.domain.entities.Caballo import Caballo


class CaballoRepositoryPort(ABC):
    @abstractmethod
    def create(self, caballo: Caballo) -> Caballo: ...

    @abstractmethod
    def find_all(self) -> List[Caballo]: ...