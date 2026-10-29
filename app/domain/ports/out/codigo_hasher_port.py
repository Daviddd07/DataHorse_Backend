from abc import ABC, abstractmethod


class CodigoHasherPort(ABC):
    @abstractmethod
    def hashear(self, codigo: str) -> str: ...
