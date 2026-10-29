from datetime import date

from pydantic import BaseModel, EmailStr, Field

# ======================================================
# AUTENTICACIÓN
# ======================================================

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


class GoogleAuthRequest(BaseModel):
    credential: str


class CorreoRequest(BaseModel):
    correo: EmailStr


class VerificarCodigoRequest(BaseModel):
    correo: EmailStr
    codigo: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResetPasswordRequest(BaseModel):
    correo: EmailStr
    codigo: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    nueva_password: str = Field(min_length=8, max_length=64)


# ======================================================
# CABALLOS
# ======================================================

class CaballoCreateRequest(BaseModel):
    id_raza: int | None = None
    raza_personalizada: str | None = None

    nombre: str
    sexo: str
    fecha_nacimiento: date
    altura: float
    color: str
    ubicacion: str
    descripcion: str
    disponibilidad: str

    precio: float | None = None


class CaballoUpdateRequest(BaseModel):
    id_raza: int | None = None
    raza_personalizada: str | None = None

    nombre: str
    fecha_nacimiento: date
    altura: float
    color: str
    ubicacion: str
    descripcion: str
    disponibilidad: str

    precio: float | None = None
