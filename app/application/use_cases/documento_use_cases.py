from typing import List

from app.application.use_cases.caballo_use_cases import obtener_caballo_activo
from app.domain.entities.documento_caballo import ContextoCaballo, DocumentoCaballo
from app.domain.exceptions import (
    AccesoDenegadoError,
    ErrorInternoError,
    RecursoNoEncontradoError,
    SolicitudInvalidaError,
)
from app.domain.ports.in_.documento_ports import (
    ArchivoDocumento,
    DocumentoNuevo,
    DocumentosDeCaballo,
    EliminarDocumentoPort,
    ListarDocumentosPort,
    ObtenerArchivoDocumentoPort,
    SubirDocumentosPort,
)
from app.domain.ports.out.almacenamiento_archivos_port import AlmacenamientoArchivosPort
from app.domain.ports.out.auditoria_port import AuditoriaPort
from app.domain.ports.out.caballo_repository_port import CaballoRepositoryPort
from app.domain.ports.out.documento_repository_port import DocumentoRepositoryPort
from app.domain.services.validador_documento import (
    DOCUMENTOS_MAX_POR_CABALLO,
    validar_archivo,
    validar_tipo,
    validar_titulo,
)

MODULO_DOCUMENTOS = "DOCUMENTOS"
NO_ENCONTRADO = "Documento no encontrado"


def _contexto_visible(repo: DocumentoRepositoryPort, id_caballo: int, id_usuario: int) -> ContextoCaballo:
    """El dueño siempre ve sus documentos; los demás, solo si el caballo está publicado.

    En cualquier otro caso se responde 404, sin revelar si el caballo existe.
    """
    contexto = repo.contexto_caballo(id_caballo)
    if contexto is None or contexto.eliminado:
        raise RecursoNoEncontradoError("Caballo no encontrado")
    if contexto.id_propietario != id_usuario and not contexto.publicado:
        raise RecursoNoEncontradoError("Caballo no encontrado")
    return contexto


class SubirDocumentosUseCase(SubirDocumentosPort):
    def __init__(
        self,
        caballo_repo: CaballoRepositoryPort,
        documento_repo: DocumentoRepositoryPort,
        almacenamiento: AlmacenamientoArchivosPort,
        auditoria: AuditoriaPort,
    ):
        self._caballo_repo = caballo_repo
        self._documento_repo = documento_repo
        self._almacenamiento = almacenamiento
        self._auditoria = auditoria

    def _auditar(self, resultado: str, id_usuario: int, detalle: str) -> None:
        self._auditoria.registrar(
            accion="SUBIR_DOCUMENTOS",
            modulo=MODULO_DOCUMENTOS,
            resultado=resultado,
            usuario_id=id_usuario,
            detalle=detalle,
        )

    def ejecutar(
        self, id_caballo: int, id_usuario: int, nuevos: List[DocumentoNuevo]
    ) -> List[DocumentoCaballo]:
        caballo = obtener_caballo_activo(self._caballo_repo, id_caballo, id_usuario)

        try:
            if not caballo.es_macho:
                raise SolicitudInvalidaError(
                    "Solo los caballos machos pueden tener documentos de respaldo"
                )
            if not nuevos:
                raise SolicitudInvalidaError("No se envió ningún documento")

            existentes = self._documento_repo.contar_por_caballo(id_caballo)
            if existentes + len(nuevos) > DOCUMENTOS_MAX_POR_CABALLO:
                raise SolicitudInvalidaError(
                    f"Máximo {DOCUMENTOS_MAX_POR_CABALLO} documentos por caballo "
                    f"(ya tiene {existentes})"
                )

            # Se valida todo antes de guardar nada, para no dejar subidas a medias.
            validados = [
                (
                    validar_tipo(n.tipo),
                    validar_titulo(n.titulo),
                    *validar_archivo(n.archivo.nombre, n.archivo.contenido),
                    n.archivo,
                )
                for n in nuevos
            ]
        except SolicitudInvalidaError as e:
            self._auditar(
                "FALLIDO", id_usuario,
                f"No se pudieron subir documentos del caballo {id_caballo}: {e.mensaje}",
            )
            raise

        guardados: List[DocumentoCaballo] = []
        rutas: List[str] = []
        try:
            for tipo, titulo, extension, content_type, archivo in validados:
                ruta = self._almacenamiento.guardar(extension, archivo.contenido)
                rutas.append(ruta)
                guardados.append(self._documento_repo.guardar(DocumentoCaballo(
                    id_documento=None,
                    id_caballo=id_caballo,
                    tipo=tipo,
                    titulo=titulo,
                    ruta=ruta,
                    nombre_original=archivo.nombre[:255],
                    content_type=content_type,
                    tamano_bytes=len(archivo.contenido),
                )))
        except Exception as e:
            # Deshace lo ya escrito para no dejar archivos huérfanos ni registros sin archivo
            for documento in guardados:
                self._documento_repo.eliminar(documento.id_documento)
            for ruta in rutas:
                self._almacenamiento.eliminar(ruta)
            self._auditar(
                "FALLIDO", id_usuario,
                f"Error guardando documentos del caballo {id_caballo}: {e}",
            )
            raise ErrorInternoError("No se pudieron guardar los documentos") from e

        self._auditar(
            "EXITOSO", id_usuario,
            f"Se subieron {len(guardados)} documentos al caballo {id_caballo}.",
        )
        return guardados


class ListarDocumentosUseCase(ListarDocumentosPort):
    def __init__(self, documento_repo: DocumentoRepositoryPort):
        self._documento_repo = documento_repo

    def ejecutar(self, id_caballo: int, id_usuario: int) -> DocumentosDeCaballo:
        contexto = _contexto_visible(self._documento_repo, id_caballo, id_usuario)
        return DocumentosDeCaballo(
            documentos=self._documento_repo.listar_por_caballo(id_caballo),
            es_propietario=contexto.id_propietario == id_usuario,
        )


class ObtenerArchivoDocumentoUseCase(ObtenerArchivoDocumentoPort):
    def __init__(self, documento_repo: DocumentoRepositoryPort, almacenamiento: AlmacenamientoArchivosPort):
        self._documento_repo = documento_repo
        self._almacenamiento = almacenamiento

    def ejecutar(
        self, id_caballo: int, id_documento: int, id_usuario: int, descargar: bool
    ) -> ArchivoDocumento:
        contexto = _contexto_visible(self._documento_repo, id_caballo, id_usuario)

        if descargar and contexto.id_propietario != id_usuario:
            raise AccesoDenegadoError("Solo el propietario puede descargar este documento")

        documento = self._documento_repo.obtener(id_caballo, id_documento)
        if documento is None:
            raise RecursoNoEncontradoError(NO_ENCONTRADO)

        try:
            contenido = self._almacenamiento.leer(documento.ruta)
        except FileNotFoundError as e:
            raise RecursoNoEncontradoError("El archivo del documento ya no existe") from e

        return ArchivoDocumento(documento=documento, contenido=contenido)


class EliminarDocumentoUseCase(EliminarDocumentoPort):
    def __init__(
        self,
        caballo_repo: CaballoRepositoryPort,
        documento_repo: DocumentoRepositoryPort,
        almacenamiento: AlmacenamientoArchivosPort,
        auditoria: AuditoriaPort,
    ):
        self._caballo_repo = caballo_repo
        self._documento_repo = documento_repo
        self._almacenamiento = almacenamiento
        self._auditoria = auditoria

    def ejecutar(self, id_caballo: int, id_documento: int, id_usuario: int) -> None:
        obtener_caballo_activo(self._caballo_repo, id_caballo, id_usuario)

        documento = self._documento_repo.obtener(id_caballo, id_documento)
        if documento is None:
            raise RecursoNoEncontradoError(NO_ENCONTRADO)

        self._documento_repo.eliminar(id_documento)

        # Si falla el borrado del archivo, el documento ya no aparece en ningún lado:
        # solo queda registrado para limpiarlo a mano.
        try:
            self._almacenamiento.eliminar(documento.ruta)
            resultado, detalle = "EXITOSO", f"Se eliminó el documento {id_documento} del caballo {id_caballo}."
        except Exception as e:
            resultado = "FALLIDO"
            detalle = (
                f"El documento {id_documento} del caballo {id_caballo} se retiró de la base, "
                f"pero no se pudo borrar su archivo {documento.ruta}: {e}"
            )

        self._auditoria.registrar(
            accion="ELIMINAR_DOCUMENTO",
            modulo=MODULO_DOCUMENTOS,
            resultado=resultado,
            usuario_id=id_usuario,
            detalle=detalle,
        )
