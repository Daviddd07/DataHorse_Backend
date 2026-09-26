from dataclasses import dataclass
from typing import Optional


@dataclass
class Raza:
    id_raza: Optional[int]
    nombre: str
    descripcion: Optional[str]