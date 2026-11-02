from fastapi import APIRouter, Depends

from app.config.dependencies import (
    get_listar_usuarios_admin_use_case,
    get_resumen_admin_use_case,
)
from app.domain.ports.in_.admin_ports import ListarUsuariosAdminPort, ObtenerResumenAdminPort
from app.infraestructure.adaptadores.inbound.rest.errores import error_interno
from app.infraestructure.adaptadores.inbound.rest.seguridad import obtener_id_admin_autenticado

# Todas las rutas exigen sesión de administrador (401 sin sesión, 403 si no es admin).
router = APIRouter(
    prefix="/admin",
    tags=["administración"],
    dependencies=[Depends(obtener_id_admin_autenticado)],
)


@router.get("/resumen")
def obtener_resumen(
    use_case: ObtenerResumenAdminPort = Depends(get_resumen_admin_use_case),
):
    with error_interno("Error al consultar el resumen de administración"):
        return use_case.ejecutar()


@router.get("/usuarios")
def listar_usuarios(
    use_case: ListarUsuariosAdminPort = Depends(get_listar_usuarios_admin_use_case),
):
    with error_interno("Error al consultar los usuarios"):
        return use_case.ejecutar()
