from app.domain.ports.in_.login_port import LoginPort
from app.domain.ports.out.password_hasher_port import PasswordHasherPort
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort


class EmailAlreadyExistsError(Exception):
    pass


class LoginUseCase(LoginPort):
    def __init__(self, usuario_repo: UsuarioRepositoryPort, hasher: PasswordHasherPort):
        self.usuario_repo = usuario_repo
        self.hasher = hasher

    def execute(self, correo: str, password: str) -> str:
        usuario = self.usuario_repo.find_by_email(correo)

        # Mismo error exista o no el correo, para no filtrar qué correos
        # están registrados (evita "user enumeration").
        if usuario is None or not self.hasher.verify(password, usuario.password_hash):
            raise EmailAlreadyExistsError("Correo o contraseña incorrectos")

        return usuario.id
class InvalidCredentialsError(Exception):
    """Correo o contraseña incorrectos."""
