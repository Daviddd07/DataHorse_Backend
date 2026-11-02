from dataclasses import dataclass
from datetime import date
from typing import Optional

ROL_ADMINISTRADOR_ID = 1    # id del rol "administrador" en la tabla rol

# Activo, pero entró solo con Google y nunca creó su propia contraseña.
ESTADO_ACTIVO_GOOGLE = "activo_google"


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

    def es_administrador(self) -> bool:
        return self.id_rol == ROL_ADMINISTRADOR_ID

    def requiere_contrasena(self) -> bool:
        return (self.estado or "").lower() == ESTADO_ACTIVO_GOOGLE
