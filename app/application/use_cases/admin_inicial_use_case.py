from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.config.settings import ESTADO_INICIAL
from app.domain.entities.Usuario import ROL_ADMINISTRADOR_ID, Usuario
from app.domain.ports.out.password_hasher_port import PasswordHasherPort
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort
from app.domain.services.validador_usuario import validar_registro


@dataclass
class DatosAdminInicial:
    correo: str
    contrasena: str
    nombre: str = "Administrador"


class CrearAdminInicialUseCase:
    """Crea el primer administrador si su correo todavía no existe.

    Nunca modifica un usuario existente: si el correo ya está registrado
    no cambia ni su contraseña ni su rol.
    """

    def __init__(self, repositorio: UsuarioRepositoryPort, hasher: PasswordHasherPort):
        self._repositorio = repositorio
        self._hasher = hasher

    def ejecutar(self, datos: DatosAdminInicial) -> Optional[Usuario]:
        correo = datos.correo.strip().lower()
        nombre = datos.nombre.strip() or "Administrador"

        validar_registro(nombre, correo, datos.contrasena, None, None)

        if self._repositorio.find_by_email(correo):
            return None

        return self._repositorio.create(Usuario(
            id_usuario=None,
            id_rol=ROL_ADMINISTRADOR_ID,
            nombre=nombre,
            correo=correo,
            contrasena=self._hasher.hashear(datos.contrasena),
            telefono=None,
            ubicacion=None,
            fecha_registro=date.today(),
            estado=ESTADO_INICIAL,
        ))
