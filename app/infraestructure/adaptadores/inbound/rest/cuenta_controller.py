from fastapi import APIRouter, Depends, File, UploadFile

from app.config.dependencies import (
    get_actualizar_perfil_use_case,
    get_cambiar_foto_perfil_use_case,
    get_obtener_perfil_use_case,
    get_quitar_foto_perfil_use_case,
)
from app.config.settings import FOTO_MAX_SIZE
from app.domain.entities.Usuario import Usuario
from app.domain.ports.in_.foto_ports import ArchivoSubido
from app.domain.ports.in_.perfil_ports import (
    ActualizarPerfilComando,
    ActualizarPerfilPort,
    CambiarFotoPerfilPort,
    ObtenerPerfilPort,
    QuitarFotoPerfilPort,
)
from app.infraestructure.adaptadores.inbound.rest.errores import error_interno
from app.infraestructure.adaptadores.inbound.rest.schemas import (
    ActualizarPerfilRequest,
    PerfilResponse,
    ruta_publica,
)
from app.infraestructure.adaptadores.inbound.rest.seguridad import obtener_id_usuario_autenticado

router = APIRouter(prefix="/cuenta", tags=["cuenta"])


def _a_respuesta(usuario: Usuario) -> PerfilResponse:
    return PerfilResponse(
        id=usuario.id_usuario,
        nombre=usuario.nombre,
        correo=usuario.correo,
        telefono=usuario.telefono,
        ciudad=usuario.ciudad,
        departamento=usuario.departamento,
        fecha_registro=usuario.fecha_registro,
        es_admin=usuario.es_administrador(),
        solo_google=usuario.requiere_contrasena(),
        foto_perfil=ruta_publica(usuario.foto_perfil),
    )


@router.get("/perfil", response_model=PerfilResponse)
def obtener_perfil(
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ObtenerPerfilPort = Depends(get_obtener_perfil_use_case),
):
    with error_interno("Error al consultar el perfil"):
        return _a_respuesta(use_case.ejecutar(id_usuario))


@router.patch("/perfil", response_model=PerfilResponse)
def actualizar_perfil(
    body: ActualizarPerfilRequest,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ActualizarPerfilPort = Depends(get_actualizar_perfil_use_case),
):
    comando = ActualizarPerfilComando(
        nombre=body.nombre,
        telefono=body.telefono,
        ciudad=body.ciudad,
        departamento=body.departamento,
    )
    with error_interno("Error al actualizar el perfil"):
        return _a_respuesta(use_case.ejecutar(id_usuario, comando))


@router.put("/foto", response_model=PerfilResponse)
async def cambiar_foto_perfil(
    foto: UploadFile = File(...),
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: CambiarFotoPerfilPort = Depends(get_cambiar_foto_perfil_use_case),
):
    # Se lee como máximo un byte de más: basta para saber que excede el límite sin cargar todo
    archivo = ArchivoSubido(
        nombre=foto.filename or "",
        content_type=foto.content_type or "",
        contenido=await foto.read(FOTO_MAX_SIZE + 1),
    )
    with error_interno("Error al guardar la foto de perfil"):
        return _a_respuesta(use_case.ejecutar(id_usuario, archivo))


@router.delete("/foto", response_model=PerfilResponse)
def quitar_foto_perfil(
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: QuitarFotoPerfilPort = Depends(get_quitar_foto_perfil_use_case),
):
    with error_interno("Error al quitar la foto de perfil"):
        return _a_respuesta(use_case.ejecutar(id_usuario))
