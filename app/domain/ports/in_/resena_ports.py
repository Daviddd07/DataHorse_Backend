from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities.resena import EstadoConexion, Resena, ResumenCalificacion


class CalificarUsuarioPort(ABC):
    @abstractmethod
    def ejecutar(
        self, id_usuario: int, id_conversacion: int, calificacion: int, comentario: Optional[str]
    ) -> Resena:
        """El participante califica al otro (1 a 5 estrellas) en un chat finalizado."""


class ObtenerCalificacionPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int) -> ResumenCalificacion: ...


class ObtenerEstadoConexionPort(ABC):
    @abstractmethod
    def ejecutar(self, ids_usuario: List[int]) -> dict[int, EstadoConexion]: ...


class RegistrarConexionPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int) -> None:
        """Guarda la hora actual como última conexión del usuario."""
