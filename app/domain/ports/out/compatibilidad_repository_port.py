from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Optional

from app.domain.entities.compatibilidad import (
    EjemplarEvaluado,
    EvaluacionGuardada,
    ResultadoCompatibilidad,
)


class CompatibilidadRepositoryPort(ABC):
    @abstractmethod
    def obtener_ejemplar(self, id_caballo: int) -> Optional[EjemplarEvaluado]: ...

    @abstractmethod
    def porcentaje_razas(self, id_raza_yegua: int, id_raza_caballo: int) -> Optional[float]:
        """Porcentaje de referencia de la tabla compatibilidad_razas, si existe el par."""

    @abstractmethod
    def buscar_resultado(
        self, id_caballo: int, id_yegua: int, huella: str
    ) -> Optional[ResultadoCompatibilidad]:
        """Última evaluación guardada del par con exactamente los mismos datos."""

    @abstractmethod
    def contar_evaluaciones_desde(self, id_usuario: int, desde: datetime) -> int:
        """Evaluaciones nuevas (llamadas a la IA) del usuario desde `desde` (UTC)."""

    @abstractmethod
    def guardar(
        self,
        id_usuario: int,
        id_caballo: int,
        id_yegua: int,
        huella: str,
        fecha: date,
        resultado: ResultadoCompatibilidad,
    ) -> int:
        """Guarda la solicitud y su resultado en una transacción; devuelve el id de la solicitud."""

    @abstractmethod
    def listar_de_usuario(self, id_usuario: int) -> List[dict]:
        """Resumen de los estudios del usuario (par, puntaje, confianza y fecha), más recientes primero."""

    @abstractmethod
    def obtener_evaluacion(self, id_solicitud: int) -> Optional[EvaluacionGuardada]: ...
