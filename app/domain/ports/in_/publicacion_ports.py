from abc import ABC, abstractmethod
from typing import List, Optional


class ListarPublicacionesPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario_actual: Optional[int]) -> List[dict]: ...


class ObtenerPublicacionPort(ABC):
    @abstractmethod
    def ejecutar(self, id_publicacion: int, id_usuario_actual: Optional[int]) -> dict: ...
