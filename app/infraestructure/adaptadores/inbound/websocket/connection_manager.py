import asyncio
import logging
from collections import defaultdict
from typing import Dict, Set

from fastapi import WebSocket

logger = logging.getLogger("datahorse")


class ConnectionManager:
    """Conexiones WebSocket activas agrupadas por una clave numérica.

    Se usa con dos claves distintas: por conversación (chat abierto) y por usuario
    (avisos de mensajes nuevos en cualquier pantalla).
    Vive en memoria del proceso: sirve mientras el backend corra con un solo worker
    de uvicorn. Con varios workers haría falta un canal compartido (p. ej. Redis).
    Una misma clave puede tener varias conexiones (varias pestañas abiertas).
    """

    def __init__(self, nombre: str = "conexiones") -> None:
        self._nombre = nombre
        self._conexiones: Dict[int, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def conectar(self, clave: int, websocket: WebSocket) -> None:
        async with self._lock:
            self._conexiones[clave].add(websocket)

    async def desconectar(self, clave: int, websocket: WebSocket) -> None:
        async with self._lock:
            conexiones = self._conexiones.get(clave)
            if conexiones is None:
                return
            conexiones.discard(websocket)
            if not conexiones:
                del self._conexiones[clave]

    def cantidad(self, clave: int) -> int:
        return len(self._conexiones.get(clave, ()))

    async def difundir(self, clave: int, datos: dict) -> None:
        """Envía `datos` a todas las conexiones de la clave; descarta las que fallen."""
        async with self._lock:
            destinatarios = list(self._conexiones.get(clave, ()))

        caidas = []
        for websocket in destinatarios:
            try:
                await websocket.send_json(datos)
            except Exception:
                logger.warning("No se pudo enviar por WebSocket | %s=%s", self._nombre, clave)
                caidas.append(websocket)

        for websocket in caidas:
            await self.desconectar(clave, websocket)


# Chat abierto: clave = id de la conversación
manager = ConnectionManager("conversación")

# Avisos de mensajes nuevos: clave = id del usuario
notificaciones_manager = ConnectionManager("usuario")
