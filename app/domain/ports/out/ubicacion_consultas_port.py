from abc import ABC, abstractmethod
from typing import List, Optional


class UbicacionConsultasPort(ABC):
    @abstractmethod
    def listar_departamentos(self) -> List[str]: ...

    @abstractmethod
    def listar_ciudades(self, departamento: Optional[str] = None) -> List[str]: ...
