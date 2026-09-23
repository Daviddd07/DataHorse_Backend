from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    correo: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RegistrarRequest(BaseModel):
    correo: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nombre: str = Field(min_length=1, max_length=100)


class UsuarioResponse(BaseModel):
    id: str
    correo: str
    nombre: str
