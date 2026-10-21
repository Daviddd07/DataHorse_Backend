from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Usuario:
    """Entidad que refleja la tabla Usuario."""
    id_usuario: Optional[int]
    id_rol: int
    nombre: str
    correo: str
    contrasena: str
    telefono: Optional[str]
    ubicacion: Optional[str]
    
    ubicacion_lat: Optional[float] = None
    ubicacion_lng: Optional[float] = None
    ubicacion_texto: Optional[str] = None
    ciudad: Optional[str] = None
    departamento: Optional[str] = None
    
    fecha_registro: date = None
    estado: str = None
