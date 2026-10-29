import hmac
import secrets
from datetime import datetime, timedelta

from app.domain.entities.Usuario import Usuario
from app.domain.exceptions import DemasiadosIntentosError, SolicitudInvalidaError
from app.domain.ports.out.codigo_hasher_port import CodigoHasherPort
from app.domain.ports.out.codigo_verificacion_repository_port import (
    CodigoVerificacionRepositoryPort,
)
from app.domain.ports.out.enviador_codigo_port import EnviadorCodigoPort

TIPO_REGISTRO = "REGISTRO"
TIPO_RECUPERAR_PASSWORD = "RECUPERAR_PASSWORD"

CODIGO_EXPIRA_MINUTOS = 10
MAX_INTENTOS_CODIGO = 5


class CodigoVerificacionService:
    """Emite y valida los códigos de 6 dígitos que se envían por correo."""

    def __init__(
        self,
        repositorio: CodigoVerificacionRepositoryPort,
        hasher: CodigoHasherPort,
        enviador: EnviadorCodigoPort,
    ):
        self._repositorio = repositorio
        self._hasher = hasher
        self._enviador = enviador

    def emitir(self, usuario: Usuario, tipo: str) -> None:
        codigo = f"{secrets.randbelow(1_000_000):06d}"

        self._repositorio.reemplazar(
            id_usuario=usuario.id_usuario,
            tipo=tipo,
            codigo_hash=self._hasher.hashear(codigo),
            fecha_expiracion=datetime.now() + timedelta(minutes=CODIGO_EXPIRA_MINUTOS),
        )

        self._enviador.enviar(
            correo=usuario.correo,
            nombre=usuario.nombre,
            codigo=codigo,
            tipo=tipo,
            minutos_validez=CODIGO_EXPIRA_MINUTOS,
        )

    def validar(self, id_usuario: int, codigo: str, tipo: str) -> None:
        registro = self._repositorio.obtener_vigente(id_usuario, tipo)

        if registro is None:
            raise SolicitudInvalidaError("No existe un código válido")

        if registro.fecha_expiracion < datetime.now():
            self._repositorio.marcar_usado(registro.id_verificacion)
            raise SolicitudInvalidaError("El código ha expirado")

        if registro.intentos >= MAX_INTENTOS_CODIGO:
            self._repositorio.marcar_usado(registro.id_verificacion)
            raise DemasiadosIntentosError("Superaste el máximo de intentos")

        if not hmac.compare_digest(self._hasher.hashear(codigo), registro.codigo_hash):
            self._repositorio.registrar_intento_fallido(
                registro.id_verificacion,
                MAX_INTENTOS_CODIGO,
            )
            raise SolicitudInvalidaError("Código incorrecto")

        self._repositorio.marcar_usado(registro.id_verificacion)
