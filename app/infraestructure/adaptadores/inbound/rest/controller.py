from fastapi import APIRouter, Depends, HTTPException, Response

from app.application.use_cases.login_use_case import InvalidCredentialsError
from app.config.dependencies import get_login_use_case, get_registrar_use_case
from app.domain.exceptions import DatosInvalidosError, EmailAlreadyExistsError
from app.domain.ports.in_.login_port import LoginPort
from app.domain.ports.in_.registrar_usuario_port import RegistrarUsuarioPort
from app.infraestructure.adaptadores.inbound.rest.schemas import (
    LoginRequest,
    RegistrarRequest,
    UsuarioResponse,
)
from app.domain.ports.in_.registrar_usuario_port import (
    RegistrarUsuarioComando,
    RegistrarUsuarioPort,
)
from app.infraestructure.adaptadores.outbound.security.jwt_handler import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(
    body: LoginRequest,
    response: Response,
    use_case: LoginPort = Depends(get_login_use_case),
):
    try:
        usuario_id = use_case.execute(body.correo, body.password)
    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")

    token = create_access_token(usuario_id)

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,  # cambia a True cuando sirvas por HTTPS
        samesite="lax",
        max_age=1800,
    )
    return {"mensaje": "Login exitoso"}


@router.post("/registro", response_model=UsuarioResponse, status_code=201)
def registrar(
    body: RegistrarRequest,
    use_case: RegistrarUsuarioPort = Depends(get_registrar_use_case),
):
    comando = RegistrarUsuarioComando(
        nombre=body.nombre,
        correo=body.correo,
        contrasena=body.password,
        telefono=body.telefono,
        ubicacion=body.ubicacion,
    )
    try:
        usuario = use_case.ejecutar(comando)
    except DatosInvalidosError as e:
        raise HTTPException(status_code=422, detail=e.mensaje)
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Ese correo ya está registrado")

    return UsuarioResponse(id=usuario.id_usuario, correo=usuario.correo, nombre=usuario.nombre)