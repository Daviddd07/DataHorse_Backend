from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from app.domain.entities.Usuario import Usuario
from app.domain.ports.in_.foto_ports import ArchivoSubido


@dataclass
class ActualizarPerfilComando:
    """Lo único que el usuario puede cambiar de su perfil (nunca correo, rol ni estado)."""
    nombre: str
    telefono: Optional[str]
    ciudad: Optional[str]
    departamento: Optional[str]


class ObtenerPerfilPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int) -> Usuario: ...


class ActualizarPerfilPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int, comando: ActualizarPerfilComando) -> Usuario: ...


class CambiarFotoPerfilPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int, archivo: ArchivoSubido) -> Usuario: ...


class QuitarFotoPerfilPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int) -> Usuario: ...
