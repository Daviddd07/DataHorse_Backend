from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LogEntradaSchema(BaseModel):
    nivel: Literal["debug", "info", "warn", "error"]
    mensaje: str = Field(min_length=1, max_length=1000)
    contexto: dict | None = None
    url: str = Field(max_length=500)
    user_agent: str = Field(max_length=500)
    sesion_id: str = Field(max_length=50)
    fecha: datetime


class LoteLogsSchema(BaseModel):
    logs: list[LogEntradaSchema] = Field(min_length=1, max_length=50)
