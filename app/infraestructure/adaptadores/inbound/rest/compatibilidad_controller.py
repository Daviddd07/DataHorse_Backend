from fastapi import APIRouter, Depends

from app.config.dependencies import (
    get_cupo_compatibilidad_use_case,
    get_evaluar_compatibilidad_use_case,
    get_listar_resultados_compatibilidad_use_case,
    get_obtener_resultado_compatibilidad_use_case,
)
from app.domain.ports.in_.compatibilidad_ports import (
    ConsultarCupoCompatibilidadPort,
    EvaluarCompatibilidadPort,
    ListarResultadosCompatibilidadPort,
    ObtenerResultadoCompatibilidadPort,
)
from app.infraestructure.adaptadores.inbound.rest.errores import error_interno
from app.infraestructure.adaptadores.inbound.rest.schemas import EvaluarCompatibilidadRequest
from app.infraestructure.adaptadores.inbound.rest.seguridad import obtener_id_usuario_autenticado

router = APIRouter(prefix="/compatibilidad", tags=["compatibilidad"])


@router.get("/cupo")
def consultar_cupo(
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ConsultarCupoCompatibilidadPort = Depends(get_cupo_compatibilidad_use_case),
):
    with error_interno("Error al consultar las estimaciones disponibles"):
        return use_case.ejecutar(id_usuario)


@router.post("")
def evaluar_compatibilidad(
    body: EvaluarCompatibilidadRequest,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: EvaluarCompatibilidadPort = Depends(get_evaluar_compatibilidad_use_case),
):
    with error_interno("Error al evaluar la compatibilidad"):
        return use_case.ejecutar(id_usuario, body.id_caballo, body.id_yegua)


@router.get("/mis-resultados")
def listar_mis_resultados(
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ListarResultadosCompatibilidadPort = Depends(get_listar_resultados_compatibilidad_use_case),
):
    with error_interno("Error al consultar tus estudios"):
        return use_case.ejecutar(id_usuario)


# Estudio guardado: no vuelve a llamar a la IA ni gasta estimaciones
@router.get("/resultados/{id_solicitud}")
def obtener_resultado(
    id_solicitud: int,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ObtenerResultadoCompatibilidadPort = Depends(get_obtener_resultado_compatibilidad_use_case),
):
    with error_interno("Error al consultar el estudio"):
        return use_case.ejecutar(id_usuario, id_solicitud)
