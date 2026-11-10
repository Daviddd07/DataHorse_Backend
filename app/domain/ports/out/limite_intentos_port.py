from abc import ABC, abstractmethod


class LimiteIntentosPort(ABC):
    """Cuenta intentos fallidos por clave (p. ej. un correo) dentro de una ventana de tiempo."""

    @abstractmethod
    def segundos_bloqueado(self, clave: str) -> int:
        """Segundos que faltan para poder volver a intentar; 0 si no está bloqueada."""

    @abstractmethod
    def registrar_fallo(self, clave: str) -> None: ...

    @abstractmethod
    def limpiar(self, clave: str) -> None:
        """Olvida los fallos de la clave (tras un acceso correcto)."""
