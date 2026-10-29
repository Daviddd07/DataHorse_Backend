from abc import ABC, abstractmethod
from typing import List, Optional


class PublicacionConsultasPort(ABC):
    @abstractmethod
    def listar_activas(self, id_usuario_actual: int) -> List[dict]: ...

    @abstractmethod
    def obtener_detalle(self, id_publicacion: int, id_usuario_actual: int) -> Optional[dict]: ...
