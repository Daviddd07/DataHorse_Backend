from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

CALIFICACION_MINIMA = 1
CALIFICACION_MAXIMA = 5
LONGITUD_MAXIMA_COMENTARIO = 1000


@dataclass(frozen=True)
class Resena:
    """Calificación que un participante deja al otro al finalizar una conversación."""

    id_resena: int
    id_conversacion: int
    id_evaluador: int
    id_evaluado: int
    calificacion: int
    comentario: Optional[str]
    fecha: date

    def a_dict(self) -> dict:
        return {
            "id_resena": self.id_resena,
            "id_conversacion": self.id_conversacion,
            "id_evaluador": self.id_evaluador,
            "id_evaluado": self.id_evaluado,
            "calificacion": self.calificacion,
            "comentario": self.comentario,
            "fecha": self.fecha.isoformat(),
        }


@dataclass(frozen=True)
class ResumenCalificacion:
    """Promedio de estrellas (1 a 5) y cuántas reseñas tiene un usuario."""

    promedio: Optional[float]
    total: int

    @staticmethod
    def desde(promedio, total) -> "ResumenCalificacion":
        total = int(total or 0)
        if total == 0 or promedio is None:
            return ResumenCalificacion(promedio=None, total=0)
        return ResumenCalificacion(promedio=round(float(promedio), 1), total=total)

    def a_dict(self) -> dict:
        return {"promedio": self.promedio, "total": self.total}


@dataclass(frozen=True)
class EstadoConexion:
    """Si el usuario tiene la app abierta ahora y cuándo se conectó por última vez."""

    en_linea: bool
    ultima_conexion: Optional[datetime]

    def a_dict(self) -> dict:
        return {
            "en_linea": self.en_linea,
            "ultima_conexion": self.ultima_conexion.isoformat() if self.ultima_conexion else None,
        }
