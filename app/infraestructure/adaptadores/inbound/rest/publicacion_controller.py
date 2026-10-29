from fastapi import APIRouter, Depends

from app.config.dependencies import (
    get_listar_publicaciones_use_case,
    get_obtener_publicacion_use_case,
)
from app.domain.ports.in_.publicacion_ports import ListarPublicacionesPort, ObtenerPublicacionPort
from app.infraestructure.adaptadores.inbound.rest.errores import error_interno
from app.infraestructure.adaptadores.inbound.rest.seguridad import obtener_id_usuario_autenticado

router = APIRouter(prefix="/publicaciones", tags=["publicaciones"])


@router.get("")
def listar_publicaciones(
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ListarPublicacionesPort = Depends(get_listar_publicaciones_use_case),
):
    with error_interno("Error al consultar publicaciones"):
        return use_case.ejecutar(id_usuario)


@router.get("/{id_publicacion}")
def obtener_publicacion_detalle(
    id_publicacion: int,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ObtenerPublicacionPort = Depends(get_obtener_publicacion_use_case),
):
    with error_interno("Error al consultar la publicación"):
        return use_case.ejecutar(id_publicacion, id_usuario)
