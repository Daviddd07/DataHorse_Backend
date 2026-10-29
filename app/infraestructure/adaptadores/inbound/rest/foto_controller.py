from typing import List

from fastapi import APIRouter, Depends, File, UploadFile

from app.config.dependencies import get_eliminar_foto_use_case, get_subir_fotos_use_case
from app.domain.ports.in_.foto_ports import ArchivoSubido, EliminarFotoPort, SubirFotosPort
from app.infraestructure.adaptadores.inbound.rest.errores import error_interno
from app.infraestructure.adaptadores.inbound.rest.foto_schemas import FotoCaballoResponse
from app.infraestructure.adaptadores.inbound.rest.seguridad import obtener_id_usuario_autenticado

router = APIRouter(prefix="/caballos", tags=["fotos"])


@router.post("/{id_caballo}/fotos", response_model=List[FotoCaballoResponse])
async def subir_fotos(
    id_caballo: int,
    files: List[UploadFile] = File(...),
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: SubirFotosPort = Depends(get_subir_fotos_use_case),
):
    archivos = [
        ArchivoSubido(nombre=f.filename, content_type=f.content_type, contenido=await f.read())
        for f in files
    ]

    fotos = use_case.ejecutar(id_caballo, id_usuario, archivos)

    return [
        FotoCaballoResponse(
            id_foto=f.id_foto,
            ruta=f"/{f.ruta}",
            es_principal=f.es_principal,
            orden=f.orden,
            fecha_subida=f.fecha_subida,
        )
        for f in fotos
    ]


@router.delete("/{id_caballo}/fotos/{id_foto}")
def eliminar_foto(
    id_caballo: int,
    id_foto: int,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: EliminarFotoPort = Depends(get_eliminar_foto_use_case),
):
    with error_interno("Error al eliminar la foto"):
        use_case.ejecutar(id_caballo, id_foto, id_usuario)

    return {"mensaje": "Foto eliminada correctamente", "id_foto": id_foto}
