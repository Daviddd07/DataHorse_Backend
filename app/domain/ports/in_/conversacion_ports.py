from abc import ABC, abstractmethod
from typing import List

from app.domain.entities.conversacion import Conversacion, Mensaje


class AbrirConversacionPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int, id_publicacion: int) -> int:
        """Devuelve el id de la conversación (nueva o ya existente) con el dueño de la publicación."""


class ListarConversacionesPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int) -> List[dict]: ...


class ObtenerConversacionPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int, id_conversacion: int) -> dict:
        """Cabecera de la conversación y su historial de mensajes."""


class VerificarParticipantePort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int, id_conversacion: int) -> Conversacion:
        """Lanza RecursoNoEncontradoError o AccesoDenegadoError si el usuario no puede entrar."""


class ContarNoLeidosPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int) -> int: ...


class MarcarLeidosPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int, id_conversacion: int) -> int: ...


class FinalizarConversacionPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int, id_conversacion: int) -> Conversacion:
        """Pasa la conversación a 'finalizada' (queda en solo lectura y se puede calificar)."""


class EnviarMensajePort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int, id_conversacion: int, contenido: str) -> Mensaje: ...
