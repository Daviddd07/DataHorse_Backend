import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text

from app.application.use_cases.login_use_case import (
    InvalidCredentialsError,
)
from app.config.dependencies import (
    get_login_use_case,
    get_registrar_use_case,
    get_usuario_repo,
)
from app.domain.exceptions import (
    DatosInvalidosError,
    EmailAlreadyExistsError,
)
from app.domain.ports.in_.login_port import LoginPort
from app.domain.ports.in_.registrar_usuario_port import (
    RegistrarUsuarioComando,
    RegistrarUsuarioPort,
)
from app.domain.ports.out.usuario_repository_port import (
    UsuarioRepositoryPort,
)
from app.infraestructure.adaptadores.inbound.rest.schemas import (
    LoginRequest,
    RegistrarRequest,
    UsuarioResponse,
)
from app.infraestructure.adaptadores.outbound.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import (
    engine,
)
from app.infraestructure.adaptadores.outbound.security.jwt_handler import (
    create_access_token,
    decode_access_token,
)


# =========================================================
# CONFIGURACIÃ“N
# =========================================================

load_dotenv(override=True)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

MAILJET_API_KEY = os.getenv("MAILJET_API_KEY")
MAILJET_SECRET_KEY = os.getenv("MAILJET_SECRET_KEY")
MAILJET_SENDER_EMAIL = os.getenv("MAILJET_SENDER_EMAIL")
MAILJET_SENDER_NAME = os.getenv(
    "MAILJET_SENDER_NAME",
    "DataHorse",
)

CODIGO_SECRET = os.getenv("CODIGO_SECRET")

MAILJET_URL = "https://api.mailjet.com/v3.1/send"

CODIGO_EXPIRA_MINUTOS = 10
MAX_INTENTOS_CODIGO = 5


router = APIRouter(
    prefix="/auth",
    tags=["AutenticaciÃ³n"],
)


# =========================================================
# REQUESTS
# =========================================================

class GoogleAuthRequest(BaseModel):
    credential: str


class CorreoRequest(BaseModel):
    correo: EmailStr


class VerificarCodigoRequest(BaseModel):
    correo: EmailStr
    codigo: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
    )


class ResetPasswordRequest(BaseModel):
    correo: EmailStr

    codigo: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
    )

    nueva_password: str = Field(
        min_length=8,
        max_length=64,
    )


# =========================================================
# FUNCIONES AUXILIARES
# =========================================================

def _crear_cookie(
    response: Response,
    id_usuario: int,
):
    token = create_access_token(
        id_usuario
    )
    
    is_production = os.getenv("ENVIRONMENT") == "production"

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=is_production,                      
        samesite="none" if is_production else "lax", 
        max_age=1800,
    )


def _usuario_actual_id(
    request: Request,
) -> int:

    token = request.cookies.get(
        "access_token"
    )

    if not token:
        raise HTTPException(
            status_code=401,
            detail="No autenticado",
        )

    id_usuario = decode_access_token(
        token
    )

    if id_usuario is None:
        raise HTTPException(
            status_code=401,
            detail="SesiÃ³n invÃ¡lida o expirada",
        )

    try:
        return int(id_usuario)

    except (ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="SesiÃ³n invÃ¡lida",
        )


def _generar_codigo() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_codigo(
    codigo: str,
) -> str:

    if not CODIGO_SECRET:
        raise HTTPException(
            status_code=500,
            detail="CODIGO_SECRET no estÃ¡ configurado",
        )

    return hmac.new(
        CODIGO_SECRET.encode("utf-8"),
        codigo.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _validar_password(
    password: str,
):
    if len(password) < 8:
        raise HTTPException(
            status_code=422,
            detail="La contraseÃ±a debe tener mÃ­nimo 8 caracteres",
        )

    if not any(c.isupper() for c in password):
        raise HTTPException(
            status_code=422,
            detail="La contraseÃ±a debe incluir una mayÃºscula",
        )

    if not any(c.islower() for c in password):
        raise HTTPException(
            status_code=422,
            detail="La contraseÃ±a debe incluir una minÃºscula",
        )

    if not any(c.isdigit() for c in password):
        raise HTTPException(
            status_code=422,
            detail="La contraseÃ±a debe incluir un nÃºmero",
        )


# =========================================================
# MAILJET
# =========================================================

def _enviar_codigo(
    correo: str,
    nombre: str,
    codigo: str,
    tipo: str,
):

    if not all(
        [
            MAILJET_API_KEY,
            MAILJET_SECRET_KEY,
            MAILJET_SENDER_EMAIL,
        ]
    ):
        raise HTTPException(
            status_code=500,
            detail="Mailjet no estÃ¡ configurado completamente",
        )

    if tipo == "REGISTRO":
        asunto = "Verifica tu cuenta de DataHorse"
        titulo = "Verifica tu correo"
        mensaje = (
            "Usa este cÃ³digo para activar "
            "tu cuenta de DataHorse."
        )

    else:
        asunto = "RecuperaciÃ³n de contraseÃ±a - DataHorse"
        titulo = "Recupera tu contraseÃ±a"
        mensaje = (
            "Usa este cÃ³digo para establecer "
            "una nueva contraseÃ±a."
        )

    html = f"""
    <div style="
        font-family: Arial, sans-serif;
        max-width: 520px;
        margin: auto;
        padding: 30px;
    ">
        <h2>{titulo}</h2>

        <p>Hola {nombre},</p>

        <p>{mensaje}</p>

        <div style="
            text-align: center;
            margin: 30px 0;
        ">
            <strong style="
                font-size: 32px;
                letter-spacing: 8px;
            ">
                {codigo}
            </strong>
        </div>

        <p>
            Este cÃ³digo vence en
            {CODIGO_EXPIRA_MINUTOS} minutos.
        </p>

        <p>
            Si no solicitaste este cÃ³digo,
            ignora este mensaje.
        </p>

        <p><strong>DataHorse</strong></p>
    </div>
    """

    payload = {
        "Messages": [
            {
                "From": {
                    "Email": MAILJET_SENDER_EMAIL,
                    "Name": MAILJET_SENDER_NAME,
                },
                "To": [
                    {
                        "Email": correo,
                        "Name": nombre,
                    }
                ],
                "Subject": asunto,
                "TextPart": (
                    f"Hola {nombre}. "
                    f"Tu cÃ³digo DataHorse es {codigo}. "
                    f"Vence en {CODIGO_EXPIRA_MINUTOS} minutos."
                ),
                "HTMLPart": html,
            }
        ]
    }

    try:
        respuesta = requests.post(
            MAILJET_URL,
            auth=(
                MAILJET_API_KEY,
                MAILJET_SECRET_KEY,
            ),
            json=payload,
            timeout=15,
        )

    except requests.RequestException as e:
        print(
            "ERROR CONECTANDO CON MAILJET:",
            repr(e),
        )

        raise HTTPException(
            status_code=502,
            detail="No fue posible conectar con Mailjet",
        )

    if not respuesta.ok:
        print(
            "ERROR MAILJET:",
            respuesta.status_code,
            respuesta.text,
        )

        raise HTTPException(
            status_code=502,
            detail="Mailjet rechazÃ³ el envÃ­o del correo",
        )


# =========================================================
# CÃ“DIGOS DE VERIFICACIÃ“N
# =========================================================

def _crear_codigo_verificacion(
    id_usuario: int,
    correo: str,
    nombre: str,
    tipo: str,
):

    codigo = _generar_codigo()

    codigo_hash = _hash_codigo(
        codigo
    )

    fecha_expiracion = (
        datetime.now()
        + timedelta(
            minutes=CODIGO_EXPIRA_MINUTOS
        )
    )

    with engine.begin() as connection:

        # Invalidar cÃ³digos anteriores del mismo tipo.
        connection.execute(
            text("""
                UPDATE verificacion_correo

                SET usado = 1

                WHERE usuario_id_usuario = :id_usuario
                  AND tipo = :tipo
                  AND usado = 0
            """),
            {
                "id_usuario": id_usuario,
                "tipo": tipo,
            },
        )

        connection.execute(
            text("""
                INSERT INTO verificacion_correo (
                    usuario_id_usuario,
                    codigo_hash,
                    tipo,
                    fecha_expiracion,
                    usado,
                    intentos
                )
                VALUES (
                    :id_usuario,
                    :codigo_hash,
                    :tipo,
                    :fecha_expiracion,
                    0,
                    0
                )
            """),
            {
                "id_usuario": id_usuario,
                "codigo_hash": codigo_hash,
                "tipo": tipo,
                "fecha_expiracion": fecha_expiracion,
            },
        )

    _enviar_codigo(
        correo=correo,
        nombre=nombre,
        codigo=codigo,
        tipo=tipo,
    )


def _validar_codigo(
    id_usuario: int,
    codigo: str,
    tipo: str,
):

    with engine.begin() as connection:

        registro = connection.execute(
            text("""
                SELECT
                    id_verificacion,
                    codigo_hash,
                    fecha_expiracion,
                    intentos

                FROM verificacion_correo

                WHERE usuario_id_usuario = :id_usuario
                  AND tipo = :tipo
                  AND usado = 0

                ORDER BY id_verificacion DESC

                LIMIT 1
            """),
            {
                "id_usuario": id_usuario,
                "tipo": tipo,
            },
        ).first()

        if registro is None:
            raise HTTPException(
                status_code=400,
                detail="No existe un cÃ³digo vÃ¡lido",
            )

        if registro.fecha_expiracion < datetime.now():

            connection.execute(
                text("""
                    UPDATE verificacion_correo
                    SET usado = 1
                    WHERE id_verificacion = :id
                """),
                {
                    "id": registro.id_verificacion
                },
            )

            raise HTTPException(
                status_code=400,
                detail="El cÃ³digo ha expirado",
            )

        if registro.intentos >= MAX_INTENTOS_CODIGO:

            connection.execute(
                text("""
                    UPDATE verificacion_correo
                    SET usado = 1
                    WHERE id_verificacion = :id
                """),
                {
                    "id": registro.id_verificacion
                },
            )

            raise HTTPException(
                status_code=429,
                detail="Superaste el mÃ¡ximo de intentos",
            )

        codigo_correcto = hmac.compare_digest(
            _hash_codigo(codigo),
            registro.codigo_hash,
        )

        if not codigo_correcto:

            connection.execute(
                text("""
                    UPDATE verificacion_correo

                    SET
                        intentos = intentos + 1,
                        usado = CASE
                            WHEN intentos + 1 >= :max_intentos
                            THEN 1
                            ELSE usado
                        END

                    WHERE id_verificacion = :id
                """),
                {
                    "id": registro.id_verificacion,
                    "max_intentos": MAX_INTENTOS_CODIGO,
                },
            )

            raise HTTPException(
                status_code=400,
                detail="CÃ³digo incorrecto",
            )

        connection.execute(
            text("""
                UPDATE verificacion_correo
                SET usado = 1
                WHERE id_verificacion = :id
            """),
            {
                "id": registro.id_verificacion
            },
        )


# =========================================================
# REGISTRO NORMAL
# =========================================================

@router.post(
    "/register",
    status_code=201,
)
def register(
    body: RegistrarRequest,
    use_case: RegistrarUsuarioPort = Depends(
        get_registrar_use_case
    ),
):

    try:
        usuario = use_case.ejecutar(
            RegistrarUsuarioComando(
                nombre=body.nombre,
                correo=body.correo,
                contrasena=body.password,
                telefono=body.telefono,
                ubicacion=body.ubicacion,
            )
        )

    except DatosInvalidosError as e:
        raise HTTPException(
            status_code=422,
            detail=e.mensaje,
        )

    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=409,
            detail="Ese correo ya estÃ¡ registrado",
        )

    # El usuario todavÃ­a no ha confirmado su correo.
    with engine.begin() as connection:
        connection.execute(
            text("""
                UPDATE usuario
                SET estado = 'pendiente'
                WHERE id_usuario = :id_usuario
            """),
            {
                "id_usuario": usuario.id_usuario
            },
        )

    try:
        _crear_codigo_verificacion(
            id_usuario=usuario.id_usuario,
            correo=usuario.correo,
            nombre=usuario.nombre,
            tipo="REGISTRO",
        )

        correo_enviado = True

    except HTTPException as e:
        print(
            "USUARIO CREADO, PERO ERROR EN CORREO:",
            e.detail,
        )

        correo_enviado = False

    return {
        "id": usuario.id_usuario,
        "nombre": usuario.nombre,
        "correo": usuario.correo,
        "estado": "pendiente",
        "requiere_verificacion": True,
        "correo_enviado": correo_enviado,
        "mensaje": (
            "Revisa tu correo para verificar tu cuenta"
            if correo_enviado
            else
            "Cuenta creada. Usa reenviar cÃ³digo."
        ),
    }


# =========================================================
# VERIFICAR CORREO
# =========================================================

@router.post("/verify-email")
def verify_email(
    body: VerificarCodigoRequest,
    repo: UsuarioRepositoryPort = Depends(
        get_usuario_repo
    ),
):

    correo = body.correo.strip().lower()

    usuario = repo.find_by_email(
        correo
    )

    if usuario is None:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado",
        )

    if usuario.estado.lower() == "activo":
        return {
            "mensaje": "La cuenta ya estÃ¡ verificada"
        }

    _validar_codigo(
        usuario.id_usuario,
        body.codigo,
        "REGISTRO",
    )

    with engine.begin() as connection:
        connection.execute(
            text("""
                UPDATE usuario
                SET estado = 'activo'
                WHERE id_usuario = :id_usuario
            """),
            {
                "id_usuario": usuario.id_usuario
            },
        )

    return {
        "mensaje": "Correo verificado correctamente"
    }


# =========================================================
# REENVIAR CÃ“DIGO
# =========================================================

@router.post("/resend-code")
def resend_code(
    body: CorreoRequest,
    repo: UsuarioRepositoryPort = Depends(
        get_usuario_repo
    ),
):

    usuario = repo.find_by_email(
        body.correo.strip().lower()
    )

    if usuario is None:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado",
        )

    if usuario.estado.lower() == "activo":
        return {
            "mensaje": "La cuenta ya estÃ¡ verificada"
        }

    _crear_codigo_verificacion(
        usuario.id_usuario,
        usuario.correo,
        usuario.nombre,
        "REGISTRO",
    )

    return {
        "mensaje": "CÃ³digo reenviado correctamente"
    }


# =========================================================
# LOGIN NORMAL
# =========================================================

from app.infraestructure.adaptadores.outbound.persistence.audit_log_service import (
    registrar_auditoria,
)

@router.post("/login")
def login(
    body: LoginRequest,
    response: Response,
    use_case: LoginPort = Depends(
        get_login_use_case
    ),
    repo: UsuarioRepositoryPort = Depends(
        get_usuario_repo
    ),
):
    try:
        usuario_id = use_case.execute(
            body.correo,
            body.password,
        )

    except InvalidCredentialsError:
        registrar_auditoria(
            accion="LOGIN",
            modulo="AUTENTICACION",
            resultado="FALLIDO",
            detalle="Credenciales incorrectas",
        )

        raise HTTPException(
            status_code=401,
            detail="Correo o contraseña incorrectos",
        )

    usuario = repo.find_by_id(int(usuario_id))

    if usuario is None:
        registrar_auditoria(
            accion="LOGIN",
            modulo="AUTENTICACION",
            resultado="FALLIDO",
            detalle="Usuario no encontrado",
        )

        raise HTTPException(
            status_code=401,
            detail="Usuario no encontrado",
        )

    if usuario.estado.lower() != "activo":
        registrar_auditoria(
            accion="LOGIN",
            modulo="AUTENTICACION",
            resultado="DENEGADO",
            usuario_id=usuario.id_usuario,
            detalle="Usuario sin acceso por estado inactivo",
        )

        raise HTTPException(
            status_code=403,
            detail="Debes verificar tu correo antes de iniciar sesión",
        )

    _crear_cookie(
        response,
        usuario.id_usuario,
    )

    registrar_auditoria(
        accion="LOGIN",
        modulo="AUTENTICACION",
        resultado="EXITOSO",
        usuario_id=usuario.id_usuario,
        detalle="Inicio de sesión correcto",
    )

    return {
        "mensaje": "Login exitoso"
    }
# =========================================================
# GOOGLE SIGN-IN
# =========================================================

@router.post("/google")
def google_auth(
    body: GoogleAuthRequest,
    response: Response,
    registrar: RegistrarUsuarioPort = Depends(get_registrar_use_case),
    repo: UsuarioRepositoryPort = Depends(get_usuario_repo),
):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_CLIENT_ID no estÃ¡ configurado",
        )

    try:
        datos = google_id_token.verify_oauth2_token(
            body.credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10,
        )
    except Exception as e:
        print("ERROR GOOGLE:", repr(e))
        raise HTTPException(
            status_code=401,
            detail="Token de Google invÃ¡lido",
        )

    google_sub = datos.get("sub")
    correo = datos.get("email")
    nombre = datos.get("name")
    verificado = datos.get("email_verified")

    if not (google_sub and correo and verificado):
        raise HTTPException(
            status_code=401,
            detail="La cuenta de Google no pudo verificarse",
        )

    correo = correo.strip().lower()
    nombre = nombre.strip() if nombre else correo.split("@")[0]

    # Buscar primero por identificador Google.
    with engine.connect() as connection:
        vinculo = connection.execute(
            text("""
                SELECT usuario_id_usuario
                FROM usuario_google
                WHERE google_sub = :google_sub
            """),
            {"google_sub": google_sub},
        ).first()

    if vinculo:
        usuario = repo.find_by_id(int(vinculo.usuario_id_usuario))
        if usuario is None:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
    else:
        usuario = repo.find_by_email(correo)

        if usuario is None:
            password_interno = "Aa1!" + secrets.token_urlsafe(32)

            try:
                usuario = registrar.ejecutar(
                    RegistrarUsuarioComando(
                        nombre=nombre,
                        correo=correo,
                        contrasena=password_interno,
                        telefono=None,
                        ubicacion=None,
                    )
                )
            except EmailAlreadyExistsError:
                usuario = repo.find_by_email(correo)

        if usuario is None:
            raise HTTPException(
                status_code=500,
                detail="No fue posible crear el usuario",
            )

        with engine.begin() as connection:
            otro_google = connection.execute(
                text("""
                    SELECT google_sub
                    FROM usuario_google
                    WHERE usuario_id_usuario = :id_usuario
                """),
                {"id_usuario": usuario.id_usuario},
            ).first()

            if otro_google and otro_google.google_sub != google_sub:
                raise HTTPException(
                    status_code=409,
                    detail="Esta cuenta ya estÃ¡ vinculada con otra cuenta de Google",
                )

            if not otro_google:
                connection.execute(
                    text("""
                        INSERT INTO usuario_google (
                            usuario_id_usuario,
                            google_sub
                        )
                        VALUES (
                            :id_usuario,
                            :google_sub
                        )
                    """),
                    {
                        "id_usuario": usuario.id_usuario,
                        "google_sub": google_sub,
                    },
                )

    # Google ya verificÃ³ el correo.
    with engine.begin() as connection:
        connection.execute(
            text("""
                UPDATE usuario
                SET estado = 'activo'
                WHERE id_usuario = :id_usuario
            """),
            {"id_usuario": usuario.id_usuario},
        )

    # ðŸ‘‡ AQUÃ ESTÃ EL DEBUG CORREGIDO ðŸ‘‡
    try:
        _crear_cookie(
            response,
            usuario.id_usuario,
        )

        return {
            "mensaje": "AutenticaciÃ³n con Google exitosa",
            "usuario": {
                "id": usuario.id_usuario,
                "nombre": usuario.nombre,
                "correo": usuario.correo,
            },
        }
    except Exception as e:
        import traceback
        traceback.print_exc() # Esto imprimirÃ¡ el error real en la terminal
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# OLVIDÃ‰ MI CONTRASEÃ‘A
# TambiÃ©n sirve para una cuenta creada con Google.
# =========================================================

@router.post("/forgot-password")
def forgot_password(
    body: CorreoRequest,
    repo: UsuarioRepositoryPort = Depends(get_usuario_repo),
):
    usuario = repo.find_by_email(body.correo.strip().lower())

    if usuario is not None:
        _crear_codigo_verificacion(
            usuario.id_usuario,
            usuario.correo,
            usuario.nombre,
            "RECUPERAR_PASSWORD",
        )

    return {
        "mensaje": "Si el correo está registrado, recibirás un código."
    }

@router.post("/reset-password")
def reset_password(
    body: ResetPasswordRequest,
    repo: UsuarioRepositoryPort = Depends(
        get_usuario_repo
    ),
):

    usuario = repo.find_by_email(
        body.correo.strip().lower()
    )

    if usuario is None:
        raise HTTPException(
            status_code=400,
            detail="Correo o cÃ³digo invÃ¡lido",
        )

    _validar_password(
        body.nueva_password
    )

    _validar_codigo(
        usuario.id_usuario,
        body.codigo,
        "RECUPERAR_PASSWORD",
    )

    hasher = Argon2PasswordHasher()

    nueva_hash = hasher.hashear(
        body.nueva_password
    )

    with engine.begin() as connection:
        connection.execute(
            text("""
                UPDATE usuario

                SET
                    `contraseÃ±a` = :contrasena,
                    estado = 'activo'

                WHERE id_usuario = :id_usuario
            """),
            {
                "contrasena": nueva_hash,
                "id_usuario": usuario.id_usuario,
            },
        )

    return {
        "mensaje": "ContraseÃ±a actualizada correctamente"
    }


# =========================================================
# USUARIO ACTUAL
# =========================================================

@router.get(
    "/me",
    response_model=UsuarioResponse,
)
def me(
    request: Request,
    repo: UsuarioRepositoryPort = Depends(
        get_usuario_repo
    ),
):

    id_usuario = _usuario_actual_id(
        request
    )

    usuario = repo.find_by_id(
        id_usuario
    )

    if usuario is None:
        raise HTTPException(
            status_code=401,
            detail="Usuario no encontrado",
        )

    return UsuarioResponse(
        id=usuario.id_usuario,
        correo=usuario.correo,
        nombre=usuario.nombre,
    )


# =========================================================
# LOGOUT
# =========================================================

@router.post("/logout")
def logout(
    response: Response,
):
   
    is_production = os.getenv("ENVIRONMENT") == "production"

    response.delete_cookie(
        key="access_token",
        httponly=True,
      
        secure=is_production,
        samesite="none" if is_production else "lax",
    )

    return {
        "mensaje": "SesiÃ³n cerrada correctamente"
    }
