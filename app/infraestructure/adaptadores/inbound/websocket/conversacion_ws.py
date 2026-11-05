"""WebSocket de las conversaciones: recibe mensajes, los guarda y los reenvía a los participantes.

Protocolo (JSON):
    cliente -> servidor: {"tipo": "mensaje", "contenido": "..."}
    servidor -> cliente: {"tipo": "mensaje", "mensaje": {...}}
                         {"tipo": "error", "detalle": "..."}

Además, cada mensaje se avisa al otro participante por su WebSocket de avisos
(/ws/notificaciones), para que lo vea aunque no tenga el chat abierto.

Códigos de cierre propios: 4401 sin sesión, 4403 no participa, 4404 no existe.
"""
import json
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from starlette.concurrency import run_in_threadpool

from app.config.dependencies import (
    get_enviar_mensaje_use_case,
    get_token_service,
    get_verificar_participante_use_case,
)
from app.domain.entities.conversacion import Conversacion, Mensaje
from app.domain.exceptions import (
    AccesoDenegadoError,
    DominioError,
    RecursoNoEncontradoError,
)
from app.domain.ports.in_.conversacion_ports import EnviarMensajePort, VerificarParticipantePort
from app.domain.ports.out.token_port import TokenPort
from app.infraestructure.adaptadores.inbound.websocket.connection_manager import (
    manager,
    notificaciones_manager,
)
from app.infraestructure.adaptadores.inbound.websocket.seguridad_ws import (
    CIERRE_ACCESO_DENEGADO,
    CIERRE_NO_AUTENTICADO,
    CIERRE_NO_ENCONTRADO,
    id_usuario_de,
    origen_permitido,
)

logger = logging.getLogger("datahorse")

router = APIRouter()


async def _avisar_al_destinatario(conversacion: Conversacion, mensaje: Mensaje) -> None:
    destinatario = conversacion.otro_participante(mensaje.id_usuario)
    await notificaciones_manager.difundir(
        destinatario,
        {
            "tipo": "nuevo_mensaje",
            "mensaje": mensaje.a_dict(),
            "remitente": conversacion.nombre_de(mensaje.id_usuario),
            "titulo_publicacion": conversacion.titulo_publicacion,
        },
    )


@router.websocket("/ws/conversaciones/{id_conversacion}")
async def conversacion_ws(
    websocket: WebSocket,
    id_conversacion: int,
    tokens: TokenPort = Depends(get_token_service),
    verificador: VerificarParticipantePort = Depends(get_verificar_participante_use_case),
    enviar: EnviarMensajePort = Depends(get_enviar_mensaje_use_case),
):
    # Un origen ajeno se rechaza antes de aceptar (el navegador recibe un 403).
    if not origen_permitido(websocket):
        logger.warning(
            "WebSocket rechazado por origen no permitido | origen=%s", websocket.headers.get("origin")
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Se acepta primero para que el cliente reciba el código de cierre y sepa si reintentar.
    await websocket.accept()

    id_usuario = id_usuario_de(websocket, tokens)
    if id_usuario is None:
        await websocket.close(code=CIERRE_NO_AUTENTICADO, reason="No autenticado")
        return

    try:
        conversacion = await run_in_threadpool(verificador.ejecutar, id_usuario, id_conversacion)
    except RecursoNoEncontradoError:
        await websocket.close(code=CIERRE_NO_ENCONTRADO, reason="Conversación no encontrada")
        return
    except AccesoDenegadoError:
        await websocket.close(code=CIERRE_ACCESO_DENEGADO, reason="No perteneces a esta conversación")
        return
    except Exception:
        logger.exception("Error al validar la conversación %s por WebSocket", id_conversacion)
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    await manager.conectar(id_conversacion, websocket)
    logger.info(
        "WebSocket conectado | conversación=%s | usuario=%s | conexiones=%s",
        id_conversacion, id_usuario, manager.cantidad(id_conversacion),
    )

    try:
        while True:
            texto = await websocket.receive_text()

            # La sesión dura poco (cookie de 30 min): si caducó, se corta el chat.
            if id_usuario_de(websocket, tokens) is None:
                await websocket.close(code=CIERRE_NO_AUTENTICADO, reason="Sesión expirada")
                break

            try:
                datos = json.loads(texto)
            except ValueError:
                await websocket.send_json({"tipo": "error", "detalle": "Formato inválido"})
                continue

            if not isinstance(datos, dict) or datos.get("tipo") != "mensaje":
                await websocket.send_json({"tipo": "error", "detalle": "Tipo de mensaje no soportado"})
                continue

            contenido = datos.get("contenido")
            if not isinstance(contenido, str):
                await websocket.send_json({"tipo": "error", "detalle": "El mensaje debe ser texto"})
                continue

            try:
                mensaje = await run_in_threadpool(enviar.ejecutar, id_usuario, id_conversacion, contenido)
            except AccesoDenegadoError:
                await websocket.close(code=CIERRE_ACCESO_DENEGADO, reason="No perteneces a esta conversación")
                break
            except DominioError as e:
                await websocket.send_json({"tipo": "error", "detalle": e.mensaje})
                continue
            except Exception:
                logger.exception("Error al guardar un mensaje de la conversación %s", id_conversacion)
                await websocket.send_json({"tipo": "error", "detalle": "No se pudo enviar el mensaje"})
                continue

            await manager.difundir(id_conversacion, {"tipo": "mensaje", "mensaje": mensaje.a_dict()})
            await _avisar_al_destinatario(conversacion, mensaje)

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Error en el WebSocket de la conversación %s", id_conversacion)
    finally:
        await manager.desconectar(id_conversacion, websocket)
        logger.info(
            "WebSocket desconectado | conversación=%s | usuario=%s", id_conversacion, id_usuario
        )
