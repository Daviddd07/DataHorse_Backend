from datetime import date
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from pydantic import BaseModel
from sqlalchemy import text

from app.application.use_cases.login_use_case import InvalidCredentialsError
from app.application.use_cases.registrar_use_case import EmailAlreadyExistsError

from app.config.dependencies import (
    get_login_use_case,
    get_publicacion_repo,
    get_registrar_caballo_use_case,
    get_registrar_use_case,
    get_subir_fotos_service,
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

from app.domain.services.subir_fotos_service import SubirFotosService

from app.infraestructure.adaptadores.inbound.rest.schemas import (
    CaballoRequest,
    CaballoResponse,
    LoginRequest,
    PublicacionListItem,
    RegistrarRequest,
    UsuarioResponse,
)

from app.infraestructure.adaptadores.inbound.rest.foto_schemas import (
    FotoCaballoResponse,
)

from app.infraestructure.adaptadores.outbound.persistence.db_conexion import (
    engine,
)

from app.infraestructure.adaptadores.outbound.security.jwt_handler import (
    create_access_token,
    decode_access_token,
)


# ======================================================
# ROUTERS
# ======================================================

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

razas_router = APIRouter(
    prefix="/razas",
    tags=["razas"],
)

caballos_router = APIRouter(
    prefix="/caballos",
    tags=["caballos"],
)

publicaciones_router = APIRouter(
    prefix="/publicaciones",
    tags=["publicaciones"],
)


# ======================================================
# REQUEST PUBLICACIÓN
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


# ======================================================
# OBTENER USUARIO AUTENTICADO
# ======================================================

def _obtener_id_usuario_autenticado(request: Request) -> int:
    """Lee y valida la cookie de sesión, devolviendo el id del usuario logueado."""
    token = request.cookies.get("access_token")

    if token is None:
        raise HTTPException(
            status_code=401,
            detail="No autenticado",
        )

    id_texto = decode_access_token(token)

    if id_texto is None:
        raise HTTPException(
            status_code=401,
            detail="Sesión inválida o expirada",
        )

    try:
        return int(id_texto)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Sesión inválida",
        )


# Alias por compatibilidad con el código del compañero
obtener_usuario_autenticado = _obtener_id_usuario_autenticado


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
        usuario_id = use_case.execute(body.correo, body.password)

    except InvalidCredentialsError:
        raise HTTPException(
            status_code=401,
            detail="Correo o contraseña incorrectos",
        )

    token = create_access_token(usuario_id)

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=1800,
    )

    return {"mensaje": "Login exitoso"}


# ======================================================
# REGISTRO
# ======================================================

@router.post(
    "/register",
    response_model=UsuarioResponse,
    status_code=201,
)
def register(
    body: RegistrarRequest,
    use_case: RegistrarUsuarioPort = Depends(get_registrar_use_case),
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
        raise HTTPException(status_code=422, detail=e.mensaje)

    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=409,
            detail="Ese correo ya está registrado",
        )

    return UsuarioResponse(
        id=usuario.id_usuario,
        correo=usuario.correo,
        nombre=usuario.nombre,
    )


# ======================================================
# USUARIO ACTUAL
# ======================================================

@router.get("/me", response_model=UsuarioResponse)
def me(
    request: Request,
    repo: UsuarioRepositoryPort = Depends(get_usuario_repo),
):
    id_usuario = _obtener_id_usuario_autenticado(request)

    usuario = repo.find_by_id(id_usuario)

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

            return [
                {
                    "id_raza": fila.id_raza,
                    "nombre": fila.nombre,
                    "descripcion": fila.descripcion,
                }
                for fila in resultado
            ]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar razas: {str(e)}",
        )


# ======================================================
# REGISTRAR CABALLO + PUBLICACIÓN
# ======================================================

@caballos_router.post(
    "",
    status_code=201,
)
def registrar_caballo(
    body: CaballoCreateRequest,
    request: Request,
):
    id_usuario = _obtener_id_usuario_autenticado(request)

    if body.sexo not in ("Macho", "Hembra"):
        raise HTTPException(
            status_code=422,
            detail="El sexo debe ser Macho o Hembra",
        )

    if not body.nombre.strip():
        raise HTTPException(
            status_code=422,
            detail="El nombre es obligatorio",
        )

    if body.altura <= 0:
        raise HTTPException(
            status_code=422,
            detail="La altura debe ser mayor que cero",
        )

    precio_referencia = body.precio

    if body.sexo == "Hembra":
        precio_referencia = None

    if body.sexo == "Macho":
        if precio_referencia is None or precio_referencia <= 0:
            raise HTTPException(
                status_code=422,
                detail="Debes ingresar un precio para el caballo",
            )

    try:
        with engine.begin() as connection:
            usuario = connection.execute(
                text("""
                    SELECT id_usuario
                    FROM usuario
                    WHERE id_usuario = :id_usuario
                """),
                {"id_usuario": id_usuario},
            ).first()

            if usuario is None:
                raise HTTPException(
                    status_code=404,
                    detail="Usuario no encontrado",
                )

            # ==================================================
            # RAZA
            # ==================================================

            id_raza = body.id_raza

            if body.raza_personalizada and body.raza_personalizada.strip():
                siguiente_raza = connection.execute(
                    text("""
                        SELECT
                            COALESCE(MAX(id_raza), 0) + 1
                        FROM raza
                    """)
                ).scalar()

                id_raza = int(siguiente_raza)

                connection.execute(
                    text("""
                        INSERT INTO raza (
                            id_raza,
                            nombre,
                            descripcion
                        )
                        VALUES (
                            :id_raza,
                            :nombre,
                            :descripcion
                        )
                    """),
                    {
                        "id_raza": id_raza,
                        "nombre": body.raza_personalizada.strip(),
                        "descripcion": "Raza registrada desde publicación",
                    },
                )

            if id_raza is None:
                raise HTTPException(
                    status_code=422,
                    detail="Debes seleccionar una raza",
                )

            raza = connection.execute(
                text("""
                    SELECT id_raza
                    FROM raza
                    WHERE id_raza = :id_raza
                """),
                {"id_raza": id_raza},
            ).first()

            if raza is None:
                raise HTTPException(
                    status_code=404,
                    detail="La raza seleccionada no existe",
                )

            # ==================================================
            # CABALLO
            # ==================================================

            siguiente_caballo = connection.execute(
                text("""
                    SELECT
                        COALESCE(MAX(id_caballo), 0) + 1
                    FROM caballo
                """)
            ).scalar()

            id_caballo = int(siguiente_caballo)

            connection.execute(
                text("""
                    INSERT INTO caballo (
                        id_caballo,
                        nombre,
                        sexo,
                        fecha_nacimiento,
                        altura,
                        color,
                        ubicacion,
                        descripcion,
                        disponibilidad,
                        raza_id_raza,
                        usuario_id_usuario
                    )
                    VALUES (
                        :id_caballo,
                        :nombre,
                        :sexo,
                        :fecha_nacimiento,
                        :altura,
                        :color,
                        :ubicacion,
                        :descripcion,
                        :disponibilidad,
                        :raza_id_raza,
                        :usuario_id_usuario
                    )
                """),
                {
                    "id_caballo": id_caballo,
                    "nombre": body.nombre.strip(),
                    "sexo": body.sexo,
                    "fecha_nacimiento": body.fecha_nacimiento,
                    "altura": body.altura,
                    "color": body.color.strip(),
                    "ubicacion": body.ubicacion.strip(),
                    "descripcion": body.descripcion.strip(),
                    "disponibilidad": body.disponibilidad,
                    "raza_id_raza": id_raza,
                    "usuario_id_usuario": id_usuario,
                },
            )

            # ==================================================
            # PUBLICACIÓN
            # ==================================================

            siguiente_publicacion = connection.execute(
                text("""
                    SELECT
                        COALESCE(MAX(id_publicacion), 0) + 1
                    FROM publicacion
                """)
            ).scalar()

            id_publicacion = int(siguiente_publicacion)

            connection.execute(
                text("""
                    INSERT INTO publicacion (
                        id_publicacion,
                        titulo,
                        descripcion,
                        fecha_publicacion,
                        estado,
                        precio_referencia,
                        caballo_id_caballo,
                        usuario_id_usuario
                    )
                    VALUES (
                        :id_publicacion,
                        :titulo,
                        :descripcion,
                        :fecha_publicacion,
                        :estado,
                        :precio_referencia,
                        :caballo_id_caballo,
                        :usuario_id_usuario
                    )
                """),
                {
                    "id_publicacion": id_publicacion,
                    "titulo": f"{body.nombre.strip()} - {body.sexo}",
                    "descripcion": body.descripcion.strip(),
                    "fecha_publicacion": date.today(),
                    "estado": "Activa",
                    "precio_referencia": precio_referencia,
                    "caballo_id_caballo": id_caballo,
                    "usuario_id_usuario": id_usuario,
                },
            )

        return {
            "mensaje": "Publicación registrada correctamente",
            "id_publicacion": id_publicacion,
            "id_caballo": id_caballo,
            "id_raza": id_raza,
            "id_usuario": id_usuario,
            "nombre": body.nombre,
            "sexo": body.sexo,
            "precio": precio_referencia,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al guardar publicación: {str(e)}",
        )


# ======================================================
# LISTAR PUBLICACIONES
# ======================================================

@publicaciones_router.get("")
def listar_publicaciones(request: Request):
    id_usuario_actual = _obtener_id_usuario_autenticado(request)

    try:
        with engine.connect() as connection:
            resultado = connection.execute(
                text("""
                    SELECT
                        p.id_publicacion,
                        p.titulo,
                        p.descripcion,
                        p.fecha_publicacion,
                        p.estado,
                        p.precio_referencia,
                        p.usuario_id_usuario,

                        c.id_caballo,
                        c.nombre,
                        c.sexo,
                        c.fecha_nacimiento,
                        c.altura,
                        c.color,
                        c.ubicacion,
                        c.disponibilidad,

                        r.id_raza,
                        r.nombre AS raza,

                        u.nombre AS propietario,

                        fc.ruta AS foto_ruta,

                        EXISTS (
                            SELECT 1
                            FROM favorito f
                            WHERE
                                f.usuario_id_usuario = :id_usuario
                                AND
                                f.caballo_id_caballo = c.id_caballo
                        ) AS es_favorita

                    FROM publicacion p

                    INNER JOIN caballo c
                        ON p.caballo_id_caballo = c.id_caballo

                    INNER JOIN raza r
                        ON c.raza_id_raza = r.id_raza

                    INNER JOIN usuario u
                        ON p.usuario_id_usuario = u.id_usuario

                    LEFT JOIN foto_caballo fc
                        ON fc.id_caballo = c.id_caballo
                        AND fc.es_principal = TRUE

                    WHERE p.estado = 'Activa'

                    ORDER BY p.id_publicacion DESC
                """),
                {"id_usuario": id_usuario_actual},
            )

            return [
                {
                    "id_publicacion": fila.id_publicacion,
                    "id_caballo": fila.id_caballo,
                    "id_usuario": fila.usuario_id_usuario,
                    "titulo": fila.titulo,
                    "nombre": fila.nombre,
                    "raza": fila.raza,
                    "sexo": fila.sexo,
                    "ubicacion": fila.ubicacion,
                    "color": fila.color,
                    "descripcion": fila.descripcion,
                    "disponibilidad": fila.disponibilidad,
                    "fecha_publicacion": fila.fecha_publicacion,
                    "precio": (
                        float(fila.precio_referencia)
                        if fila.precio_referencia is not None
                        else None
                    ),
                    "propietario": fila.propietario,
                    "es_mia": fila.usuario_id_usuario == id_usuario_actual,
                    "es_favorita": bool(fila.es_favorita),

       
                    "foto_principal": (
                        f"/{fila.foto_ruta}"
                        if fila.foto_ruta
                        else None
                    ),
                }
                for fila in resultado
            ]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar publicaciones: {str(e)}",
        )
# ======================================================
# AGREGAR FAVORITO
# ======================================================

@caballos_router.post("/{id_caballo}/favorito")
def agregar_favorito(id_caballo: int, request: Request):
    id_usuario = _obtener_id_usuario_autenticado(request)

    try:
        with engine.begin() as connection:
            caballo = connection.execute(
                text("""
                    SELECT id_caballo
                    FROM caballo
                    WHERE id_caballo = :id_caballo
                """),
                {"id_caballo": id_caballo},
            ).first()

            if caballo is None:
                raise HTTPException(
                    status_code=404,
                    detail="Caballo no encontrado",
                )

            ya_existe = connection.execute(
                text("""
                    SELECT id_favorito
                    FROM favorito
                    WHERE
                        usuario_id_usuario = :id_usuario
                        AND
                        caballo_id_caballo = :id_caballo
                """),
                {
                    "id_usuario": id_usuario,
                    "id_caballo": id_caballo,
                },
            ).first()

            if ya_existe is not None:
                return {"mensaje": "El caballo ya está en favoritos"}

            siguiente_favorito = connection.execute(
                text("""
                    SELECT COALESCE(MAX(id_favorito), 0) + 1
                    FROM favorito
                """)
            ).scalar()

            id_favorito = int(siguiente_favorito)

            connection.execute(
                text("""
                    INSERT INTO favorito (
                        id_favorito,
                        fecha,
                        usuario_id_usuario,
                        caballo_id_caballo
                    )
                    VALUES (
                        :id_favorito,
                        :fecha,
                        :id_usuario,
                        :id_caballo
                    )
                """),
                {
                    "id_favorito": id_favorito,
                    "fecha": date.today(),
                    "id_usuario": id_usuario,
                    "id_caballo": id_caballo,
                },
            )

        return {
            "mensaje": "Agregado a favoritos",
            "id_favorito": id_favorito,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al agregar favorito: {str(e)}",
        )


# ======================================================
# QUITAR FAVORITO
# ======================================================

@caballos_router.delete("/{id_caballo}/favorito")
def quitar_favorito(id_caballo: int, request: Request):
    id_usuario = _obtener_id_usuario_autenticado(request)

    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    DELETE FROM favorito
                    WHERE
                        usuario_id_usuario = :id_usuario
                        AND
                        caballo_id_caballo = :id_caballo
                """),
                {
                    "id_usuario": id_usuario,
                    "id_caballo": id_caballo,
                },
            )

        return {"mensaje": "Eliminado de favoritos"}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al quitar favorito: {str(e)}",
        )


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