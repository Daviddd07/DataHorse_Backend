import logging
from typing import Optional

import requests

from app.domain.entities.ubicacion import UbicacionGeocodificada
from app.domain.ports.out.geocoding_port import GeocodingPort

logger = logging.getLogger(__name__)


class NominatimGeocoding(GeocodingPort):
    """Convierte texto de ubicación a coordenadas usando OpenStreetMap Nominatim."""

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

    # Nominatim requiere un User-Agent identificable
    HEADERS = {
        "User-Agent": "DataHorse/1.0 (contacto@datahorse.com)",
        "Accept-Language": "es",
    }

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def geocodificar(self, texto: str) -> Optional[UbicacionGeocodificada]:
        if not texto or not texto.strip():
            return None

        try:
            respuesta = requests.get(
                self.NOMINATIM_URL,
                params={
                    "q": texto.strip(),
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 1,
                },
                headers=self.HEADERS,
                timeout=self.timeout,
            )

            if respuesta.status_code != 200:
                return None

            resultados = respuesta.json()

            if not resultados:
                return None

            primero = resultados[0]
            direccion = primero.get("address", {})

            ciudad = (
                direccion.get("city")
                or direccion.get("town")
                or direccion.get("village")
                or direccion.get("municipality")
                or direccion.get("county")
            )

            return UbicacionGeocodificada(
                lat=float(primero["lat"]),
                lng=float(primero["lon"]),
                texto=primero.get("display_name", texto),
                ciudad=ciudad,
                departamento=direccion.get("state"),
            )

        except Exception:
            # La geocodificación es opcional: si falla, se guarda solo el texto.
            logger.warning("Error geocodificando '%s'", texto, exc_info=True)
            return None
