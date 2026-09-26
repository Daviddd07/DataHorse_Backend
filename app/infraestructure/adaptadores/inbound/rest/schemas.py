from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, model_validator


class LoginRequest(BaseModel):
    correo: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RegistrarRequest(BaseModel):
    correo: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nombre: str = Field(min_length=1, max_length=120)
    telefono: str | None = None
    ubicacion: str | None = None

class UsuarioResponse(BaseModel):
    id: int
    correo: str
    nombre: str


class RazaResponse(BaseModel):
    id_raza: int
    nombre: str
    descripcion: Optional[str] = None


class CaballoRequest(BaseModel):
    nombre: str
    sexo: Literal["Macho", "Hembra"]
    fecha_nacimiento: date
    altura: float
    color: str
    ubicacion: str
    descripcion: str
    disponibilidad: Literal["Disponible", "No disponible"]
    # Exactamente uno de los dos: una raza existente o una escrita a mano ("Otro")
    id_raza: Optional[int] = None
    raza_personalizada: Optional[str] = None

    @model_validator(mode="after")
    def validar_raza(self):
        if not self.id_raza and not self.raza_personalizada:
            raise ValueError("Debes elegir una raza o escribir una en 'Otro'")
        if self.id_raza and self.raza_personalizada:
            raise ValueError("Elige una raza existente o escribe una en 'Otro', no ambas")
        return self


class CaballoResponse(BaseModel):
    id_caballo: int
    id_raza: int
    id_propietario: int
    nombre: str
    sexo: str
    fecha_nacimiento: date
    altura: float
    color: str
    ubicacion: str
    descripcion: str
    disponibilidad: str