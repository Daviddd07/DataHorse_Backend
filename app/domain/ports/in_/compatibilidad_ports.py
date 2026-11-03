from abc import ABC, abstractmethod
from typing import List


class EvaluarCompatibilidadPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int, id_caballo: int, id_yegua: int) -> dict:
        """Evalúa un caballo del marketplace con una yegua del usuario."""


class ConsultarCupoCompatibilidadPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int) -> dict:
        """Estimaciones usadas y restantes del usuario hoy."""


class ListarResultadosCompatibilidadPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int) -> List[dict]:
        """Estudios que hizo el usuario, del más reciente al más antiguo."""


class ObtenerResultadoCompatibilidadPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int, id_solicitud: int) -> dict:
        """Un estudio guardado del usuario, sin volver a evaluarlo."""
