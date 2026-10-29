from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.Usuario import Usuario


class UsuarioRepositoryPort(ABC):
    @abstractmethod
    def create(self, usuario: Usuario) -> Usuario: ...

    @abstractmethod
    def find_by_email(self, correo: str) -> Optional[Usuario]: ...

    @abstractmethod
    def find_by_id(self, id_usuario: int) -> Optional[Usuario]: ...

    @abstractmethod
    def actualizar_estado(self, id_usuario: int, estado: str) -> None: ...

    @abstractmethod
    def actualizar_contrasena(self, id_usuario: int, contrasena_hash: str) -> None: ...
