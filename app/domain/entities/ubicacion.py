from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class UbicacionGeocodificada:
    lat: float
    lng: float
    texto: str
    ciudad: Optional[str]
    departamento: Optional[str]
