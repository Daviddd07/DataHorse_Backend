from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi import Request
from app.config.dependencies import (
    get_usuario_repo,
    get_listar_razas_use_case,
    get_registrar_caballo_use_case,
)
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort
from app.infraestructure.adaptadores.outbound.security.jwt_handler import (
    create_access_token,
    decode_access_token,
)
from app.application.use_cases.login_use_case import InvalidCredentialsError
<<<<<<< HEAD
from app.application.use_cases.registrar_use_case import EmailAlreadyExistsError

from app.config.dependencies import (
    get_login_use_case,
    get_registrar_use_case,
)

=======
from app.config.dependencies import get_login_use_case, get_registrar_use_case
from app.domain.exceptions import DatosInvalidosError, EmailAlreadyExistsError
>>>>>>> 7c3e33babdff51df967880f35799735231fe1b21
from app.domain.ports.in_.login_port import LoginPort
from app.domain.ports.in_.registrar_usuario_port import RegistrarUsuarioPort
from app.infraestructure.adaptadores.inbound.rest.schemas import (
    LoginRequest,
    RegistrarRequest,
    UsuarioResponse,
    RazaResponse,
    CaballoRequest,
    CaballoResponse,
)
<<<<<<< HEAD
=======
from app.domain.ports.in_.registrar_usuario_port import (
    RegistrarUsuarioComando,
    RegistrarUsuarioPort,
)

>>>>>>> 7c3e33babdff51df967880f35799735231fe1b21

from app.infraestructure.adaptadores.outbound.security.jwt_handler import (
    create_access_token,
)

<<<<<<< HEAD

router = APIRouter(prefix="/auth", tags=["auth"])


# ======================================================
# LOGIN
# ======================================================
=======
>>>>>>> 7c3e33babdff51df967880f35799735231fe1b21

@router.post("/login")
def login(
    body: LoginRequest,
    response: Response,
    use_case: LoginPort = Depends(get_login_use_case),
):
    try:
        usuario_id = use_case.execute(
            body.correo,
            body.password
        )

    except InvalidCredentialsError:
        raise HTTPException(
            status_code=401,
            detail="Correo o contraseña incorrectos"
        )

    token = create_access_token(usuario_id)

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,  # True cuando uses HTTPS
        samesite="lax",
        max_age=1800,
    )

    return {
        "mensaje": "Login exitoso"
    }


<<<<<<< HEAD
# ======================================================
# REGISTRO
# ======================================================

@router.post(
    "/register",
    response_model=UsuarioResponse,
    status_code=201
)
def register(
=======
@router.post("/registro", response_model=UsuarioResponse, status_code=201)
def registrar(
>>>>>>> 7c3e33babdff51df967880f35799735231fe1b21
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
<<<<<<< HEAD

        comando = RegistrarUsuarioComando(
            nombre=body.nombre,
            correo=body.correo,
            contrasena=body.password,
            telefono=getattr(body, "telefono", None),
            ubicacion=getattr(body, "ubicacion", None),
        )

        usuario = use_case.ejecutar(comando)

    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=409,
            detail="Ese correo ya está registrado"
        )

    return UsuarioResponse(
        id=usuario.id_usuario,
        correo=usuario.correo,
        nombre=usuario.nombre
    )
=======
        usuario = use_case.ejecutar(comando)
    except DatosInvalidosError as e:
        raise HTTPException(status_code=422, detail=e.mensaje)
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Ese correo ya está registrado")

    return UsuarioResponse(id=usuario.id_usuario, correo=usuario.correo, nombre=usuario.nombre)


@router.get("/me", response_model=UsuarioResponse)
def me(
    request: Request,
    repo: UsuarioRepositoryPort = Depends(get_usuario_repo),
):
    token = request.cookies.get("access_token")
    if token is None:
        raise HTTPException(status_code=401, detail="No autenticado")

    id_texto = decode_access_token(token)
    if id_texto is None:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")

    usuario = repo.find_by_id(int(id_texto))
    if usuario is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    return UsuarioResponse(id=usuario.id_usuario, correo=usuario.correo, nombre=usuario.nombre)