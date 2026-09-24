from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Usuario:
    """Entidad que refleja la tabla Usuario."""
    id_usuario: Optional[int]      # PK
    id_rol: int                    # FK (lo asigna el backend)
    nombre: str                    # VARCHAR(120)
    correo: str                    # VARCHAR(180) único
    contrasena: str                # VARCHAR(255) -> SIEMPRE el hash
    telefono: Optional[str]        # VARCHAR(30)
    ubicacion: Optional[str]       # VARCHAR(180)
    fecha_registro: date           # DATE
    estado: str                    # VARCHAR(30)
