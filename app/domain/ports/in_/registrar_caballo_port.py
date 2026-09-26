from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.domain.entities.Caballo import Caballo


@dataclass
class RegistrarCaballoComando:
    id_propietario: int  # lo decide el servidor (viene del JWT, no del body)
    nombre: str
    sexo: str
    fecha_nacimiento: date
    altura: float
    color: str
    ubicacion: str
    descripcion: str
    disponibilidad: str
    id_raza: Optional[int] = None
    raza_personalizada: Optional[str] = None  # cuando el usuario eligió "Otro"


class RegistrarCaballoPort(ABC):
    @abstractmethod
    def ejecutar(self, c: RegistrarCaballoComando) -> Caballo: ...