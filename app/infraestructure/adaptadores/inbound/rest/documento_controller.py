from datetime import datetime
from typing import List
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.config.dependencies import (
    get_eliminar_documento_use_case,
    get_listar_documentos_use_case,
    get_obtener_archivo_documento_use_case,
    get_subir_documentos_use_case,
)
from app.domain.entities.documento_caballo import TIPOS_DOCUMENTO, DocumentoCaballo
from app.domain.exceptions import SolicitudInvalidaError
from app.domain.ports.in_.documento_ports import (
    ArchivoDocumento,
    DocumentoNuevo,
    EliminarDocumentoPort,
    ListarDocumentosPort,
    ObtenerArchivoDocumentoPort,
    SubirDocumentosPort,
)
from app.domain.ports.in_.foto_ports import ArchivoSubido
from app.infraestructure.adaptadores.inbound.rest.errores import error_interno
from app.infraestructure.adaptadores.inbound.rest.seguridad import obtener_id_usuario_autenticado

router = APIRouter(prefix="/caballos", tags=["documentos"])


class DocumentoResponse(BaseModel):
    id_documento: int
    tipo: str
    tipo_etiqueta: str
    titulo: str
    content_type: str
    es_pdf: bool
    tamano_bytes: int
    estado_verificacion: str
    fecha_subida: datetime | None = None


class DocumentosResponse(BaseModel):
    es_propietario: bool
    documentos: List[DocumentoResponse]


def _a_respuesta(d: DocumentoCaballo) -> DocumentoResponse:
    return DocumentoResponse(
        id_documento=d.id_documento,
        tipo=d.tipo,
        tipo_etiqueta=d.tipo_etiqueta,
        titulo=d.titulo,
        content_type=d.content_type,
        es_pdf=d.es_pdf,
        tamano_bytes=d.tamano_bytes,
        estado_verificacion=d.estado_verificacion,
        fecha_subida=d.fecha_subida,
    )


def _respuesta_archivo(archivo: ArchivoDocumento, disposicion: str) -> Response:
    nombre = quote(archivo.documento.nombre_original)
    return Response(
        content=archivo.contenido,
        media_type=archivo.documento.content_type,
        headers={
            "Content-Disposition": f"{disposicion}; filename*=UTF-8''{nombre}",
            # Que ni el navegador ni un proxy guarden copia del documento
            "Cache-Control": "no-store, private",
            # Se sirve exactamente como el tipo validado al subirlo
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/documentos/tipos")
def listar_tipos_documento():
    return [{"valor": valor, "etiqueta": etiqueta} for valor, etiqueta in TIPOS_DOCUMENTO.items()]


@router.post("/{id_caballo}/documentos", response_model=List[DocumentoResponse])
async def subir_documentos(
    id_caballo: int,
    files: List[UploadFile] = File(...),
    tipos: List[str] = Form(...),
    titulos: List[str] = Form(...),
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: SubirDocumentosPort = Depends(get_subir_documentos_use_case),
):
    # Cada archivo va con su tipo y su título, en el mismo orden
    if not len(files) == len(tipos) == len(titulos):
        raise SolicitudInvalidaError("Cada documento necesita su tipo y su título")

    nuevos = [
        DocumentoNuevo(
            tipo=tipo,
            titulo=titulo,
            archivo=ArchivoSubido(
                nombre=f.filename or "documento",
                content_type=f.content_type or "",
                contenido=await f.read(),
            ),
        )
        for f, tipo, titulo in zip(files, tipos, titulos)
    ]

    return [_a_respuesta(d) for d in use_case.ejecutar(id_caballo, id_usuario, nuevos)]


@router.get("/{id_caballo}/documentos", response_model=DocumentosResponse)
def listar_documentos(
    id_caballo: int,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ListarDocumentosPort = Depends(get_listar_documentos_use_case),
):
    with error_interno("Error al consultar los documentos"):
        resultado = use_case.ejecutar(id_caballo, id_usuario)

    return DocumentosResponse(
        es_propietario=resultado.es_propietario,
        documentos=[_a_respuesta(d) for d in resultado.documentos],
    )


@router.get("/{id_caballo}/documentos/{id_documento}/contenido")
def ver_documento(
    id_caballo: int,
    id_documento: int,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ObtenerArchivoDocumentoPort = Depends(get_obtener_archivo_documento_use_case),
):
    """Para el visor de la página. Requiere sesión; no se ofrece como descarga."""
    with error_interno("Error al abrir el documento"):
        archivo = use_case.ejecutar(id_caballo, id_documento, id_usuario, descargar=False)
    return _respuesta_archivo(archivo, "inline")


@router.get("/{id_caballo}/documentos/{id_documento}/descarga")
def descargar_documento(
    id_caballo: int,
    id_documento: int,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ObtenerArchivoDocumentoPort = Depends(get_obtener_archivo_documento_use_case),
):
    """Solo el propietario."""
    with error_interno("Error al descargar el documento"):
        archivo = use_case.ejecutar(id_caballo, id_documento, id_usuario, descargar=True)
    return _respuesta_archivo(archivo, "attachment")


@router.delete("/{id_caballo}/documentos/{id_documento}")
def eliminar_documento(
    id_caballo: int,
    id_documento: int,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: EliminarDocumentoPort = Depends(get_eliminar_documento_use_case),
):
    with error_interno("Error al eliminar el documento"):
        use_case.ejecutar(id_caballo, id_documento, id_usuario)

    return {"mensaje": "Documento eliminado correctamente", "id_documento": id_documento}
