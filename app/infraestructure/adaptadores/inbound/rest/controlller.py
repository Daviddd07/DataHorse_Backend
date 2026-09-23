from fastapi import APIRouter, Depends, HTTPException, Response

from app.application.use_cases.login_use_case import InvalidCredentialsError
from app.application.use_cases.registrar_use_case import EmailAlreadyExistsError
from app.config.dependencies import get_login_use_case, get_registrar_use_case
from app.domain.ports.in_.login_port import LoginPort
from app.domain.ports.in_.registrar_port import RegistrarPort
from app.infraestructure.adaptadores.inbound.rest.schemas import (
    LoginRequest,
    RegistrarRequest,
    UsuarioResponse,
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


@router.post("/register", response_model=UsuarioResponse, status_code=201)
def register(
    body: RegistrarRequest,
    use_case: RegistrarPort = Depends(get_registrar_use_case),
):
    try:
        usuario = use_case.execute(body.correo, body.password, body.nombre)
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Ese correo ya está registrado")

    return UsuarioResponse(id=usuario.id, correo=usuario.correo, nombre=usuario.nombre)
