from fastapi import APIRouter, Depends

from app.config.dependencies import get_obtener_calificacion_use_case
from app.domain.ports.in_.resena_ports import ObtenerCalificacionPort
from app.infraestructure.adaptadores.inbound.rest.errores import error_interno
from app.infraestructure.adaptadores.inbound.rest.seguridad import obtener_id_usuario_autenticado

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("/{id_usuario}/calificacion")
def obtener_calificacion(
    id_usuario: int,
    _id_actual: int = Depends(obtener_id_usuario_autenticado),
    use_case: ObtenerCalificacionPort = Depends(get_obtener_calificacion_use_case),
):
    """Promedio de estrellas (1 a 5) y cantidad de reseñas de un usuario."""
    with error_interno("Error al consultar la calificación"):
        return use_case.ejecutar(id_usuario).a_dict()
