from fastapi import APIRouter, Depends

from app.config.dependencies import get_listar_razas_use_case
from app.domain.ports.in_.listar_razas_port import ListarRazasPort
from app.infraestructure.adaptadores.inbound.rest.errores import error_interno

router = APIRouter(prefix="/razas", tags=["razas"])


@router.get("")
def listar_razas(use_case: ListarRazasPort = Depends(get_listar_razas_use_case)):
    with error_interno("Error al consultar razas"):
        return [
            {"id_raza": r.id_raza, "nombre": r.nombre, "descripcion": r.descripcion}
            for r in use_case.ejecutar()
        ]
