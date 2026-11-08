from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.config.dependencies import (
    get_abrir_conversacion_use_case,
    get_calificar_usuario_use_case,
    get_contar_no_leidos_use_case,
    get_finalizar_conversacion_use_case,
    get_listar_conversaciones_use_case,
    get_marcar_leidos_use_case,
    get_obtener_calificacion_use_case,
    get_obtener_conversacion_use_case,
)
from app.domain.entities.resena import (
    CALIFICACION_MAXIMA,
    CALIFICACION_MINIMA,
    LONGITUD_MAXIMA_COMENTARIO,
)
from app.domain.ports.in_.conversacion_ports import (
    AbrirConversacionPort,
    ContarNoLeidosPort,
    FinalizarConversacionPort,
    ListarConversacionesPort,
    MarcarLeidosPort,
    ObtenerConversacionPort,
)
from app.domain.ports.in_.resena_ports import CalificarUsuarioPort, ObtenerCalificacionPort
from app.infraestructure.adaptadores.inbound.rest.errores import error_interno
from app.infraestructure.adaptadores.inbound.rest.seguridad import obtener_id_usuario_autenticado
from app.infraestructure.adaptadores.inbound.websocket.connection_manager import (
    manager,
    notificaciones_manager,
)

router = APIRouter(prefix="/conversaciones", tags=["conversaciones"])


class AbrirConversacionRequest(BaseModel):
    id_publicacion: int = Field(gt=0)


class CalificarRequest(BaseModel):
    calificacion: int = Field(ge=CALIFICACION_MINIMA, le=CALIFICACION_MAXIMA)
    comentario: Optional[str] = Field(None, max_length=LONGITUD_MAXIMA_COMENTARIO)


@router.post("")
def abrir_conversacion(
    body: AbrirConversacionRequest,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: AbrirConversacionPort = Depends(get_abrir_conversacion_use_case),
):
    with error_interno("Error al abrir la conversación"):
        id_conversacion = use_case.ejecutar(id_usuario, body.id_publicacion)

    return {"id_conversacion": id_conversacion}


@router.get("")
def listar_conversaciones(
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ListarConversacionesPort = Depends(get_listar_conversaciones_use_case),
):
    with error_interno("Error al listar las conversaciones"):
        return use_case.ejecutar(id_usuario)


@router.get("/no-leidos")
def contar_no_leidos(
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ContarNoLeidosPort = Depends(get_contar_no_leidos_use_case),
):
    with error_interno("Error al contar los mensajes sin leer"):
        return {"total": use_case.ejecutar(id_usuario)}


@router.post("/{id_conversacion}/leer")
def marcar_leidos(
    id_conversacion: int,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: MarcarLeidosPort = Depends(get_marcar_leidos_use_case),
):
    with error_interno("Error al marcar los mensajes como leídos"):
        return {"marcados": use_case.ejecutar(id_usuario, id_conversacion)}


@router.post("/{id_conversacion}/finalizar")
async def finalizar_conversacion(
    id_conversacion: int,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: FinalizarConversacionPort = Depends(get_finalizar_conversacion_use_case),
):
    with error_interno("Error al finalizar la conversación"):
        conversacion = await run_in_threadpool(use_case.ejecutar, id_usuario, id_conversacion)

    # Los dos ven el chat cerrado y el formulario de reseña sin recargar
    await manager.difundir(id_conversacion, {"tipo": "finalizada", "por": id_usuario})
    await notificaciones_manager.difundir(
        conversacion.otro_participante(id_usuario),
        {
            "tipo": "conversacion_finalizada",
            "id_conversacion": id_conversacion,
            "por": conversacion.nombre_de(id_usuario),
        },
    )
    return {"id_conversacion": id_conversacion, "estado": "finalizada"}


@router.post("/{id_conversacion}/resena", status_code=201)
def calificar(
    id_conversacion: int,
    body: CalificarRequest,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: CalificarUsuarioPort = Depends(get_calificar_usuario_use_case),
    calificacion: ObtenerCalificacionPort = Depends(get_obtener_calificacion_use_case),
):
    with error_interno("Error al guardar la reseña"):
        resena = use_case.ejecutar(id_usuario, id_conversacion, body.calificacion, body.comentario)
        resumen = calificacion.ejecutar(resena.id_evaluado)
    return {"resena": resena.a_dict(), "calificacion_evaluado": resumen.a_dict()}


@router.get("/{id_conversacion}/mensajes")
def obtener_mensajes(
    id_conversacion: int,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ObtenerConversacionPort = Depends(get_obtener_conversacion_use_case),
):
    with error_interno("Error al obtener los mensajes"):
        return use_case.ejecutar(id_usuario, id_conversacion)
