from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Optional

from app.domain.entities.conversacion import Conversacion, Mensaje


class ConversacionRepositoryPort(ABC):
    @abstractmethod
    def obtener_dueno_publicacion_activa(self, id_publicacion: int) -> Optional[int]:
        """Devuelve el id del dueño de la publicación, o None si no existe o no está activa."""

    @abstractmethod
    def buscar_id(self, id_publicacion: int, id_interesado: int) -> Optional[int]: ...

    @abstractmethod
    def crear(self, id_publicacion: int, id_interesado: int, fecha: date) -> int:
        """Crea la conversación (o devuelve la existente si otra solicitud se adelantó)."""

    @abstractmethod
    def obtener(self, id_conversacion: int) -> Optional[Conversacion]: ...

    @abstractmethod
    def obtener_resumen(self, id_conversacion: int, id_usuario: int) -> Optional[dict]:
        """Datos de cabecera de la conversación vistos por id_usuario (título, el otro participante...)."""

    @abstractmethod
    def listar_de_usuario(self, id_usuario: int) -> List[dict]: ...

    @abstractmethod
    def listar_mensajes(self, id_conversacion: int, limite: int) -> List[Mensaje]:
        """Últimos `limite` mensajes, del más antiguo al más reciente."""

    @abstractmethod
    def contar_no_leidos(self, id_usuario: int) -> int:
        """Mensajes que otros le enviaron a id_usuario y que aún no ha leído."""

    @abstractmethod
    def marcar_leidos(self, id_conversacion: int, id_usuario: int) -> int:
        """Marca como leídos los mensajes recibidos por id_usuario; devuelve cuántos cambiaron."""

    @abstractmethod
    def guardar_mensaje(
        self, id_conversacion: int, id_usuario: int, contenido: str, fecha_envio: datetime
    ) -> Mensaje: ...
