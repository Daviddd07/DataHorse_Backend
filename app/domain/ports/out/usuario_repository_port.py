from abc import ABC, abstractmethod

from app.domain.entities.Usuario import User


class UserRepositoryPort(ABC):
    @abstractmethod
    def find_by_email(self, correo: str) -> User | None:
        ...

    @abstractmethod
    def create(self, correo: str, password_hash: str, nombre: str) -> User:
        ...