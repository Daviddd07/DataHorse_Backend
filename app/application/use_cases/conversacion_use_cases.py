from datetime import datetime, timedelta, timezone
from typing import Callable, List

from app.domain.entities.conversacion import LONGITUD_MAXIMA_MENSAJE, Conversacion, Mensaje
from app.domain.exceptions import (
    AccesoDenegadoError,
    RecursoNoEncontradoError,
    SolicitudInvalidaError,
)
from app.domain.ports.in_.conversacion_ports import (
    AbrirConversacionPort,
    ContarNoLeidosPort,
    EnviarMensajePort,
    MarcarLeidosPort,
    ListarConversacionesPort,
    ObtenerConversacionPort,
    VerificarParticipantePort,
)
from app.domain.ports.out.auditoria_port import AuditoriaPort
from app.domain.ports.out.conversacion_repository_port import ConversacionRepositoryPort

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


class ListarConversacionesUseCase(ListarConversacionesPort):
    def __init__(self, repo: ConversacionRepositoryPort):
        self._repo = repo

    def ejecutar(self, id_usuario: int) -> List[dict]:
        return self._repo.listar_de_usuario(id_usuario)


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
    def __init__(self, repo: ConversacionRepositoryPort, verificador: VerificarParticipantePort):
        self._repo = repo
        self._verificador = verificador

    def ejecutar(self, id_usuario: int, id_conversacion: int) -> dict:
        self._verificador.ejecutar(id_usuario, id_conversacion)
        resumen = self._repo.obtener_resumen(id_conversacion, id_usuario)
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
        self._verificador.ejecutar(id_usuario, id_conversacion)

        return self._repo.guardar_mensaje(id_conversacion, id_usuario, texto, self._reloj())
