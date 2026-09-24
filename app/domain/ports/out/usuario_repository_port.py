from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.Usuario import Usuario


class UsuarioRepositoryPort(ABC):
    @abstractmethod
    def create(self, usuario: Usuario) -> Usuario: ...

    @abstractmethod
    def find_by_email(self, correo: str) -> Optional[Usuario]: ...