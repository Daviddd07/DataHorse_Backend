from dataclasses import dataclass
from datetime import datetime

ESTADO_CONVERSACION_ACTIVA = "activa"
ESTADO_MENSAJE_NO_LEIDO = "no_leido"
ESTADO_MENSAJE_LEIDO = "leido"
LONGITUD_MAXIMA_MENSAJE = 2000


@dataclass(frozen=True)
class Conversacion:
    """Conversación entre el interesado y el dueño (vendedor) de una publicación."""

    id_conversacion: int
    id_publicacion: int
    id_interesado: int
    id_vendedor: int
    nombre_interesado: str = ""
    nombre_vendedor: str = ""
    titulo_publicacion: str = ""

    def es_participante(self, id_usuario: int) -> bool:
        return id_usuario in (self.id_interesado, self.id_vendedor)

    def otro_participante(self, id_usuario: int) -> int:
        return self.id_vendedor if id_usuario == self.id_interesado else self.id_interesado

    def nombre_de(self, id_usuario: int) -> str:
        return self.nombre_interesado if id_usuario == self.id_interesado else self.nombre_vendedor


@dataclass(frozen=True)
class Mensaje:
    id_mensaje: int
    id_conversacion: int
    id_usuario: int
    contenido: str
    fecha_envio: datetime
    estado_lectura: str

    def a_dict(self) -> dict:
        return {
            "id_mensaje": self.id_mensaje,
            "id_conversacion": self.id_conversacion,
            "id_usuario": self.id_usuario,
            "contenido": self.contenido,
            "fecha_envio": self.fecha_envio.isoformat(),
            "estado_lectura": self.estado_lectura,
        }
