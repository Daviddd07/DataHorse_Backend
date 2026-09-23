from abc import ABC, abstractmethod

from app.domain.entities.Usuario import User


class RegisterPort(ABC):
    @abstractmethod
    def execute(self, correo: str, password: str, nombre: str) -> User:
        ...