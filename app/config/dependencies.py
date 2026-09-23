from app.application.use_cases.login_use_case import LoginUseCase
from app.application.use_cases.registrar_use_case import RegistrarUseCase
from app.domain.ports.in_.login_port import LoginPort
from app.domain.ports.in_.registrar_port import RegistrarPort
from app.infraestructure.adaptadores.outbound.persistence.memory_usuario_repository import (
    MemoryUsuarioRepository,
)
from app.infraestructure.adaptadores.outbound.security.password_hasher import PasswordHasher

# TEMPORAL: un solo repositorio en memoria compartido por toda la app,
# mientras no exista base de datos real. Cuando la tengas, aquí es
# donde cambias MemoryUsuarioRepository() por tu repositorio con SQLAlchemy
# (posiblemente inyectado con Depends(get_db) en cada función).
_usuario_repo = MemoryUsuarioRepository()
_hasher = PasswordHasher()


def get_login_use_case() -> LoginPort:
    return LoginUseCase(usuario_repo=_usuario_repo, hasher=_hasher)


def get_registrar_use_case() -> RegistrarPort:
    return RegistrarUseCase(usuario_repo=_usuario_repo, hasher=_hasher)
