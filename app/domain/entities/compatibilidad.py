import hashlib
import json
from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime
from typing import List, Optional

from app.domain.entities.descendencia import Descendencia

NIVELES_CONFIANZA = ("alta", "media", "baja")


@dataclass(frozen=True)
class EjemplarEvaluado:
    """Un caballo o yegua tal como lo necesita la evaluación de compatibilidad."""

    id_caballo: int
    id_raza: int
    id_propietario: int
    nombre: str
    sexo: str
    raza: str
    fecha_nacimiento: date
    altura: float
    color: str
    descripcion: str
    disponibilidad: str
    propietario: str  # solo para mostrarlo al usuario; nunca se envía a la IA
    publicado: bool  # tiene una publicación activa en el marketplace
    ciudad: Optional[str] = None
    departamento: Optional[str] = None
    ubicacion_lat: Optional[float] = None
    ubicacion_lng: Optional[float] = None
    descendencia: Optional[Descendencia] = None

    @property
    def eliminado(self) -> bool:
        return self.disponibilidad == "Eliminado"


@dataclass(frozen=True)
class DatosEvaluacion:
    """Lo que se envía a la IA. Sin datos personales de los dueños."""

    caballo: dict
    yegua: dict
    diferencia_altura_cm: float
    distancia_km: Optional[float]
    porcentaje_referencia_razas: Optional[float]

    def como_dict(self) -> dict:
        return asdict(self)

    def huella(self) -> str:
        """Identifica estos datos: si no cambian, se reutiliza la evaluación guardada."""
        texto = json.dumps(self.como_dict(), sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(texto.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ResultadoCompatibilidad:
    puntuacion: int
    raza_puntos: int
    madurez_puntos: int
    altura_puntos: int
    ubicacion_puntos: int
    otros_puntos: int
    nivel_confianza: str
    resumen_cria: str
    fortalezas: List[str] = field(default_factory=list)
    riesgos: List[str] = field(default_factory=list)
    recomendaciones: List[str] = field(default_factory=list)
    datos_faltantes_importantes: List[str] = field(default_factory=list)
    modelo: str = ""

    @classmethod
    def campos_ia(cls) -> List[str]:
        """Campos que devuelve el modelo (todos menos `modelo`, que lo pone el adaptador)."""
        return [f.name for f in fields(cls) if f.name != "modelo"]

    def puntos(self) -> List[int]:
        return [
            self.puntuacion,
            self.raza_puntos,
            self.madurez_puntos,
            self.altura_puntos,
            self.ubicacion_puntos,
            self.otros_puntos,
        ]


@dataclass(frozen=True)
class EvaluacionGuardada:
    """Un estudio ya hecho, tal como quedó guardado (no se vuelve a evaluar)."""

    id_solicitud: int
    id_usuario: int
    id_caballo: int
    id_yegua: int
    creado_en: datetime  # UTC
    resultado: ResultadoCompatibilidad
