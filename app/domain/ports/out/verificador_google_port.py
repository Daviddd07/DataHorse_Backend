from abc import ABC, abstractmethod


class VerificadorGooglePort(ABC):
    @abstractmethod
    def verificar(self, credencial: str) -> dict:
        """Devuelve los datos del token de Google. Lanza NoAutenticadoError si es inválido."""
