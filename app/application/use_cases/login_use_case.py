from app.domain.ports.in_.login_port import LoginPort
from app.domain.ports.out.password_hasher_port import PasswordHasherPort
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort


class InvalidCredentialsError(Exception):
    """Correo o contraseña incorrectos."""


class LoginUseCase(LoginPort):
    def __init__(self, usuario_repo: UsuarioRepositoryPort, hasher: PasswordHasherPort):
        self.usuario_repo = usuario_repo
        self.hasher = hasher

    def execute(self, correo: str, password: str) -> str:
        usuario = self.usuario_repo.find_by_email(correo.strip().lower())

        # Mismo error exista o no el correo, para no filtrar qué correos están registrados.
        if usuario is None or not self.hasher.verificar(password, usuario.contrasena):
            raise InvalidCredentialsError("Correo o contraseña incorrectos")

        return str(usuario.id_usuario)