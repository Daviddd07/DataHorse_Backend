from app.domain.entities.Usuario import Usuario
from app.domain.ports.in_.registrar_port import RegistrarPort
from app.domain.ports.out.password_hasher_port import PasswordHasherPort
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort


class EmailAlreadyExistsError(Exception):
    pass


class RegistrarUseCase(RegistrarPort):
    def __init__(self, usuario_repo: UsuarioRepositoryPort, hasher: PasswordHasherPort):
        self.usuario_repo = usuario_repo
        self.hasher = hasher

    def execute(self, correo: str, password: str, nombre: str) -> Usuario:
        if self.usuario_repo.find_by_email(correo) is not None:
            raise EmailAlreadyExistsError("Ese correo ya está registrado")

        password_hash = self.hasher.hash(password)
        return self.usuario_repo.create(correo=correo, password_hash=password_hash, nombre=nombre)
