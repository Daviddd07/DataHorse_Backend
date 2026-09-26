from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Publicacion:
    id_publicacion: Optional[int]
    id_caballo: int
    id_usuario: int
    titulo: str
    descripcion: str
    precio_referencia: float
    estado: str
    fecha_publicacion: date