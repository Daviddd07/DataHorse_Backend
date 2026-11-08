from datetime import datetime
from typing import Callable, List, Optional

from app.domain.entities.resena import (
    CALIFICACION_MAXIMA,
    CALIFICACION_MINIMA,
    LONGITUD_MAXIMA_COMENTARIO,
    EstadoConexion,
    Resena,
    ResumenCalificacion,
)
from app.domain.exceptions import ConflictoError, SolicitudInvalidaError
from app.domain.ports.in_.conversacion_ports import VerificarParticipantePort
from app.domain.ports.in_.resena_ports import (
    CalificarUsuarioPort,
    ObtenerCalificacionPort,
    ObtenerEstadoConexionPort,
    RegistrarConexionPort,
)
from app.domain.ports.out.auditoria_port import AuditoriaPort
from app.domain.ports.out.presencia_port import EnLineaPort, UltimaConexionRepositoryPort
from app.domain.ports.out.resena_repository_port import ResenaRepositoryPort

MODULO_RESENAS = "RESENAS"


class CalificarUsuarioUseCase(CalificarUsuarioPort):
    def __init__(
        self,
        verificador: VerificarParticipantePort,
        repo: ResenaRepositoryPort,
        auditoria: AuditoriaPort,
        reloj: Callable[[], datetime],
    ):
        self._verificador = verificador
        self._repo = repo
        self._auditoria = auditoria
        self._reloj = reloj

    def ejecutar(
        self, id_usuario: int, id_conversacion: int, calificacion: int, comentario: Optional[str]
    ) -> Resena:
        if (
            isinstance(calificacion, bool)
            or not isinstance(calificacion, int)
            or not CALIFICACION_MINIMA <= calificacion <= CALIFICACION_MAXIMA
        ):
            raise SolicitudInvalidaError(
                f"La calificación debe ser de {CALIFICACION_MINIMA} a {CALIFICACION_MAXIMA} estrellas"
            )
        texto = (comentario or "").strip() or None
        if texto is not None and len(texto) > LONGITUD_MAXIMA_COMENTARIO:
            raise SolicitudInvalidaError(
                f"El comentario no puede superar {LONGITUD_MAXIMA_COMENTARIO} caracteres"
            )

        conversacion = self._verificador.ejecutar(id_usuario, id_conversacion)
        if not conversacion.esta_finalizada():
            raise SolicitudInvalidaError("Solo puedes calificar cuando el chat esté finalizado")
        if self._repo.existe(id_conversacion, id_usuario):
            raise ConflictoError("Ya calificaste a esta persona en esta conversación")

        id_evaluado = conversacion.otro_participante(id_usuario)
        resena = self._repo.crear(
            id_conversacion, id_usuario, id_evaluado, calificacion, texto, self._reloj().date()
        )

        self._auditoria.registrar(
            accion="CALIFICAR_USUARIO",
            modulo=MODULO_RESENAS,
            resultado="EXITOSO",
            usuario_id=id_usuario,
            detalle=(
                f"Calificó con {calificacion} estrellas al usuario {id_evaluado} "
                f"(conversación {id_conversacion})."
            ),
        )
        return resena


class ObtenerCalificacionUseCase(ObtenerCalificacionPort):
    def __init__(self, repo: ResenaRepositoryPort):
        self._repo = repo

    def ejecutar(self, id_usuario: int) -> ResumenCalificacion:
        return self._repo.resumen_de(id_usuario)


class ObtenerEstadoConexionUseCase(ObtenerEstadoConexionPort):
    def __init__(self, en_linea: EnLineaPort, ultima_conexion: UltimaConexionRepositoryPort):
        self._en_linea = en_linea
        self._ultima_conexion = ultima_conexion

    def ejecutar(self, ids_usuario: List[int]) -> dict[int, EstadoConexion]:
        ids = list(dict.fromkeys(ids_usuario))
        if not ids:
            return {}
        ultimas = self._ultima_conexion.obtener(ids)
        return {
            id_usuario: EstadoConexion(
                en_linea=self._en_linea.esta_en_linea(id_usuario),
                ultima_conexion=ultimas.get(id_usuario),
            )
            for id_usuario in ids
        }


class RegistrarConexionUseCase(RegistrarConexionPort):
    def __init__(self, ultima_conexion: UltimaConexionRepositoryPort, reloj: Callable[[], datetime]):
        self._ultima_conexion = ultima_conexion
        self._reloj = reloj

    def ejecutar(self, id_usuario: int) -> None:
        self._ultima_conexion.registrar(id_usuario, self._reloj())
