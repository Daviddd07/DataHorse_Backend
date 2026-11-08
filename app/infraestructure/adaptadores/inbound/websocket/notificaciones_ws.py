"""WebSocket de avisos del usuario.

Mientras está abierto, el usuario cuenta como "en línea" para las personas con las que chatea.

servidor -> cliente:
    {"tipo": "nuevo_mensaje", "mensaje": {...}, "remitente": "...", "titulo_publicacion": "..."}
    {"tipo": "conversacion_finalizada", "id_conversacion": 3, "por": "..."}
    {"tipo": "presencia", "id_usuario": 7, "en_linea": true, "ultima_conexion": "..."}
El cliente no necesita enviar nada; lo que mande se ignora.
"""
import logging
from typing import Callable, List

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from starlette.concurrency import run_in_threadpool

from app.config.dependencies import (
    get_buscar_contactos,
    get_estado_conexion_use_case,
    get_registrar_conexion_use_case,
    get_token_service,
)
from app.domain.ports.in_.resena_ports import ObtenerEstadoConexionPort, RegistrarConexionPort
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


async def _anunciar_presencia(
    id_usuario: int,
    registrar: RegistrarConexionPort,
    estado_conexion: ObtenerEstadoConexionPort,
    buscar_contactos: Callable[[int], List[int]],
) -> None:
    """Guarda la hora de conexión y avisa a sus contactos si entró o salió."""
    try:
        await run_in_threadpool(registrar.ejecutar, id_usuario)
        estados = await run_in_threadpool(estado_conexion.ejecutar, [id_usuario])
        contactos = await run_in_threadpool(buscar_contactos, id_usuario)
    except Exception:
        logger.exception("No se pudo actualizar la presencia del usuario %s", id_usuario)
        return

    evento = {"tipo": "presencia", "id_usuario": id_usuario, **estados[id_usuario].a_dict()}
    for contacto in contactos:
        await notificaciones_manager.difundir(contacto, evento)


@router.websocket("/ws/notificaciones")
async def notificaciones_ws(
    websocket: WebSocket,
    tokens: TokenPort = Depends(get_token_service),
    registrar: RegistrarConexionPort = Depends(get_registrar_conexion_use_case),
    estado_conexion: ObtenerEstadoConexionPort = Depends(get_estado_conexion_use_case),
    buscar_contactos: Callable[[int], List[int]] = Depends(get_buscar_contactos),
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

    estaba_desconectado = notificaciones_manager.cantidad(id_usuario) == 0
    await notificaciones_manager.conectar(id_usuario, websocket)
    if estaba_desconectado:
        await _anunciar_presencia(id_usuario, registrar, estado_conexion, buscar_contactos)

    try:
        while True:
            await websocket.receive_text()  # mantiene viva la conexión hasta que se cierre
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Error en el WebSocket de avisos del usuario %s", id_usuario)
    finally:
        await notificaciones_manager.desconectar(id_usuario, websocket)
        # Solo pasa a "inactivo" cuando cierra su última pestaña
        if notificaciones_manager.cantidad(id_usuario) == 0:
            await _anunciar_presencia(id_usuario, registrar, estado_conexion, buscar_contactos)
