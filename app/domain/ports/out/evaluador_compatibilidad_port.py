from abc import ABC, abstractmethod

from app.domain.entities.compatibilidad import DatosEvaluacion, ResultadoCompatibilidad


class EvaluadorCompatibilidadPort(ABC):
    """Servicio de IA que estima la compatibilidad. Cambiar de proveedor = otro adaptador."""

    @abstractmethod
    def evaluar(self, datos: DatosEvaluacion) -> ResultadoCompatibilidad: ...
