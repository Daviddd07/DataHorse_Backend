from abc import ABC, abstractmethod


class PasswordHasherPort(ABC):
    @abstractmethod
    def verificar(self, plain_password: str, hashed_password: str) -> bool:
        ...

    @abstractmethod
    def hashear(self, plain_password: str) -> str:
        ...