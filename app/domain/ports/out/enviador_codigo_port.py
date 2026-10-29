from abc import ABC, abstractmethod


class EnviadorCodigoPort(ABC):
    @abstractmethod
    def enviar(
        self,
        correo: str,
        nombre: str,
        codigo: str,
        tipo: str,
        minutos_validez: int,
    ) -> None:
        """Envía el código al usuario. Lanza ServicioExternoError o ConfiguracionError."""
