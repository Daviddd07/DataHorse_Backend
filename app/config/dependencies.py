from app.application.use_cases.login_use_case import LoginUseCase
from app.application.use_cases.registrar_use_case import RegistrarUseCase
from app.domain.ports.in_.login_port import LoginPort
from app.domain.ports.in_.registrar_usuario_port import RegistrarUsuarioPort
from app.infraestructure.adaptadores.outbound.argon2_password_hasher import Argon2PasswordHasher
from app.infraestructure.adaptadores.outbound.usuario_repository_mysql import UsuarioRepositoryMySQL

# TEMPORAL: un solo repositorio en memoria y un solo hasher, compartidos por
# toda la app. Cuando exista la base de datos, aquí cambias el repositorio.
_usuario_repo = UsuarioRepositoryMySQL()
_hasher = Argon2PasswordHasher()


def get_login_use_case() -> LoginPort:
    return LoginUseCase(usuario_repo=_usuario_repo, hasher=_hasher)


def get_registrar_use_case() -> RegistrarUsuarioPort:
    return RegistrarUseCase(_usuario_repo, _hasher)