from abc import ABC, abstractmethod
from typing import Optional


class AuditoriaPort(ABC):
    @abstractmethod
    def registrar(
        self,
        accion: str,
        modulo: str,
        resultado: str,
        usuario_id: Optional[int] = None,
        detalle: Optional[str] = None,
    ) -> None:
        """Guarda un evento de auditoría. No debe interrumpir la operación si falla."""
