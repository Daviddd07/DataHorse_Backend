"""Raíz de composición: el único lugar que conoce las implementaciones concretas.

Los controllers y casos de uso dependen de puertos; aquí se decide qué adaptador
los cumple. Para cambiar MySQL, Mailjet o Nominatim por otra cosa solo se toca este archivo.
"""
import os

from dotenv import load_dotenv
from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.services.codigo_verificacion_service import CodigoVerificacionService
from app.application.use_cases.caballo_use_cases import (
    ActualizarCaballoUseCase,
    EliminarCaballoUseCase,
    ListarMisCaballosUseCase,
    ListarUbicacionesUseCase,
    ObtenerCaballoUseCase,
)
from app.application.use_cases.cuenta_use_cases import (
    AutenticarConGoogleUseCase,
    IniciarSesionUseCase,
    ObtenerUsuarioActualUseCase,
    ReenviarCodigoUseCase,
    RegistrarCuentaUseCase,
    RestablecerContrasenaUseCase,
    SolicitarRecuperacionUseCase,
    VerificarCorreoUseCase,
)
from app.application.use_cases.favorito_use_cases import (
    AgregarFavoritoUseCase,
    QuitarFavoritoUseCase,
)
from app.application.use_cases.foto_use_cases import EliminarFotoUseCase, SubirFotosUseCase
from app.application.use_cases.listar_razas_use_case import ListarRazasUseCase
from app.application.use_cases.login_use_case import LoginUseCase
from app.application.use_cases.publicacion_use_cases import (
    ListarPublicacionesUseCase,
    ObtenerPublicacionUseCase,
)
from app.application.use_cases.registrar_caballo_use_case import RegistrarCaballoUseCase
from app.application.use_cases.registrar_logs_use_case import RegistrarLogsUseCase
from app.application.use_cases.registrar_use_case import RegistrarUseCase
from app.config.settings import FOTO_CABALLO_DIR, FOTO_CABALLO_URL_PREFIX
from app.domain.ports.in_.caballo_ports import (
    ActualizarCaballoPort,
    EliminarCaballoPort,
    ListarMisCaballosPort,
    ListarUbicacionesPort,
    ObtenerCaballoPort,
)
from app.domain.ports.in_.cuenta_ports import (
    AutenticarConGooglePort,
    IniciarSesionPort,
    ObtenerUsuarioActualPort,
    ReenviarCodigoPort,
    RegistrarCuentaPort,
    RestablecerContrasenaPort,
    SolicitarRecuperacionPort,
    VerificarCorreoPort,
)
from app.domain.ports.in_.favorito_ports import AgregarFavoritoPort, QuitarFavoritoPort
from app.domain.ports.in_.foto_ports import EliminarFotoPort, SubirFotosPort
from app.domain.ports.in_.listar_razas_port import ListarRazasPort
from app.domain.ports.in_.login_port import LoginPort
from app.domain.ports.in_.publicacion_ports import ListarPublicacionesPort, ObtenerPublicacionPort
from app.domain.ports.in_.registrar_caballo_port import RegistrarCaballoPort
from app.domain.ports.in_.registrar_logs_port import RegistrarLogsPort
from app.domain.ports.in_.registrar_usuario_port import RegistrarUsuarioPort
from app.domain.ports.out.foto_repository import FotoRepository
from app.domain.ports.out.token_port import TokenPort
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort
from app.infraestructure.adaptadores.outbound.almacenamiento.almacenamiento_local import (
    AlmacenamientoLocal,
)
from app.infraestructure.adaptadores.outbound.argon2_password_hasher import Argon2PasswordHasher
from app.infraestructure.adaptadores.outbound.correo.mailjet_enviador import MailjetEnviadorCodigo
from app.infraestructure.adaptadores.outbound.geocoding.nominatim_geocoding import (
    NominatimGeocoding,
)
from app.infraestructure.adaptadores.outbound.persistence.audit_log_service import AuditoriaMySQL
from app.infraestructure.adaptadores.outbound.persistence.caballo_repository_mysql import (
    CaballoConsultasMySQL,
    CaballoRepositoryMySQL,
)
from app.infraestructure.adaptadores.outbound.persistence.codigo_verificacion_repository_mysql import (
    CodigoVerificacionRepositoryMySQL,
)
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import get_db
from app.infraestructure.adaptadores.outbound.persistence.favorito_repository_mysql import (
    FavoritoRepositoryMySQL,
)
from app.infraestructure.adaptadores.outbound.persistence.log_repository_mysql import (
    LogRepositoryMySQL,
)
from app.infraestructure.adaptadores.outbound.persistence.foto_repository_mysql import (
    FotoRepositoryMySQL,
)
from app.infraestructure.adaptadores.outbound.persistence.publicacion_consultas_mysql import (
    PublicacionConsultasMySQL,
)
from app.infraestructure.adaptadores.outbound.persistence.raza_repository_mysql import (
    RazaRepositoryMySQL,
)
from app.infraestructure.adaptadores.outbound.persistence.ubicacion_consultas_mysql import (
    UbicacionConsultasMySQL,
)
from app.infraestructure.adaptadores.outbound.persistence.usuario_google_repository_mysql import (
    UsuarioGoogleRepositoryMySQL,
)
from app.infraestructure.adaptadores.outbound.persistence.usuario_repository_mysql import (
    UsuarioRepositoryMySQL,
)
from app.infraestructure.adaptadores.outbound.security.google_verificador import VerificadorGoogle
from app.infraestructure.adaptadores.outbound.security.hmac_codigo_hasher import HmacCodigoHasher
from app.infraestructure.adaptadores.outbound.security.jwt_handler import JwtTokenService

load_dotenv(override=True)

# ======================================================
# ADAPTADORES (sin estado, se comparten entre solicitudes)
# ======================================================

_usuario_repo = UsuarioRepositoryMySQL()
_usuario_google_repo = UsuarioGoogleRepositoryMySQL()
_hasher = Argon2PasswordHasher()
_caballo_repo = CaballoRepositoryMySQL()
_caballo_consultas = CaballoConsultasMySQL()
_raza_repo = RazaRepositoryMySQL()
_publicacion_consultas = PublicacionConsultasMySQL()
_ubicacion_consultas = UbicacionConsultasMySQL()
_favorito_repo = FavoritoRepositoryMySQL()
_log_repo = LogRepositoryMySQL()
_auditoria = AuditoriaMySQL()
_geocoding = NominatimGeocoding()
_tokens = JwtTokenService()
_almacenamiento = AlmacenamientoLocal(FOTO_CABALLO_DIR, FOTO_CABALLO_URL_PREFIX)
_verificador_google = VerificadorGoogle(os.getenv("GOOGLE_CLIENT_ID"))

_codigos = CodigoVerificacionService(
    repositorio=CodigoVerificacionRepositoryMySQL(),
    hasher=HmacCodigoHasher(os.getenv("CODIGO_SECRET")),
    enviador=MailjetEnviadorCodigo(
        api_key=os.getenv("MAILJET_API_KEY"),
        secret_key=os.getenv("MAILJET_SECRET_KEY"),
        remitente=os.getenv("MAILJET_SENDER_EMAIL"),
        nombre_remitente=os.getenv("MAILJET_SENDER_NAME", "DataHorse"),
    ),
)


def get_usuario_repo() -> UsuarioRepositoryPort:
    return _usuario_repo


def get_token_service() -> TokenPort:
    return _tokens


# ======================================================
# AUTENTICACIÓN Y CUENTA
# ======================================================

def get_login_use_case() -> LoginPort:
    return LoginUseCase(usuario_repo=_usuario_repo, hasher=_hasher)


def get_registrar_use_case() -> RegistrarUsuarioPort:
    return RegistrarUseCase(_usuario_repo, _hasher, _geocoding)


def get_registrar_cuenta_use_case() -> RegistrarCuentaPort:
    return RegistrarCuentaUseCase(get_registrar_use_case(), _usuario_repo, _codigos)


def get_verificar_correo_use_case() -> VerificarCorreoPort:
    return VerificarCorreoUseCase(_usuario_repo, _codigos)


def get_reenviar_codigo_use_case() -> ReenviarCodigoPort:
    return ReenviarCodigoUseCase(_usuario_repo, _codigos)


def get_iniciar_sesion_use_case() -> IniciarSesionPort:
    return IniciarSesionUseCase(get_login_use_case(), _usuario_repo, _auditoria)


def get_autenticar_google_use_case() -> AutenticarConGooglePort:
    return AutenticarConGoogleUseCase(
        _verificador_google,
        get_registrar_use_case(),
        _usuario_repo,
        _usuario_google_repo,
    )


def get_solicitar_recuperacion_use_case() -> SolicitarRecuperacionPort:
    return SolicitarRecuperacionUseCase(_usuario_repo, _codigos)


def get_restablecer_contrasena_use_case() -> RestablecerContrasenaPort:
    return RestablecerContrasenaUseCase(_usuario_repo, _codigos, _hasher)


def get_usuario_actual_use_case() -> ObtenerUsuarioActualPort:
    return ObtenerUsuarioActualUseCase(_usuario_repo)


# ======================================================
# RAZAS, CABALLOS Y PUBLICACIONES
# ======================================================

def get_listar_razas_use_case() -> ListarRazasPort:
    return ListarRazasUseCase(_raza_repo)


def get_registrar_caballo_use_case() -> RegistrarCaballoPort:
    return RegistrarCaballoUseCase(_caballo_repo, _raza_repo, _usuario_repo, _geocoding)


def get_listar_mis_caballos_use_case() -> ListarMisCaballosPort:
    return ListarMisCaballosUseCase(_caballo_consultas)


def get_obtener_caballo_use_case() -> ObtenerCaballoPort:
    return ObtenerCaballoUseCase(_caballo_consultas)


def get_actualizar_caballo_use_case() -> ActualizarCaballoPort:
    return ActualizarCaballoUseCase(_caballo_repo, _geocoding)


def get_eliminar_caballo_use_case() -> EliminarCaballoPort:
    return EliminarCaballoUseCase(_caballo_repo)


def get_listar_ubicaciones_use_case() -> ListarUbicacionesPort:
    return ListarUbicacionesUseCase(_ubicacion_consultas)


def get_listar_publicaciones_use_case() -> ListarPublicacionesPort:
    return ListarPublicacionesUseCase(_publicacion_consultas)


def get_obtener_publicacion_use_case() -> ObtenerPublicacionPort:
    return ObtenerPublicacionUseCase(_publicacion_consultas)


def get_agregar_favorito_use_case() -> AgregarFavoritoPort:
    return AgregarFavoritoUseCase(_caballo_repo, _favorito_repo, _auditoria)


def get_quitar_favorito_use_case() -> QuitarFavoritoPort:
    return QuitarFavoritoUseCase(_favorito_repo, _auditoria)


# ======================================================
# LOGS DEL FRONTEND
# ======================================================

def get_registrar_logs_use_case() -> RegistrarLogsPort:
    return RegistrarLogsUseCase(_log_repo)


# ======================================================
# FOTOS (el repositorio usa la sesión de la solicitud)
# ======================================================

def get_foto_repository(db: Session = Depends(get_db)) -> FotoRepository:
    return FotoRepositoryMySQL(db)


def get_subir_fotos_use_case(
    foto_repo: FotoRepository = Depends(get_foto_repository),
) -> SubirFotosPort:
    return SubirFotosUseCase(_caballo_repo, foto_repo, _almacenamiento, _auditoria)


def get_eliminar_foto_use_case(
    foto_repo: FotoRepository = Depends(get_foto_repository),
) -> EliminarFotoPort:
    return EliminarFotoUseCase(_caballo_repo, foto_repo, _almacenamiento, _auditoria)
