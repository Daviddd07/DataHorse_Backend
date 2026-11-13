import logging
import threading
from collections import OrderedDict
from typing import Optional

import requests

from app.domain.entities.ubicacion import UbicacionGeocodificada
from app.domain.ports.out.geocoding_port import GeocodingPort

logger = logging.getLogger(__name__)

# Marca interna: "Nominatim respondió, pero no encontró el lugar" (se cachea igual que un acierto).
_SIN_RESULTADO = object()


class NominatimGeocoding(GeocodingPort):
    """Convierte texto de ubicación a coordenadas usando OpenStreetMap Nominatim.

    Nominatim es un servicio público que admite como máximo 1 petición por segundo y la
    llamada bloquea el hilo de la petición. Por eso:
      - Las respuestas se guardan en una caché en memoria por texto de ubicación (en la
        práctica se repiten pocas ciudades), incluidas las búsquedas sin resultado.
      - Los errores temporales (timeout, red, HTTP != 200) NO se cachean, para reintentar luego.
      - El timeout es corto: la geocodificación es opcional y no debe frenar el registro.
    """

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

    # Nominatim requiere un User-Agent identificable
    HEADERS = {
        "User-Agent": "DataHorse/1.0 (contacto@datahorse.com)",
        "Accept-Language": "es",
    }

    MAX_ENTRADAS_CACHE = 1000

    def __init__(self, timeout: int = 3):
        self.timeout = timeout
        self._cache: OrderedDict[str, object] = OrderedDict()
        self._lock = threading.Lock()  # las rutas síncronas corren en varios hilos

    def geocodificar(self, texto: str) -> Optional[UbicacionGeocodificada]:
        if not texto or not texto.strip():
            return None

        clave = " ".join(texto.split()).casefold()
        en_cache = self._leer_cache(clave)
        if en_cache is not None:
            return None if en_cache is _SIN_RESULTADO else en_cache

        resultado = self._consultar(texto.strip())
        if resultado is not None:  # None = error temporal: no se guarda
            self._guardar_cache(clave, resultado)
            return None if resultado is _SIN_RESULTADO else resultado
        return None

    def _consultar(self, texto: str):
        """Devuelve la ubicación, _SIN_RESULTADO si Nominatim no la encontró, o None si hubo un error."""
        try:
            respuesta = requests.get(
                self.NOMINATIM_URL,
                params={
                    "q": texto,
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
                return _SIN_RESULTADO

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

    def _leer_cache(self, clave: str):
        with self._lock:
            valor = self._cache.get(clave)
            if valor is not None:
                self._cache.move_to_end(clave)  # usado recientemente
            return valor

    def _guardar_cache(self, clave: str, valor) -> None:
        with self._lock:
            self._cache[clave] = valor
            self._cache.move_to_end(clave)
            if len(self._cache) > self.MAX_ENTRADAS_CACHE:
                self._cache.popitem(last=False)  # descarta la menos usada
