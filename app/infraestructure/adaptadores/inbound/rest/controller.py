from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import text

from app.application.use_cases.login_use_case import InvalidCredentialsError
from app.application.use_cases.registrar_use_case import EmailAlreadyExistsError

from app.config.dependencies import (
    get_login_use_case,
    get_publicacion_repo,
    get_registrar_caballo_use_case,
    get_registrar_use_case,
    get_usuario_repo,
)

from app.domain.exceptions import DatosInvalidosError

from app.domain.ports.in_.login_port import LoginPort
from app.domain.ports.in_.registrar_caballo_port import (
    RegistrarCaballoComando,
    RegistrarCaballoPort,
)
from app.domain.ports.in_.registrar_usuario_port import (
    RegistrarUsuarioComando,
    RegistrarUsuarioPort,
)

from app.domain.ports.out.usuario_repository_port import (
    UsuarioRepositoryPort,
)
from app.domain.ports.out.publicacion_repository_port import (
    PublicacionRepositoryPort,
)

from app.infraestructure.adaptadores.inbound.rest.schemas import (
    CaballoRequest,
    CaballoResponse,
    LoginRequest,
    PublicacionListItem,
    RegistrarRequest,
    UsuarioResponse,
)

from app.infraestructure.adaptadores.outbound.persistence.db_conexion import (
    engine,
)

from app.infraestructure.adaptadores.outbound.security.jwt_handler import (
    create_access_token,
    decode_access_token,
)
from typing import List
from fastapi import UploadFile, File
from app.infraestructure.adaptadores.inbound.rest.foto_schemas import FotoCaballoResponse
from app.domain.services.subir_fotos_service import SubirFotosService
from app.config.dependencies import get_subir_fotos_service

# ======================================================
# ROUTERS
# ======================================================

# Rutas de autenticación
router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

# Rutas de razas
razas_router = APIRouter(
    prefix="/razas",
    tags=["razas"]
)

# Rutas de caballos
caballos_router = APIRouter(
    prefix="/caballos",
    tags=["caballos"]
)


def _obtener_id_usuario_autenticado(request: Request) -> int:
    """Lee y valida la cookie de sesión, devolviendo el id del usuario logueado."""
    token = request.cookies.get("access_token")

    if token is None:
        raise HTTPException(
            status_code=401,
            detail="No autenticado"
        )

    id_texto = decode_access_token(token)

    if id_texto is None:
        raise HTTPException(
            status_code=401,
            detail="Sesión inválida o expirada"
        )

    return int(id_texto)


# ======================================================
# LOGIN
# ======================================================

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
        secure=False,  # Cambiar a True cuando uses HTTPS
        samesite="lax",
        max_age=1800,
    )

    return {
        "mensaje": "Login exitoso"
    }


# ======================================================
# REGISTRO
# ======================================================

@router.post(
    "/register",
    response_model=UsuarioResponse,
    status_code=201
)
def register(
    body: RegistrarRequest,
    use_case: RegistrarUsuarioPort = Depends(
        get_registrar_use_case
    ),
):
    comando = RegistrarUsuarioComando(
        nombre=body.nombre,
        correo=body.correo,
        contrasena=body.password,
        telefono=getattr(body, "telefono", None),
        ubicacion=getattr(body, "ubicacion", None),
    )

    try:
        usuario = use_case.ejecutar(comando)

    except DatosInvalidosError as e:
        raise HTTPException(
            status_code=422,
            detail=e.mensaje
        )

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


# ======================================================
# USUARIO ACTUAL
# ======================================================

@router.get(
    "/me",
    response_model=UsuarioResponse
)
def me(
    request: Request,
    repo: UsuarioRepositoryPort = Depends(
        get_usuario_repo
    ),
):
    id_usuario = _obtener_id_usuario_autenticado(request)

    usuario = repo.find_by_id(id_usuario)

    if usuario is None:
        raise HTTPException(
            status_code=401,
            detail="Usuario no encontrado"
        )

    return UsuarioResponse(
        id=usuario.id_usuario,
        correo=usuario.correo,
        nombre=usuario.nombre
    )


# ======================================================
# LISTAR RAZAS
# ======================================================

@razas_router.get("")
def listar_razas():
    try:
        with engine.connect() as connection:

            resultado = connection.execute(
                text("""
                    SELECT
                        id_raza,
                        nombre,
                        descripcion
                    FROM raza
                    ORDER BY nombre
                """)
            )

            razas = []

            for fila in resultado:
                razas.append(
                    {
                        "id_raza": fila.id_raza,
                        "nombre": fila.nombre,
                        "descripcion": fila.descripcion
                    }
                )

            return razas

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ======================================================
# REGISTRAR CABALLO
# ======================================================

@caballos_router.post(
    "",
    response_model=CaballoResponse,
    status_code=201
)
def registrar_caballo(
    body: CaballoRequest,
    request: Request,
    use_case: RegistrarCaballoPort = Depends(get_registrar_caballo_use_case),
):
    id_propietario = _obtener_id_usuario_autenticado(request)

    comando = RegistrarCaballoComando(
        id_propietario=id_propietario,
        nombre=body.nombre,
        sexo=body.sexo,
        fecha_nacimiento=body.fecha_nacimiento,
        altura=body.altura,
        color=body.color,
        ubicacion=body.ubicacion,
        descripcion=body.descripcion,
        disponibilidad=body.disponibilidad,
        id_raza=body.id_raza,
        raza_personalizada=body.raza_personalizada,
        titulo=body.titulo,
        precio=body.precio,
    )

    try:
        caballo = use_case.ejecutar(comando)
    except DatosInvalidosError as e:
        raise HTTPException(status_code=422, detail=e.mensaje)

    return CaballoResponse(
        id_caballo=caballo.id_caballo,
        id_raza=caballo.id_raza,
        id_propietario=caballo.id_propietario,
        nombre=caballo.nombre,
        sexo=caballo.sexo,
        fecha_nacimiento=caballo.fecha_nacimiento,
        altura=caballo.altura,
        color=caballo.color,
        ubicacion=caballo.ubicacion,
        descripcion=caballo.descripcion,
        disponibilidad=caballo.disponibilidad,
    )


# ======================================================
# LISTAR PUBLICACIONES (MARKETPLACE)
# ======================================================

@caballos_router.get("", response_model=list[PublicacionListItem])
def listar_publicaciones(
    publicacion_repo: PublicacionRepositoryPort = Depends(get_publicacion_repo),
):
    try:
        return publicacion_repo.find_all_activas()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# ======================================================
# SUBIR FOTOS DE UN CABALLO
# ======================================================

@caballos_router.post(
    "/{id_caballo}/fotos",
    response_model=List[FotoCaballoResponse],
)
async def subir_fotos(
    id_caballo: int,
    files: List[UploadFile] = File(...),
    service: SubirFotosService = Depends(get_subir_fotos_service),
):
    print(f"🔍 id_caballo={id_caballo}, cantidad files={len(files)}")   # 👈 temporal
    for f in files:
        print(f"   → {f.filename} | {f.content_type}")                   # 👈 temporal

    archivos = []

    for f in files:
        contenido = await f.read()
        archivos.append((f.filename, f.content_type, contenido))

    try:
        fotos = service.ejecutar(id_caballo, archivos)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return [
        FotoCaballoResponse(
            id_foto=f.id_foto,
            ruta=f"/{f.ruta}",
            es_principal=f.es_principal,
            orden=f.orden,
            fecha_subida=f.fecha_subida,
        )
        for f in fotos
    ]