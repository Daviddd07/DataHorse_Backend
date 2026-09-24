from abc import ABC, abstractmethod

from app.domain.entities.Usuario import Usuario


class  UsuarioRepositoryPort(ABC):
    @abstractmethod
    def find_by_email(self, correo: str) -> Usuario | None:
        ...

    @abstractmethod
    def create(self, correo: str, password_hash: str, nombre: str) -> Usuario:
        ...