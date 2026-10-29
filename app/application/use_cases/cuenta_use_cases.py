import logging
import secrets

from app.application.services.codigo_verificacion_service import (
    TIPO_RECUPERAR_PASSWORD,
    TIPO_REGISTRO,
    CodigoVerificacionService,
)
from app.domain.entities.Usuario import Usuario
from app.domain.exceptions import (
    AccesoDenegadoError,
    ConfiguracionError,
    ConflictoError,
    CorreoYaRegistradoError,
    ErrorInternoError,
    InvalidCredentialsError,
    NoAutenticadoError,
    RecursoNoEncontradoError,
    ServicioExternoError,
    SolicitudInvalidaError,
)
from app.domain.ports.in_.cuenta_ports import (
    AutenticarConGooglePort,
    CuentaRegistrada,
    IniciarSesionPort,
    ObtenerUsuarioActualPort,
    ReenviarCodigoPort,
    RegistrarCuentaPort,
    RestablecerContrasenaPort,
    SolicitarRecuperacionPort,
    VerificarCorreoPort,
)
from app.domain.ports.in_.login_port import LoginPort
from app.domain.ports.in_.registrar_usuario_port import (
    RegistrarUsuarioComando,
    RegistrarUsuarioPort,
)
from app.domain.ports.out.auditoria_port import AuditoriaPort
from app.domain.ports.out.password_hasher_port import PasswordHasherPort
from app.domain.ports.out.usuario_google_repository_port import UsuarioGoogleRepositoryPort
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort
from app.domain.ports.out.verificador_google_port import VerificadorGooglePort
from app.domain.services.validador_usuario import validar_nueva_contrasena

logger = logging.getLogger(__name__)

ESTADO_ACTIVO = "activo"
ESTADO_PENDIENTE = "pendiente"
MODULO_AUTENTICACION = "AUTENTICACION"


def _normalizar_correo(correo: str) -> str:
    return correo.strip().lower()


def _esta_activo(usuario: Usuario) -> bool:
    return (usuario.estado or "").lower() == ESTADO_ACTIVO


def _buscar_por_correo(repo: UsuarioRepositoryPort, correo: str) -> Usuario:
    usuario = repo.find_by_email(_normalizar_correo(correo))

    if usuario is None:
        raise RecursoNoEncontradoError("Usuario no encontrado")

    return usuario


class RegistrarCuentaUseCase(RegistrarCuentaPort):
    """Crea el usuario en estado pendiente y le envía el código de verificación."""

    def __init__(
        self,
        registrar: RegistrarUsuarioPort,
        usuario_repo: UsuarioRepositoryPort,
        codigos: CodigoVerificacionService,
    ):
        self._registrar = registrar
        self._usuario_repo = usuario_repo
        self._codigos = codigos

    def ejecutar(self, comando: RegistrarUsuarioComando) -> CuentaRegistrada:
        usuario = self._registrar.ejecutar(comando)
        self._usuario_repo.actualizar_estado(usuario.id_usuario, ESTADO_PENDIENTE)

        try:
            self._codigos.emitir(usuario, TIPO_REGISTRO)
            correo_enviado = True
        except (ServicioExternoError, ConfiguracionError) as e:
            # La cuenta queda creada; el usuario puede pedir que se reenvíe el código.
            logger.warning("Usuario %s creado, pero falló el correo: %s", usuario.id_usuario, e.mensaje)
            correo_enviado = False

        return CuentaRegistrada(usuario=usuario, correo_enviado=correo_enviado)


class VerificarCorreoUseCase(VerificarCorreoPort):
    def __init__(self, usuario_repo: UsuarioRepositoryPort, codigos: CodigoVerificacionService):
        self._usuario_repo = usuario_repo
        self._codigos = codigos

    def ejecutar(self, correo: str, codigo: str) -> bool:
        usuario = _buscar_por_correo(self._usuario_repo, correo)

        if _esta_activo(usuario):
            return False

        self._codigos.validar(usuario.id_usuario, codigo, TIPO_REGISTRO)
        self._usuario_repo.actualizar_estado(usuario.id_usuario, ESTADO_ACTIVO)
        return True


class ReenviarCodigoUseCase(ReenviarCodigoPort):
    def __init__(self, usuario_repo: UsuarioRepositoryPort, codigos: CodigoVerificacionService):
        self._usuario_repo = usuario_repo
        self._codigos = codigos

    def ejecutar(self, correo: str) -> bool:
        usuario = _buscar_por_correo(self._usuario_repo, correo)

        if _esta_activo(usuario):
            return False

        self._codigos.emitir(usuario, TIPO_REGISTRO)
        return True


class IniciarSesionUseCase(IniciarSesionPort):
    """Valida credenciales (LoginPort), exige cuenta activa y deja rastro de auditoría."""

    def __init__(
        self,
        login: LoginPort,
        usuario_repo: UsuarioRepositoryPort,
        auditoria: AuditoriaPort,
    ):
        self._login = login
        self._usuario_repo = usuario_repo
        self._auditoria = auditoria

    def _auditar(self, resultado: str, detalle: str, usuario_id: int | None = None) -> None:
        self._auditoria.registrar(
            accion="LOGIN",
            modulo=MODULO_AUTENTICACION,
            resultado=resultado,
            usuario_id=usuario_id,
            detalle=detalle,
        )

    def ejecutar(self, correo: str, password: str) -> int:
        try:
            id_usuario = int(self._login.execute(correo, password))
        except InvalidCredentialsError:
            self._auditar("FALLIDO", "Credenciales incorrectas")
            raise

        usuario = self._usuario_repo.find_by_id(id_usuario)

        if usuario is None:
            self._auditar("FALLIDO", "Usuario no encontrado")
            raise NoAutenticadoError("Usuario no encontrado")

        if not _esta_activo(usuario):
            self._auditar("DENEGADO", "Usuario sin acceso por estado inactivo", usuario.id_usuario)
            raise AccesoDenegadoError("Debes verificar tu correo antes de iniciar sesión")

        self._auditar("EXITOSO", "Inicio de sesión correcto", usuario.id_usuario)
        return usuario.id_usuario


class AutenticarConGoogleUseCase(AutenticarConGooglePort):
    def __init__(
        self,
        verificador: VerificadorGooglePort,
        registrar: RegistrarUsuarioPort,
        usuario_repo: UsuarioRepositoryPort,
        google_repo: UsuarioGoogleRepositoryPort,
    ):
        self._verificador = verificador
        self._registrar = registrar
        self._usuario_repo = usuario_repo
        self._google_repo = google_repo

    def ejecutar(self, credencial: str) -> Usuario:
        datos = self._verificador.verificar(credencial)

        google_sub = datos.get("sub")
        correo = datos.get("email")
        nombre = datos.get("name")

        if not (google_sub and correo and datos.get("email_verified")):
            raise NoAutenticadoError("La cuenta de Google no pudo verificarse")

        correo = _normalizar_correo(correo)
        nombre = nombre.strip() if nombre else correo.split("@")[0]

        id_vinculado = self._google_repo.obtener_id_usuario(google_sub)

        if id_vinculado is not None:
            usuario = self._usuario_repo.find_by_id(id_vinculado)
            if usuario is None:
                raise NoAutenticadoError("Usuario no encontrado")
        else:
            usuario = self._obtener_o_crear(correo, nombre)
            self._vincular(usuario, google_sub)

        # Google ya verificó el correo.
        self._usuario_repo.actualizar_estado(usuario.id_usuario, ESTADO_ACTIVO)
        return usuario

    def _obtener_o_crear(self, correo: str, nombre: str) -> Usuario:
        usuario = self._usuario_repo.find_by_email(correo)

        if usuario is None:
            try:
                usuario = self._registrar.ejecutar(
                    RegistrarUsuarioComando(
                        nombre=nombre,
                        correo=correo,
                        # Contraseña aleatoria que cumple la política; el usuario entra con Google.
                        contrasena="Aa1!" + secrets.token_urlsafe(32),
                    )
                )
            except CorreoYaRegistradoError:
                usuario = self._usuario_repo.find_by_email(correo)

        if usuario is None:
            raise ErrorInternoError("No fue posible crear el usuario")

        return usuario

    def _vincular(self, usuario: Usuario, google_sub: str) -> None:
        sub_existente = self._google_repo.obtener_sub(usuario.id_usuario)

        if sub_existente is None:
            self._google_repo.vincular(usuario.id_usuario, google_sub)
        elif sub_existente != google_sub:
            raise ConflictoError("Esta cuenta ya está vinculada con otra cuenta de Google")


class SolicitarRecuperacionUseCase(SolicitarRecuperacionPort):
    def __init__(self, usuario_repo: UsuarioRepositoryPort, codigos: CodigoVerificacionService):
        self._usuario_repo = usuario_repo
        self._codigos = codigos

    def ejecutar(self, correo: str) -> None:
        usuario = self._usuario_repo.find_by_email(_normalizar_correo(correo))

        # Si el correo no existe no se informa, para no revelar qué cuentas hay.
        if usuario is not None:
            self._codigos.emitir(usuario, TIPO_RECUPERAR_PASSWORD)


class RestablecerContrasenaUseCase(RestablecerContrasenaPort):
    def __init__(
        self,
        usuario_repo: UsuarioRepositoryPort,
        codigos: CodigoVerificacionService,
        hasher: PasswordHasherPort,
    ):
        self._usuario_repo = usuario_repo
        self._codigos = codigos
        self._hasher = hasher

    def ejecutar(self, correo: str, codigo: str, nueva_contrasena: str) -> None:
        usuario = self._usuario_repo.find_by_email(_normalizar_correo(correo))

        if usuario is None:
            raise SolicitudInvalidaError("Correo o código inválido")

        validar_nueva_contrasena(nueva_contrasena)
        self._codigos.validar(usuario.id_usuario, codigo, TIPO_RECUPERAR_PASSWORD)

        self._usuario_repo.actualizar_contrasena(
            usuario.id_usuario,
            self._hasher.hashear(nueva_contrasena),
        )
        self._usuario_repo.actualizar_estado(usuario.id_usuario, ESTADO_ACTIVO)


class ObtenerUsuarioActualUseCase(ObtenerUsuarioActualPort):
    def __init__(self, usuario_repo: UsuarioRepositoryPort):
        self._usuario_repo = usuario_repo

    def ejecutar(self, id_usuario: int) -> Usuario:
        usuario = self._usuario_repo.find_by_id(id_usuario)

        if usuario is None:
            raise NoAutenticadoError("Usuario no encontrado")

        return usuario
