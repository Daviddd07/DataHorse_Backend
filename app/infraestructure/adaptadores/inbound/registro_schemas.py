from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RegistroRequest(BaseModel):
    # extra="forbid": si alguien envía id_rol, estado, etc., se rechaza (422).
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(max_length=120)
    correo: str = Field(max_length=180)
    contrasena: str = Field(max_length=64)
    telefono: Optional[str] = Field(default=None, max_length=30)
    ubicacion: Optional[str] = Field(default=None, max_length=180)


class RegistroResponse(BaseModel):
    id_usuario: int
    nombre: str
    correo: str
