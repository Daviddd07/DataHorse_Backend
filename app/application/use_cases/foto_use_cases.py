from pathlib import Path
from typing import List

from app.application.use_cases.caballo_use_cases import obtener_caballo_activo
from app.config.settings import FOTO_ALLOWED_TYPES, FOTO_EXT_ALLOWED, FOTO_MAX_SIZE
from app.domain.entities.foto_caballo import FotoCaballo
from app.domain.exceptions import (
    ErrorInternoError,
    RecursoNoEncontradoError,
    SolicitudInvalidaError,
)
from app.domain.ports.in_.foto_ports import ArchivoSubido, EliminarFotoPort, SubirFotosPort
from app.domain.ports.out.almacenamiento_archivos_port import AlmacenamientoArchivosPort
from app.domain.ports.out.auditoria_port import AuditoriaPort
from app.domain.ports.out.caballo_repository_port import CaballoRepositoryPort
from app.domain.ports.out.foto_repository import FotoRepository

MODULO_FOTOS = "FOTOGRAFIAS"


def validar_archivo(archivo: ArchivoSubido) -> str:
    """Valida tipo, tamaño y extensión. Devuelve la extensión en minúsculas."""
    if archivo.content_type not in FOTO_ALLOWED_TYPES:
        raise SolicitudInvalidaError(f"Tipo no permitido: {archivo.content_type}")

    if len(archivo.contenido) > FOTO_MAX_SIZE:
        raise SolicitudInvalidaError(f"{archivo.nombre} excede 5MB")

    extension = Path(archivo.nombre).suffix.lower()
    if extension not in FOTO_EXT_ALLOWED:
        raise SolicitudInvalidaError(f"Extensión no permitida: {extension}")

    return extension


class SubirFotosUseCase(SubirFotosPort):
    def __init__(
        self,
        caballo_repo: CaballoRepositoryPort,
        foto_repo: FotoRepository,
        almacenamiento: AlmacenamientoArchivosPort,
        auditoria: AuditoriaPort,
    ):
        self._caballo_repo = caballo_repo
        self._foto_repo = foto_repo
        self._almacenamiento = almacenamiento
        self._auditoria = auditoria

    def ejecutar(
        self,
        id_caballo: int,
        id_usuario: int,
        archivos: List[ArchivoSubido],
    ) -> List[FotoCaballo]:
        obtener_caballo_activo(self._caballo_repo, id_caballo, id_usuario)

        # Se validan todos antes de escribir nada, para no dejar subidas a medias.
        try:
            extensiones = [validar_archivo(a) for a in archivos]
        except SolicitudInvalidaError as e:
            self._auditoria.registrar(
                accion="SUBIR_FOTOGRAFIAS",
                modulo=MODULO_FOTOS,
                resultado="FALLIDO",
                usuario_id=id_usuario,
                detalle=f"No se pudieron subir fotografías del caballo {id_caballo}: {e.mensaje}",
            )
            raise

        ya_tiene_fotos = self._foto_repo.contar_por_caballo(id_caballo) > 0
        guardadas: List[FotoCaballo] = []

        for orden, (archivo, extension) in enumerate(zip(archivos, extensiones)):
            ruta = self._almacenamiento.guardar(extension, archivo.contenido)
            foto = FotoCaballo(
                id_foto=None,
                id_caballo=id_caballo,
                ruta=ruta,
                es_principal=(not ya_tiene_fotos) and orden == 0,
                orden=orden,
            )
            guardadas.append(self._foto_repo.guardar(foto))

        self._auditoria.registrar(
            accion="SUBIR_FOTOGRAFIAS",
            modulo=MODULO_FOTOS,
            resultado="EXITOSO",
            usuario_id=id_usuario,
            detalle=f"Se subieron {len(guardadas)} fotografías al caballo {id_caballo}.",
        )

        return guardadas


class EliminarFotoUseCase(EliminarFotoPort):
    def __init__(
        self,
        caballo_repo: CaballoRepositoryPort,
        foto_repo: FotoRepository,
        almacenamiento: AlmacenamientoArchivosPort,
        auditoria: AuditoriaPort,
    ):
        self._caballo_repo = caballo_repo
        self._foto_repo = foto_repo
        self._almacenamiento = almacenamiento
        self._auditoria = auditoria

    def ejecutar(self, id_caballo: int, id_foto: int, id_usuario: int) -> None:
        obtener_caballo_activo(self._caballo_repo, id_caballo, id_usuario)

        foto = self._foto_repo.obtener_por_id(id_foto)
        if foto is None or foto.id_caballo != id_caballo:
            raise RecursoNoEncontradoError("Foto no encontrada")

        self._foto_repo.eliminar(id_foto)

        try:
            self._almacenamiento.eliminar(foto.ruta)
        except Exception as e:
            self._auditoria.registrar(
                accion="ELIMINAR_FOTOGRAFIA",
                modulo=MODULO_FOTOS,
                resultado="FALLIDO",
                usuario_id=id_usuario,
                detalle=(
                    f"El registro de la fotografía {id_foto} fue eliminado de la base de datos, "
                    f"pero falló el borrado del archivo físico del caballo {id_caballo}: {e}"
                ),
            )
            raise ErrorInternoError(
                "La fotografía fue retirada de la base de datos, "
                "pero no se pudo eliminar su archivo físico."
            ) from e

        self._foto_repo.promover_principal(id_caballo)

        self._auditoria.registrar(
            accion="ELIMINAR_FOTOGRAFIA",
            modulo=MODULO_FOTOS,
            resultado="EXITOSO",
            usuario_id=id_usuario,
            detalle=f"Se eliminó la fotografía {id_foto} del caballo {id_caballo}.",
        )
