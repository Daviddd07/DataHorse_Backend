from abc import ABC, abstractmethod


class LoginPort(ABC):
    @abstractmethod
    def execute(self, correo: str, password: str) -> str:
        ...