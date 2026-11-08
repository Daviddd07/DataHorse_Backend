from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from app.domain.entities.resena import Resena, ResumenCalificacion


class ResenaRepositoryPort(ABC):
    @abstractmethod
    def existe(self, id_conversacion: int, id_evaluador: int) -> bool:
        """True si id_evaluador ya calificó al otro participante de esa conversación."""

    @abstractmethod
    def crear(
        self,
        id_conversacion: int,
        id_evaluador: int,
        id_evaluado: int,
        calificacion: int,
        comentario: Optional[str],
        fecha: date,
    ) -> Resena:
        """Lanza ConflictoError si ya existía (dos solicitudes simultáneas)."""

    @abstractmethod
    def resumen_de(self, id_usuario: int) -> ResumenCalificacion: ...
