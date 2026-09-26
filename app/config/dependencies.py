from app.application.use_cases.login_use_case import LoginUseCase
from app.application.use_cases.registrar_use_case import RegistrarUseCase
from app.application.use_cases.registrar_caballo_use_case import RegistrarCaballoUseCase

from app.domain.ports.in_.login_port import LoginPort
from app.domain.ports.in_.registrar_caballo_port import RegistrarCaballoPort
from app.domain.ports.in_.registrar_usuario_port import RegistrarUsuarioPort

from app.infraestructure.adaptadores.outbound.argon2_password_hasher import (
    Argon2PasswordHasher,
)

from app.infraestructure.adaptadores.outbound.persistence.caballo_repository_mysql import (
    CaballoRepositoryMySQL,
)
from app.infraestructure.adaptadores.outbound.persistence.publicacion_repository_mysql import (
    PublicacionRepositoryMySQL,
)
from app.infraestructure.adaptadores.outbound.persistence.raza_repository_mysql import (
    RazaRepositoryMySQL,
)
from app.infraestructure.adaptadores.outbound.persistence.usuario_repository_mysql import (
    UsuarioRepositoryMySQL,
)


_usuario_repo = UsuarioRepositoryMySQL()
_hasher = Argon2PasswordHasher()
_caballo_repo = CaballoRepositoryMySQL()
_raza_repo = RazaRepositoryMySQL()
_publicacion_repo = PublicacionRepositoryMySQL()


def get_login_use_case() -> LoginPort:
    return LoginUseCase(
        usuario_repo=_usuario_repo,
        hasher=_hasher
    )


def get_registrar_use_case() -> RegistrarUsuarioPort:
    return RegistrarUseCase(
        _usuario_repo,
        _hasher
    )


def get_registrar_caballo_use_case() -> RegistrarCaballoPort:
    return RegistrarCaballoUseCase(
        caballo_repo=_caballo_repo,
        raza_repo=_raza_repo,
        publicacion_repo=_publicacion_repo,
    )


def get_publicacion_repo():
    return _publicacion_repo


def get_usuario_repo():
    return _usuario_repo