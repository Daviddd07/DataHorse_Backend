from abc import ABC, abstractmethod
from typing import List


class ListarPublicacionesPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario_actual: int) -> List[dict]: ...


class ObtenerPublicacionPort(ABC):
    @abstractmethod
    def ejecutar(self, id_publicacion: int, id_usuario_actual: int) -> dict: ...
