from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class LogFrontend:
    id_log: Optional[int]
    id_usuario: Optional[int]  # None si el log llegó sin sesión iniciada
    nivel: str  # "debug" | "info" | "warn" | "error"
    mensaje: str
    contexto: Optional[dict]
    url: str
    user_agent: str
    sesion_id: str
    fecha: datetime  # UTC, sin zona horaria
