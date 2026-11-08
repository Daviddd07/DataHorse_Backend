"""Presencia en línea: un usuario está "en línea" mientras tenga abierto su canal de avisos."""
from app.domain.ports.out.presencia_port import EnLineaPort
from app.infraestructure.adaptadores.inbound.websocket.connection_manager import (
    ConnectionManager,
)


class EnLineaPorWebSocket(EnLineaPort):
    def __init__(self, manager: ConnectionManager):
        self._manager = manager

    def esta_en_linea(self, id_usuario: int) -> bool:
        return self._manager.cantidad(id_usuario) > 0
