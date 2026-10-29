from datetime import date

from app.config.settings import ESTADO_INICIAL, ROL_USUARIO_ID
from app.domain.entities.Usuario import Usuario
from app.domain.exceptions import EmailAlreadyExistsError
from app.domain.ports.in_.registrar_usuario_port import RegistrarUsuarioComando, RegistrarUsuarioPort
from app.domain.ports.out.geocoding_port import GeocodingPort
from app.domain.ports.out.password_hasher_port import PasswordHasherPort
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort
from app.domain.services.validador_usuario import validar_registro

__all__ = ["EmailAlreadyExistsError", "RegistrarUseCase"]


class RegistrarUseCase(RegistrarUsuarioPort):
    def __init__(
        self,
        repositorio: UsuarioRepositoryPort,
        hasher: PasswordHasherPort,
        geocoding: GeocodingPort,
    ):
        self._repositorio = repositorio
        self._hasher = hasher
        self._geocoding = geocoding

    def ejecutar(self, c: RegistrarUsuarioComando) -> Usuario:
        nombre = c.nombre.strip()
        correo = c.correo.strip().lower()
        telefono = (c.telefono or "").strip() or None
        ubicacion = (c.ubicacion or "").strip() or None

        validar_registro(nombre, correo, c.contrasena, telefono, ubicacion)

        if self._repositorio.find_by_email(correo):
            raise EmailAlreadyExistsError()

        geo = self._geocoding.geocodificar(ubicacion) if ubicacion else None

        usuario = Usuario(
            id_usuario=None,
            id_rol=ROL_USUARIO_ID,
            nombre=nombre,
            correo=correo,
            contrasena=self._hasher.hashear(c.contrasena),
            telefono=telefono,
            ubicacion=ubicacion,
            ubicacion_lat=geo.lat if geo else None,
            ubicacion_lng=geo.lng if geo else None,
            ubicacion_texto=geo.texto if geo else ubicacion,
            ciudad=geo.ciudad if geo else None,
            departamento=geo.departamento if geo else None,
            fecha_registro=date.today(),
            estado=ESTADO_INICIAL,
        )
        return self._repositorio.create(usuario)
