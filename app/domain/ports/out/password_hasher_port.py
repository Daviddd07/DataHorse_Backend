from abc import ABC, abstractmethod


class PasswordHasherPort(ABC):
    @abstractmethod
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        ...

    @abstractmethod
    def hash(self, plain_password: str) -> str:
        ...