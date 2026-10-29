from fastapi import APIRouter, Depends

from app.config.dependencies import get_agregar_favorito_use_case, get_quitar_favorito_use_case
from app.domain.ports.in_.favorito_ports import AgregarFavoritoPort, QuitarFavoritoPort
from app.infraestructure.adaptadores.inbound.rest.errores import error_interno
from app.infraestructure.adaptadores.inbound.rest.seguridad import obtener_id_usuario_autenticado

router = APIRouter(prefix="/caballos", tags=["favoritos"])


@router.post("/{id_caballo}/favorito")
def agregar_favorito(
    id_caballo: int,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: AgregarFavoritoPort = Depends(get_agregar_favorito_use_case),
):
    with error_interno("Error al agregar favorito"):
        id_favorito = use_case.ejecutar(id_usuario, id_caballo)

    if id_favorito is None:
        return {"mensaje": "El caballo ya está en favoritos"}

    return {"mensaje": "Agregado a favoritos", "id_favorito": id_favorito}


@router.delete("/{id_caballo}/favorito")
def quitar_favorito(
    id_caballo: int,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: QuitarFavoritoPort = Depends(get_quitar_favorito_use_case),
):
    with error_interno("Error al quitar favorito"):
        quitado = use_case.ejecutar(id_usuario, id_caballo)

    if not quitado:
        return {"mensaje": "El caballo no estaba en favoritos"}

    return {"mensaje": "Eliminado de favoritos"}
