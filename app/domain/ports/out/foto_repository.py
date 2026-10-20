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
        
    @abstractmethod
    def obtener_por_id(self, id_foto: int) -> FotoCaballo | None:
        """Devuelve una foto por su id, o None si no existe."""
        ...

    @abstractmethod
    def eliminar(self, id_foto: int) -> None:
        """Elimina el registro de la foto. El archivo fisico se maneja aparte."""
        ...

    @abstractmethod
    def promover_principal(self, id_caballo: int) -> None:
        """Marca la primera foto restante como principal si no existe ninguna."""
        ...