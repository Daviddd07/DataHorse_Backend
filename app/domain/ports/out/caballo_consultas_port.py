from abc import ABC, abstractmethod
from typing import List, Optional


class CaballoConsultasPort(ABC):
    """Lecturas ya armadas para las pantallas del propietario."""

    @abstractmethod
    def listar_de_propietario(self, id_usuario: int) -> List[dict]: ...

    @abstractmethod
    def obtener_detalle_de_propietario(self, id_caballo: int, id_usuario: int) -> Optional[dict]: ...
