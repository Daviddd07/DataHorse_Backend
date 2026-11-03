from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from app.domain.entities.descendencia import Descendencia


@dataclass
class ActualizarCaballoComando:
    id_caballo: int
    id_usuario: int
    nombre: str
    fecha_nacimiento: date
    altura: float
    color: str
    ubicacion: str
    descripcion: str
    disponibilidad: str
    id_raza: Optional[int] = None
    raza_personalizada: Optional[str] = None
    precio: Optional[float] = None
    # None = no se envió: se conserva la descendencia guardada
    descendencia: Optional[Descendencia] = None


class ListarMisCaballosPort(ABC):
    @abstractmethod
    def ejecutar(self, id_usuario: int) -> List[dict]: ...


class ObtenerCaballoPort(ABC):
    @abstractmethod
    def ejecutar(self, id_caballo: int, id_usuario: int) -> dict: ...


class ActualizarCaballoPort(ABC):
    @abstractmethod
    def ejecutar(self, c: ActualizarCaballoComando) -> None: ...


class EliminarCaballoPort(ABC):
    @abstractmethod
    def ejecutar(self, id_caballo: int, id_usuario: int) -> None: ...


class ListarUbicacionesPort(ABC):
    @abstractmethod
    def departamentos(self) -> List[str]: ...

    @abstractmethod
    def ciudades(self, departamento: Optional[str] = None) -> List[str]: ...
