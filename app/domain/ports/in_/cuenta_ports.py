from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domain.entities.Usuario import Usuario
from app.domain.ports.in_.registrar_usuario_port import RegistrarUsuarioComando


@dataclass(frozen=True)
class CuentaRegistrada:
    usuario: Usuario
    correo_enviado: bool


class RegistrarCuentaPort(ABC):
    @abstractmethod
    def ejecutar(self, comando: RegistrarUsuarioComando) -> CuentaRegistrada: ...


class VerificarCorreoPort(ABC):
    @abstractmethod
    def ejecutar(self, correo: str, codigo: str) -> bool:
        """Devuelve False si la cuenta ya estaba verificada."""


class ReenviarCodigoPort(ABC):
    @abstractmethod
    def ejecutar(self, correo: str) -> bool:
        """Devuelve False si la cuenta ya estaba verificada."""


class IniciarSesionPort(ABC):
    @abstractmethod
    def ejecutar(self, correo: str, password: str) -> int:
        """Devuelve el id del usuario autenticado."""


class AutenticarConGooglePort(ABC):
    @abstractmethod
    def ejecutar(self, credencial: str) -> Usuario: ...


class SolicitarRecuperacionPort(ABC):
    @abstractmethod
    def ejecutar(self, correo: str) -> None: ...


class RestablecerContrasenaPort(ABC):
    @abstractmethod
    def ejecutar(self, correo: str, codigo: str, nueva_contrasena: str) -> None: ...


class ObtenerUsuarioActualPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int) -> Usuario: ...
