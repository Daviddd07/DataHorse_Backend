from datetime import date

from app.config.settings import ESTADO_INICIAL, ROL_USUARIO_ID
from app.domain.entities.Usuario import Usuario
from app.domain.exceptions import EmailAlreadyExistsError
from app.domain.ports.in_.registrar_usuario_port import RegistrarUsuarioComando, RegistrarUsuarioPort
from app.domain.ports.out.password_hasher_port import PasswordHasherPort
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort
from app.domain.services.validador_usuario import validar_registro


class RegistrarUseCase(RegistrarUsuarioPort):
    def __init__(self, repositorio: UsuarioRepositoryPort, hasher: PasswordHasherPort):
        self._repositorio = repositorio
        self._hasher = hasher

    def ejecutar(self, c: RegistrarUsuarioComando) -> Usuario:
        nombre = c.nombre.strip()
        correo = c.correo.strip().lower()
        telefono = (c.telefono or "").strip() or None
        ubicacion = (c.ubicacion or "").strip() or None

        validar_registro(nombre, correo, c.contrasena, telefono, ubicacion)

        if self._repositorio.find_by_email(correo):
            raise EmailAlreadyExistsError()

        usuario = Usuario(
            id_usuario=None,
            id_rol=ROL_USUARIO_ID,                          # lo decide el servidor
            nombre=nombre,
            correo=correo,
            contrasena=self._hasher.hashear(c.contrasena),  # nunca texto plano
            telefono=telefono,
            ubicacion=ubicacion,
            fecha_registro=date.today(),                    # lo decide el servidor
            estado=ESTADO_INICIAL,                          # lo decide el servidor
        )
        return self._repositorio.create(usuario)
