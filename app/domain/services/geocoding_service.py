import requests
from typing import Optional


class GeocodingService:
    """Servicio para convertir texto de ubicacion a coordenadas usando Nominatim."""

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

    # Nominatim requiere un User-Agent identificable
    HEADERS = {
        "User-Agent": "DataHorse/1.0 (contacto@datahorse.com)",
        "Accept-Language": "es",
    }

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def geocodificar(
        self,
        texto: str,
    ) -> Optional[dict]:
        """Convierte un texto de ubicacion a coordenadas + datos normalizados.

        Devuelve un dict con lat, lng, texto, ciudad, departamento.
        O None si no se encontro la ubicacion.
        """
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

            departamento = direccion.get("state")

            return {
                "lat": float(primero["lat"]),
                "lng": float(primero["lon"]),
                "texto": primero.get("display_name", texto),
                "ciudad": ciudad,
                "departamento": departamento,
            }

        except Exception as e:
            print(f"Error geocodificando '{texto}': {e}")
            return None