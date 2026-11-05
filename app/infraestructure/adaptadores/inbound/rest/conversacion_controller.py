from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.config.dependencies import (
    get_abrir_conversacion_use_case,
    get_contar_no_leidos_use_case,
    get_listar_conversaciones_use_case,
    get_marcar_leidos_use_case,
    get_obtener_conversacion_use_case,
)
from app.domain.ports.in_.conversacion_ports import (
    AbrirConversacionPort,
    ContarNoLeidosPort,
    ListarConversacionesPort,
    MarcarLeidosPort,
    ObtenerConversacionPort,
)
from app.infraestructure.adaptadores.inbound.rest.errores import error_interno
from app.infraestructure.adaptadores.inbound.rest.seguridad import obtener_id_usuario_autenticado

router = APIRouter(prefix="/conversaciones", tags=["conversaciones"])


class AbrirConversacionRequest(BaseModel):
    id_publicacion: int = Field(gt=0)


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


@router.get("/{id_conversacion}/mensajes")
def obtener_mensajes(
    id_conversacion: int,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ObtenerConversacionPort = Depends(get_obtener_conversacion_use_case),
):
    with error_interno("Error al obtener los mensajes"):
        return use_case.ejecutar(id_usuario, id_conversacion)
