from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class FotoCaballo:
    id_foto: Optional[int]
    id_caballo: int
    ruta: str                    # "uploads/caballos/abc123.jpg"
    es_principal: bool
    orden: int
    fecha_subida: Optional[datetime] = None