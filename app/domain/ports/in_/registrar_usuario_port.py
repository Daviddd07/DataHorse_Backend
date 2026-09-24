from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from app.domain.entities.Usuario import Usuario


@dataclass(frozen=True)
class RegistrarUsuarioComando:
    nombre: str
    correo: str
    contrasena: str
    telefono: Optional[str] = None
    ubicacion: Optional[str] = None


class RegistrarUsuarioPort(ABC):
    @abstractmethod
    def ejecutar(self, comando: RegistrarUsuarioComando) -> Usuario: ...
