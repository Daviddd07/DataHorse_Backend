"""WebSocket de avisos del usuario: le llega un aviso cuando recibe un mensaje nuevo,
aunque no tenga abierta esa conversación.

servidor -> cliente: {"tipo": "nuevo_mensaje", "mensaje": {...}, "remitente": "...",
                      "titulo_publicacion": "..."}
El cliente no necesita enviar nada; lo que mande se ignora.
"""
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status

from app.config.dependencies import get_token_service
from app.domain.ports.out.token_port import TokenPort
from app.infraestructure.adaptadores.inbound.websocket.connection_manager import (
    notificaciones_manager,
)
from app.infraestructure.adaptadores.inbound.websocket.seguridad_ws import (
    CIERRE_NO_AUTENTICADO,
    id_usuario_de,
    origen_permitido,
)

logger = logging.getLogger("datahorse")

router = APIRouter()


@router.websocket("/ws/notificaciones")
async def notificaciones_ws(
    websocket: WebSocket,
    tokens: TokenPort = Depends(get_token_service),
):
    if not origen_permitido(websocket):
        logger.warning(
            "WebSocket de avisos rechazado por origen | origen=%s", websocket.headers.get("origin")
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    id_usuario = id_usuario_de(websocket, tokens)
    if id_usuario is None:
        await websocket.close(code=CIERRE_NO_AUTENTICADO, reason="No autenticado")
        return

    await notificaciones_manager.conectar(id_usuario, websocket)
    try:
        while True:
            await websocket.receive_text()  # mantiene viva la conexión hasta que se cierre
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Error en el WebSocket de avisos del usuario %s", id_usuario)
    finally:
        await notificaciones_manager.desconectar(id_usuario, websocket)
