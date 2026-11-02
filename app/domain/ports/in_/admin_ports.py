from abc import ABC, abstractmethod
from typing import List


class VerificarAdministradorPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int) -> None:
        """Lanza AccesoDenegadoError si el usuario no es administrador."""


class ObtenerResumenAdminPort(ABC):
    @abstractmethod
    def ejecutar(self) -> dict: ...


class ListarUsuariosAdminPort(ABC):
    @abstractmethod
    def ejecutar(self) -> List[dict]: ...
