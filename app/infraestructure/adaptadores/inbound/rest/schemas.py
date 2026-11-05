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
    es_admin: bool = False
    foto_perfil: str | None = None


def ruta_publica(ruta: str | None) -> str | None:
    """El almacenamiento guarda 'uploads/...'; el frontend la pega a la URL del backend,
    así que la API siempre la entrega con '/' inicial (igual que las fotos de caballos)."""
    return f"/{ruta.lstrip('/')}" if ruta else None


class PerfilResponse(BaseModel):
    id: int
    nombre: str
    correo: str
    telefono: str | None = None
    ciudad: str | None = None
    departamento: str | None = None
    fecha_registro: date | None = None
    es_admin: bool = False
    # Entró con Google y todavía no creó su propia contraseña
    solo_google: bool = False
    foto_perfil: str | None = None  # ruta pública (/uploads/perfiles/...)


class ActualizarPerfilRequest(BaseModel):
    nombre: str = Field(..., max_length=120)
    telefono: str | None = Field(None, max_length=30)
    ciudad: str | None = Field(None, max_length=120)
    departamento: str | None = Field(None, max_length=120)


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

class EvaluarCompatibilidadRequest(BaseModel):
    id_caballo: int = Field(gt=0)  # macho publicado en el marketplace
    id_yegua: int = Field(gt=0)  # yegua del usuario


Nombre = Field(default=None, max_length=120)
Registro = Field(default=None, max_length=60)
Logros = Field(default=None, max_length=500)
TextoLargo = Field(default=None, max_length=2000)


class DescendenciaSchema(BaseModel):
    """Todos los campos son opcionales; los largos coinciden con la tabla descendencia."""

    padre_nombre: str | None = Nombre
    padre_raza: str | None = Nombre
    padre_registro: str | None = Registro
    padre_logros: str | None = Logros
    madre_nombre: str | None = Nombre
    madre_raza: str | None = Nombre
    madre_registro: str | None = Registro
    madre_logros: str | None = Logros

    abuelo_paterno_nombre: str | None = Nombre
    abuelo_paterno_raza: str | None = Nombre
    abuela_paterna_nombre: str | None = Nombre
    abuela_paterna_raza: str | None = Nombre
    abuelo_materno_nombre: str | None = Nombre
    abuelo_materno_raza: str | None = Nombre
    abuela_materna_nombre: str | None = Nombre
    abuela_materna_raza: str | None = Nombre

    asociacion_registro: str | None = Field(default=None, max_length=150)
    criadero_origen: str | None = Field(default=None, max_length=150)

    modalidad: str | None = Field(default=None, max_length=60)
    temperamento: str | None = Field(default=None, max_length=60)

    condiciones_hereditarias: str | None = TextoLargo
    pruebas_geneticas: str | None = TextoLargo

    crias_anteriores: int | None = Field(default=None, ge=0)
    caracteristicas_crias: str | None = TextoLargo

    notas: str | None = TextoLargo


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

    descendencia: DescendenciaSchema | None = None


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

    # Si no se envía, se conserva la descendencia guardada
    descendencia: DescendenciaSchema | None = None
