from datetime import datetime, timedelta, timezone
from typing import Callable, List, Optional

from app.domain.entities.conversacion import (
    ESTADO_CONVERSACION_ACTIVA,
    ESTADO_CONVERSACION_FINALIZADA,
    LONGITUD_MAXIMA_MENSAJE,
    Conversacion,
    Mensaje,
)
from app.domain.exceptions import (
    AccesoDenegadoError,
    ConflictoError,
    RecursoNoEncontradoError,
    SolicitudInvalidaError,
)
from app.domain.ports.in_.conversacion_ports import (
    AbrirConversacionPort,
    ContarNoLeidosPort,
    EnviarMensajePort,
    FinalizarConversacionPort,
    MarcarLeidosPort,
    ListarConversacionesPort,
    ObtenerConversacionPort,
    VerificarParticipantePort,
)
from app.domain.ports.out.auditoria_port import AuditoriaPort
from app.domain.ports.in_.resena_ports import ObtenerEstadoConexionPort
from app.domain.ports.out.conversacion_repository_port import ConversacionRepositoryPort
from app.domain.ports.out.resena_repository_port import ResenaRepositoryPort

MODULO_CONVERSACIONES = "CONVERSACIONES"
LIMITE_HISTORIAL = 200


def reloj_local(zona_horaria_horas: int) -> Callable[[], datetime]:
    """Hora local sin tzinfo, que es como se guarda en las columnas DATETIME."""
    zona = timezone(timedelta(hours=zona_horaria_horas))
    return lambda: datetime.now(zona).replace(tzinfo=None, microsecond=0)


class AbrirConversacionUseCase(AbrirConversacionPort):
    def __init__(
        self,
        repo: ConversacionRepositoryPort,
        auditoria: AuditoriaPort,
        reloj: Callable[[], datetime],
    ):
        self._repo = repo
        self._auditoria = auditoria
        self._reloj = reloj

    def ejecutar(self, id_usuario: int, id_publicacion: int) -> int:
        existente = self._repo.buscar_id(id_publicacion, id_usuario)
        if existente is not None:
            # Volver a pulsar "Chatear" reabre una conversación finalizada
            self._repo.cambiar_estado(existente, ESTADO_CONVERSACION_ACTIVA)
            return existente

        id_dueno = self._repo.obtener_dueno_publicacion_activa(id_publicacion)
        if id_dueno is None:
            raise RecursoNoEncontradoError("Publicación no encontrada")
        if id_dueno == id_usuario:
            raise SolicitudInvalidaError("No puedes iniciar una conversación sobre tu propia publicación")

        id_conversacion = self._repo.crear(id_publicacion, id_usuario, self._reloj().date())

        self._auditoria.registrar(
            accion="ABRIR_CONVERSACION",
            modulo=MODULO_CONVERSACIONES,
            resultado="EXITOSO",
            usuario_id=id_usuario,
            detalle=f"Conversación {id_conversacion} sobre la publicación {id_publicacion}.",
        )

        return id_conversacion


def _con_conexion(resumenes: List[dict], estado_conexion: Optional[ObtenerEstadoConexionPort]) -> None:
    """Agrega a cada otro participante si está en línea y cuándo se conectó por última vez."""
    if estado_conexion is None or not resumenes:
        return
    estados = estado_conexion.ejecutar([r["otro_usuario"]["id"] for r in resumenes])
    for resumen in resumenes:
        estado = estados.get(resumen["otro_usuario"]["id"])
        resumen["otro_usuario"]["conexion"] = estado.a_dict() if estado else None


class ListarConversacionesUseCase(ListarConversacionesPort):
    def __init__(
        self,
        repo: ConversacionRepositoryPort,
        estado_conexion: Optional[ObtenerEstadoConexionPort] = None,
    ):
        self._repo = repo
        self._estado_conexion = estado_conexion

    def ejecutar(self, id_usuario: int) -> List[dict]:
        resumenes = self._repo.listar_de_usuario(id_usuario)
        _con_conexion(resumenes, self._estado_conexion)
        return resumenes


class VerificarParticipanteUseCase(VerificarParticipantePort):
    def __init__(self, repo: ConversacionRepositoryPort):
        self._repo = repo

    def ejecutar(self, id_usuario: int, id_conversacion: int) -> Conversacion:
        conversacion = self._repo.obtener(id_conversacion)
        if conversacion is None:
            raise RecursoNoEncontradoError("Conversación no encontrada")
        if not conversacion.es_participante(id_usuario):
            raise AccesoDenegadoError("No perteneces a esta conversación")
        return conversacion


class ObtenerConversacionUseCase(ObtenerConversacionPort):
    def __init__(
        self,
        repo: ConversacionRepositoryPort,
        verificador: VerificarParticipantePort,
        resena_repo: Optional[ResenaRepositoryPort] = None,
        estado_conexion: Optional[ObtenerEstadoConexionPort] = None,
    ):
        self._repo = repo
        self._verificador = verificador
        self._resena_repo = resena_repo
        self._estado_conexion = estado_conexion

    def ejecutar(self, id_usuario: int, id_conversacion: int) -> dict:
        self._verificador.ejecutar(id_usuario, id_conversacion)
        resumen = self._repo.obtener_resumen(id_conversacion, id_usuario)
        if resumen is not None:
            if self._resena_repo is not None:
                resumen["ya_califique"] = self._resena_repo.existe(id_conversacion, id_usuario)
            _con_conexion([resumen], self._estado_conexion)
        mensajes = self._repo.listar_mensajes(id_conversacion, LIMITE_HISTORIAL)
        return {
            "conversacion": resumen,
            "mensajes": [m.a_dict() for m in mensajes],
        }


class ContarNoLeidosUseCase(ContarNoLeidosPort):
    def __init__(self, repo: ConversacionRepositoryPort):
        self._repo = repo

    def ejecutar(self, id_usuario: int) -> int:
        return self._repo.contar_no_leidos(id_usuario)


class MarcarLeidosUseCase(MarcarLeidosPort):
    def __init__(self, repo: ConversacionRepositoryPort, verificador: VerificarParticipantePort):
        self._repo = repo
        self._verificador = verificador

    def ejecutar(self, id_usuario: int, id_conversacion: int) -> int:
        self._verificador.ejecutar(id_usuario, id_conversacion)
        return self._repo.marcar_leidos(id_conversacion, id_usuario)


class FinalizarConversacionUseCase(FinalizarConversacionPort):
    def __init__(
        self,
        repo: ConversacionRepositoryPort,
        verificador: VerificarParticipantePort,
        auditoria: AuditoriaPort,
    ):
        self._repo = repo
        self._verificador = verificador
        self._auditoria = auditoria

    def ejecutar(self, id_usuario: int, id_conversacion: int) -> Conversacion:
        conversacion = self._verificador.ejecutar(id_usuario, id_conversacion)
        if self._repo.cambiar_estado(id_conversacion, ESTADO_CONVERSACION_FINALIZADA):
            self._auditoria.registrar(
                accion="FINALIZAR_CONVERSACION",
                modulo=MODULO_CONVERSACIONES,
                resultado="EXITOSO",
                usuario_id=id_usuario,
                detalle=f"Conversación {id_conversacion} finalizada.",
            )
        return conversacion


class EnviarMensajeUseCase(EnviarMensajePort):
    def __init__(
        self,
        repo: ConversacionRepositoryPort,
        verificador: VerificarParticipantePort,
        reloj: Callable[[], datetime],
    ):
        self._repo = repo
        self._verificador = verificador
        self._reloj = reloj

    def ejecutar(self, id_usuario: int, id_conversacion: int, contenido: str) -> Mensaje:
        texto = (contenido or "").strip()
        if not texto:
            raise SolicitudInvalidaError("El mensaje no puede estar vacío")
        if len(texto) > LONGITUD_MAXIMA_MENSAJE:
            raise SolicitudInvalidaError(
                f"El mensaje no puede superar {LONGITUD_MAXIMA_MENSAJE} caracteres"
            )

        # Se verifica en cada mensaje: si la conversación desaparece, deja de aceptar mensajes.
        conversacion = self._verificador.ejecutar(id_usuario, id_conversacion)
        if conversacion.esta_finalizada():
            raise ConflictoError("La conversación está finalizada")

        return self._repo.guardar_mensaje(id_conversacion, id_usuario, texto, self._reloj())
