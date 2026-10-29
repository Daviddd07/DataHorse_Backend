from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.ubicacion import UbicacionGeocodificada


class GeocodingPort(ABC):
    @abstractmethod
    def geocodificar(self, texto: str) -> Optional[UbicacionGeocodificada]:
        """Devuelve la ubicación normalizada, o None si no se pudo resolver."""
