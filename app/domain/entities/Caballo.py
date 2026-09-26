from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Caballo:
    id_caballo: Optional[int]
    id_raza: int
    id_propietario: int
    nombre: str
    sexo: str  # "Macho" | "Hembra"
    fecha_nacimiento: date
    altura: float
    color: str
    ubicacion: str
    descripcion: str
    disponibilidad: str  # "Disponible" | "No disponible"