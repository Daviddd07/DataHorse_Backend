from abc import ABC, abstractmethod
from typing import List

from app.domain.entities.Publicaciones import Publicacion


class PublicacionRepositoryPort(ABC):
    @abstractmethod
    def create(self, publicacion: Publicacion) -> Publicacion: ...

    @abstractmethod
    def find_all_activas(self) -> List[dict]: ...