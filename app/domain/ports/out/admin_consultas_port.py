from abc import ABC, abstractmethod
from typing import List


class AdminConsultasPort(ABC):
    @abstractmethod
    def resumen(self) -> dict:
        """Totales de usuarios, caballos (por sexo y raza) y publicaciones."""

    @abstractmethod
    def listar_usuarios(self) -> List[dict]:
        """Usuarios con la cantidad de caballos, machos, yeguas y publicaciones de cada uno."""
