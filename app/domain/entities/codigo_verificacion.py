from dataclasses import dataclass
from datetime import datetime


@dataclass
class CodigoVerificacion:
    id_verificacion: int
    codigo_hash: str
    fecha_expiracion: datetime
    intentos: int
