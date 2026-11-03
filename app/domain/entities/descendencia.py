from dataclasses import dataclass, fields
from typing import List, Optional

MODALIDADES = (
    "Paso fino colombiano",
    "Trocha",
    "Trocha y galope",
    "Trote y galope",
    "Galope",
    "Salto",
    "Carreras",
    "Trabajo de campo",
    "Otra",
)

TEMPERAMENTOS = ("Tranquilo", "Dócil", "Activo", "Nervioso", "Dominante")


@dataclass
class Descendencia:
    """Genealogía y aptitudes de un caballo. Todo es opcional: muchos dueños no tienen la información."""

    padre_nombre: Optional[str] = None
    padre_raza: Optional[str] = None
    padre_registro: Optional[str] = None
    padre_logros: Optional[str] = None
    madre_nombre: Optional[str] = None
    madre_raza: Optional[str] = None
    madre_registro: Optional[str] = None
    madre_logros: Optional[str] = None

    abuelo_paterno_nombre: Optional[str] = None
    abuelo_paterno_raza: Optional[str] = None
    abuela_paterna_nombre: Optional[str] = None
    abuela_paterna_raza: Optional[str] = None
    abuelo_materno_nombre: Optional[str] = None
    abuelo_materno_raza: Optional[str] = None
    abuela_materna_nombre: Optional[str] = None
    abuela_materna_raza: Optional[str] = None

    asociacion_registro: Optional[str] = None
    criadero_origen: Optional[str] = None

    modalidad: Optional[str] = None
    temperamento: Optional[str] = None

    condiciones_hereditarias: Optional[str] = None
    pruebas_geneticas: Optional[str] = None

    crias_anteriores: Optional[int] = None
    caracteristicas_crias: Optional[str] = None

    notas: Optional[str] = None

    @classmethod
    def campos(cls) -> List[str]:
        return [f.name for f in fields(cls)]

    def campos_vacios(self) -> List[str]:
        """Campos sin dato; la evaluación de compatibilidad los usa para medir la confianza."""
        return [campo for campo in self.campos() if getattr(self, campo) is None]
