from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Caballo:
    id_caballo: Optional[int]
    id_raza: Optional[int]
    id_propietario: int
    nombre: str
    sexo: str  # "Macho" | "Hembra"
    fecha_nacimiento: date
    altura: float
    color: str
    ubicacion: str
    descripcion: str
    disponibilidad: str  # "Disponible" | "No disponible" | "Eliminado"

    ubicacion_lat: Optional[float] = None
    ubicacion_lng: Optional[float] = None
    ubicacion_texto: Optional[str] = None
    ciudad: Optional[str] = None
    departamento: Optional[str] = None

    @property
    def es_macho(self) -> bool:
        return self.sexo == "Macho"

    @property
    def eliminado(self) -> bool:
        return self.disponibilidad == "Eliminado"
