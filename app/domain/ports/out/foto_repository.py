from abc import ABC, abstractmethod
from typing import List
from app.domain.entities.foto_caballo import FotoCaballo


class FotoRepository(ABC):

    @abstractmethod
    def guardar(self, foto: FotoCaballo) -> FotoCaballo:
        """Persiste una foto y devuelve la entidad con id asignado."""
        ...

    @abstractmethod
    def listar_por_caballo(self, id_caballo: int) -> List[FotoCaballo]:
        ...

    @abstractmethod
    def contar_por_caballo(self, id_caballo: int) -> int:
        ...

    @abstractmethod
    def obtener_principal(self, id_caballo: int) -> FotoCaballo | None:
        ...