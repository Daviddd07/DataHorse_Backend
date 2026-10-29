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

from app.infraestructure.adaptadores.outbound.persistence.audit_log_service import (
    registrar_auditoria,
)

from app.infraestructure.adaptadores.outbound.security.jwt_handler import (
    create_access_token,
    decode_access_token,
)

from app.domain.services.geocoding_service import GeocodingService
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
# LISTAR UBICACIONES (departamentos y ciudades)
# ======================================================

@caballos_router.get("/ubicaciones/departamentos")
def listar_departamentos():
    try:
        with engine.connect() as connection:
            resultado = connection.execute(
                text("""
                    SELECT DISTINCT departamento
                    FROM caballo
                    WHERE departamento IS NOT NULL
                      AND departamento != 'Sin departamento'
                      AND disponibilidad != 'Eliminado'
                    ORDER BY departamento ASC
                """)
            )

            return [
                {"departamento": fila.departamento}
                for fila in resultado
            ]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar departamentos: {str(e)}",
        )


@caballos_router.get("/ubicaciones/ciudades")
def listar_ciudades(departamento: str | None = None):
    try:
        with engine.connect() as connection:
            if departamento:
                resultado = connection.execute(
                    text("""
                        SELECT DISTINCT ciudad
                        FROM caballo
                        WHERE ciudad IS NOT NULL
                          AND ciudad != 'Sin ciudad'
                          AND departamento = :departamento
                          AND disponibilidad != 'Eliminado'
                        ORDER BY ciudad ASC
                    """),
                    {"departamento": departamento},
                )
            else:
                resultado = connection.execute(
                    text("""
                        SELECT DISTINCT ciudad
                        FROM caballo
                        WHERE ciudad IS NOT NULL
                          AND ciudad != 'Sin ciudad'
                          AND disponibilidad != 'Eliminado'
                        ORDER BY ciudad ASC
                    """)
                )

            return [
                {"ciudad": fila.ciudad}
                for fila in resultado
            ]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar ciudades: {str(e)}",
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

                        # ==================================================
            # GEOCODING DE LA UBICACION
            # ==================================================

            geocoding = GeocodingService()
            datos_geo = geocoding.geocodificar(body.ubicacion)

            ubicacion_lat = datos_geo["lat"] if datos_geo else None
            ubicacion_lng = datos_geo["lng"] if datos_geo else None
            ubicacion_texto = datos_geo["texto"] if datos_geo else body.ubicacion.strip()
            ciudad = datos_geo["ciudad"] if datos_geo else None
            departamento = datos_geo["departamento"] if datos_geo else None

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
                        ubicacion_lat,
                        ubicacion_lng,
                        ubicacion_texto,
                        ciudad,
                        departamento,
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
                        :ubicacion_lat,
                        :ubicacion_lng,
                        :ubicacion_texto,
                        :ciudad,
                        :departamento,
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
                    "ubicacion_lat": ubicacion_lat,
                    "ubicacion_lng": ubicacion_lng,
                    "ubicacion_texto": ubicacion_texto,
                    "ciudad": ciudad,
                    "departamento": departamento,
                    "descripcion": body.descripcion.strip(),
                    "disponibilidad": body.disponibilidad,
                    "raza_id_raza": id_raza,
                    "usuario_id_usuario": id_usuario,
                },
            )

            # ==================================================
            # PUBLICACIÓN
            # ==================================================

                        # ==================================================
            # PUBLICACIÓN (solo para Machos)
            # ==================================================

            id_publicacion = None

            if body.sexo == "Macho":

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
                
        mensaje = (
            "Publicación registrada correctamente"
            if body.sexo == "Macho"
            else "Yegua registrada correctamente"
        )

        return {
            "mensaje": mensaje,
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
                        c.ubicacion_texto,
                        c.ciudad,
                        c.departamento,
                        c.ubicacion_lat,
                        c.ubicacion_lng,
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
                      AND c.disponibilidad != 'Eliminado'

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
                    "fecha_nacimiento": fila.fecha_nacimiento,
                    "altura": float(fila.altura),
                    "ubicacion_texto": fila.ubicacion_texto,
                    "ciudad": fila.ciudad,
                    "departamento": fila.departamento,
                    "ubicacion_lat": float(fila.ubicacion_lat) if fila.ubicacion_lat else None,
                    "ubicacion_lng": float(fila.ubicacion_lng) if fila.ubicacion_lng else None,
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

        registrar_auditoria(
            accion="AGREGAR_FAVORITO",
            modulo="FAVORITOS",
            resultado="EXITOSO",
            usuario_id=id_usuario,
            detalle=f"Se agregó el caballo {id_caballo} a favoritos.",
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
            resultado_delete = connection.execute(
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
            filas_eliminadas = resultado_delete.rowcount

        if filas_eliminadas == 0:
            return {"mensaje": "El caballo no estaba en favoritos"}

        registrar_auditoria(
            accion="QUITAR_FAVORITO",
            modulo="FAVORITOS",
            resultado="EXITOSO",
            usuario_id=id_usuario,
            detalle=f"Se quitó el caballo {id_caballo} de favoritos.",
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
    request: Request,
    files: List[UploadFile] = File(...),
    service: SubirFotosService = Depends(get_subir_fotos_service),
):

    id_usuario = _obtener_id_usuario_autenticado(request)

    with engine.connect() as connection:
        caballo = connection.execute(
            text('''
                SELECT id_caballo
                FROM caballo
                WHERE id_caballo = :id_caballo
                  AND usuario_id_usuario = :id_usuario
                  AND disponibilidad != 'Eliminado'
            '''),
            {"id_caballo": id_caballo, "id_usuario": id_usuario},
        ).first()

    if caballo is None:
        raise HTTPException(status_code=404, detail="Caballo no encontrado")

    archivos = []
    for f in files:
        contenido = await f.read()
        archivos.append((f.filename, f.content_type, contenido))

    try:
        fotos = service.ejecutar(id_caballo, archivos)
    except ValueError as e:
        registrar_auditoria(
            accion="SUBIR_FOTOGRAFIAS",
            modulo="FOTOGRAFIAS",
            resultado="FALLIDO",
            usuario_id=id_usuario,
            detalle=f"No se pudieron subir fotografías del caballo {id_caballo}: {str(e)}",
        )
        raise HTTPException(status_code=400, detail=str(e))

    registrar_auditoria(
        accion="SUBIR_FOTOGRAFIAS",
        modulo="FOTOGRAFIAS",
        resultado="EXITOSO",
        usuario_id=id_usuario,
        detalle=f"Se subieron {len(fotos)} fotografías al caballo {id_caballo}.",
    )

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
    
# ======================================================
# DETALLE DE UNA PUBLICACIÓN
# ======================================================

@publicaciones_router.get("/{id_publicacion}")
def obtener_publicacion_detalle(
    id_publicacion: int,
    request: Request,
):
    id_usuario_actual = _obtener_id_usuario_autenticado(request)

    try:
        with engine.connect() as connection:

            # ==============================================
            # DATOS DE LA PUBLICACIÓN + CABALLO + RAZA + PROPIETARIO
            # ==============================================

            publicacion = connection.execute(
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
                        r.descripcion AS raza_descripcion,

                        u.nombre AS propietario,
                        u.ubicacion AS propietario_ubicacion,
                        u.telefono AS propietario_telefono,

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

                    WHERE p.id_publicacion = :id_publicacion
                      AND c.disponibilidad != 'Eliminado'
                """),
                {
                    "id_publicacion": id_publicacion,
                    "id_usuario": id_usuario_actual,
                },
            ).first()

            if publicacion is None:
                raise HTTPException(
                    status_code=404,
                    detail="Publicación no encontrada",
                )

            # ==============================================
            # FOTOS DE LA PUBLICACIÓN (todas)
            # ==============================================

            fotos_resultado = connection.execute(
                text("""
                    SELECT
                        id_foto,
                        ruta,
                        es_principal,
                        orden
                    FROM foto_caballo
                    WHERE id_caballo = :id_caballo
                    ORDER BY es_principal DESC, orden ASC
                """),
                {"id_caballo": publicacion.id_caballo},
            )

            fotos = [
                {
                    "id_foto": f.id_foto,
                    "ruta": f"/{f.ruta}",
                    "es_principal": bool(f.es_principal),
                    "orden": f.orden,
                }
                for f in fotos_resultado
            ]

            # ==============================================
            # RESPUESTA
            # ==============================================

            return {
                "id_publicacion": publicacion.id_publicacion,
                "id_caballo": publicacion.id_caballo,
                "id_usuario": publicacion.usuario_id_usuario,

                "titulo": publicacion.titulo,
                "descripcion": publicacion.descripcion,
                "fecha_publicacion": publicacion.fecha_publicacion,
                "estado": publicacion.estado,

                "nombre": publicacion.nombre,
                "sexo": publicacion.sexo,
                "fecha_nacimiento": publicacion.fecha_nacimiento,
                "altura": float(publicacion.altura),
                "color": publicacion.color,
                "ubicacion": publicacion.ubicacion,
                "disponibilidad": publicacion.disponibilidad,

                "id_raza": publicacion.id_raza,
                "raza": publicacion.raza,
                "raza_descripcion": publicacion.raza_descripcion,

                "propietario": publicacion.propietario,
                "propietario_ubicacion": publicacion.propietario_ubicacion,
                "propietario_telefono": publicacion.propietario_telefono,

                "precio": (
                    float(publicacion.precio_referencia)
                    if publicacion.precio_referencia is not None
                    else None
                ),

                "es_mia": publicacion.usuario_id_usuario == id_usuario_actual,
                "es_favorita": bool(publicacion.es_favorita),

                "fotos": fotos,
            }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar la publicación: {str(e)}",
        )
        
# ======================================================
# MIS CABALLOS (todos los del usuario: machos y hembras)
# ======================================================

@caballos_router.get("/mios")
def listar_mis_caballos(request: Request):
    id_usuario = _obtener_id_usuario_autenticado(request)

    try:
        with engine.connect() as connection:

            resultado = connection.execute(
                text("""
                    SELECT
                        c.id_caballo,
                        c.nombre,
                        c.sexo,
                        c.fecha_nacimiento,
                        c.altura,
                        c.color,
                        c.ubicacion,
                        c.ubicacion_texto,       
                        c.ciudad,                    
                        c.departamento, 
                        c.descripcion,
                        c.disponibilidad,

                        r.id_raza,
                        r.nombre AS raza,

                        fc.ruta AS foto_ruta,

                        p.id_publicacion,
                        p.precio_referencia,
                        p.estado AS estado_publicacion

                    FROM caballo c

                    INNER JOIN raza r
                        ON c.raza_id_raza = r.id_raza

                    LEFT JOIN foto_caballo fc
                        ON fc.id_caballo = c.id_caballo
                        AND fc.es_principal = TRUE

                    LEFT JOIN publicacion p
                        ON p.caballo_id_caballo = c.id_caballo
                        AND p.estado = 'Activa'

                    WHERE c.usuario_id_usuario = :id_usuario
                      AND c.disponibilidad != 'Eliminado'

                    ORDER BY c.id_caballo DESC
                """),
                {"id_usuario": id_usuario},
            )

            return [
                {
                    "id_caballo": fila.id_caballo,
                    "nombre": fila.nombre,
                    "sexo": fila.sexo,
                    "fecha_nacimiento": fila.fecha_nacimiento,
                    "altura": float(fila.altura),
                    "color": fila.color,
                    "ubicacion": fila.ubicacion,
                    "ubicacion_texto": fila.ubicacion_texto,     
                    "ciudad": fila.ciudad,                      
                    "departamento": fila.departamento,
                    "descripcion": fila.descripcion,
                    "disponibilidad": fila.disponibilidad,

                    "id_raza": fila.id_raza,
                    "raza": fila.raza,

                    "foto_principal": (
                        f"/{fila.foto_ruta}"
                        if fila.foto_ruta
                        else None
                    ),

                    "id_publicacion": fila.id_publicacion,
                    "precio": (
                        float(fila.precio_referencia)
                        if fila.precio_referencia is not None
                        else None
                    ),
                    "publicado": fila.id_publicacion is not None,
                }
                for fila in resultado
            ]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar tus caballos: {str(e)}",
        )
        
        # ======================================================
# OBTENER UN CABALLO (para edicion)
# ======================================================

@caballos_router.get("/{id_caballo}")
def obtener_caballo(
    id_caballo: int,
    request: Request,
):
    id_usuario = _obtener_id_usuario_autenticado(request)

    try:
        with engine.connect() as connection:

            caballo = connection.execute(
                text("""
                    SELECT
                        c.id_caballo,
                        c.nombre,
                        c.sexo,
                        c.fecha_nacimiento,
                        c.altura,
                        c.color,
                        c.ubicacion,
                        c.ubicacion_texto,        
                        c.ciudad,                 
                        c.departamento, 
                        c.descripcion,
                        c.disponibilidad,
                        c.raza_id_raza,
                        r.nombre AS raza,
                        p.id_publicacion,
                        p.precio_referencia
                    FROM caballo c
                    INNER JOIN raza r
                        ON c.raza_id_raza = r.id_raza
                    LEFT JOIN publicacion p
                        ON p.caballo_id_caballo = c.id_caballo
                        AND p.estado = 'Activa'
                    WHERE c.id_caballo = :id_caballo
                      AND c.usuario_id_usuario = :id_usuario
                      AND c.disponibilidad != 'Eliminado'
                """),
                {
                    "id_caballo": id_caballo,
                    "id_usuario": id_usuario,
                },
            ).first()

            if caballo is None:
                raise HTTPException(
                    status_code=404,
                    detail="Caballo no encontrado",
                )

            fotos_resultado = connection.execute(
                text("""
                    SELECT id_foto, ruta, es_principal, orden
                    FROM foto_caballo
                    WHERE id_caballo = :id_caballo
                    ORDER BY es_principal DESC, orden ASC
                """),
                {"id_caballo": id_caballo},
            )

            fotos = [
                {
                    "id_foto": f.id_foto,
                    "ruta": f"/{f.ruta}",
                    "es_principal": bool(f.es_principal),
                    "orden": f.orden,
                }
                for f in fotos_resultado
            ]

            return {
                "id_caballo": caballo.id_caballo,
                "nombre": caballo.nombre,
                "sexo": caballo.sexo,
                "fecha_nacimiento": caballo.fecha_nacimiento,
                "altura": float(caballo.altura),
                "color": caballo.color,
                "ubicacion": caballo.ubicacion,
                 "ubicacion_texto": caballo.ubicacion_texto,    
                "ciudad": caballo.ciudad,                       
                "departamento": caballo.departamento,     
                "descripcion": caballo.descripcion,
                "disponibilidad": caballo.disponibilidad,
                "id_raza": caballo.raza_id_raza,
                "raza": caballo.raza,
                "id_publicacion": caballo.id_publicacion,
                "precio": (
                    float(caballo.precio_referencia)
                    if caballo.precio_referencia is not None
                    else None
                ),
                "fotos": fotos,
            }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar el caballo: {str(e)}",
        )


# ======================================================
# ACTUALIZAR UN CABALLO
# ======================================================

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


@caballos_router.put("/{id_caballo}")
def actualizar_caballo(
    id_caballo: int,
    body: CaballoUpdateRequest,
    request: Request,
):
    id_usuario = _obtener_id_usuario_autenticado(request)

    if not body.nombre.strip():
        raise HTTPException(422, "El nombre es obligatorio")

    if body.altura <= 0:
        raise HTTPException(422, "La altura debe ser mayor que cero")

    if body.disponibilidad not in ("Disponible", "No disponible"):
        raise HTTPException(422, "Disponibilidad invalida")

    try:
        with engine.begin() as connection:

            caballo = connection.execute(
                text("""
                    SELECT id_caballo, sexo, disponibilidad
                    FROM caballo
                    WHERE id_caballo = :id
                      AND usuario_id_usuario = :uid
                """),
                {"id": id_caballo, "uid": id_usuario},
            ).first()

            if caballo is None:
                raise HTTPException(404, "Caballo no encontrado")

            if caballo.disponibilidad == "Eliminado":
                raise HTTPException(404, "Caballo no encontrado")

            es_macho = caballo.sexo == "Macho"

            # Raza: existente o nueva
            id_raza = body.id_raza

            if body.raza_personalizada and body.raza_personalizada.strip():
                siguiente_raza = connection.execute(
                    text("SELECT COALESCE(MAX(id_raza), 0) + 1 FROM raza")
                ).scalar()

                id_raza = int(siguiente_raza)

                connection.execute(
                    text("""
                        INSERT INTO raza (id_raza, nombre, descripcion)
                        VALUES (:id_raza, :nombre, :descripcion)
                    """),
                    {
                        "id_raza": id_raza,
                        "nombre": body.raza_personalizada.strip(),
                        "descripcion": "Raza registrada desde edicion",
                    },
                )

            if id_raza is None:
                raise HTTPException(422, "Debes seleccionar una raza")

            precio_referencia = body.precio if es_macho else None

            if es_macho and (precio_referencia is None or precio_referencia <= 0):
                raise HTTPException(422, "Debes ingresar un precio valido")

                        # ==================================================
            # GEOCODING DE LA UBICACION (si cambio)
            # ==================================================

            ubicacion_anterior = connection.execute(
                text("""
                    SELECT ubicacion
                    FROM caballo
                    WHERE id_caballo = :id_caballo
                """),
                {"id_caballo": id_caballo},
            ).scalar()

            ubicacion_lat = None
            ubicacion_lng = None
            ubicacion_texto = body.ubicacion.strip()
            ciudad = None
            departamento = None

            if ubicacion_anterior != body.ubicacion.strip():
                geocoding = GeocodingService()
                datos_geo = geocoding.geocodificar(body.ubicacion)

                if datos_geo:
                    ubicacion_lat = datos_geo["lat"]
                    ubicacion_lng = datos_geo["lng"]
                    ubicacion_texto = datos_geo["texto"]
                    ciudad = datos_geo["ciudad"]
                    departamento = datos_geo["departamento"]

            connection.execute(
                text("""
                    UPDATE caballo
                    SET
                        nombre = :nombre,
                        fecha_nacimiento = :fecha_nacimiento,
                        altura = :altura,
                        color = :color,
                        ubicacion = :ubicacion,
                        ubicacion_lat = COALESCE(:ubicacion_lat, ubicacion_lat),
                        ubicacion_lng = COALESCE(:ubicacion_lng, ubicacion_lng),
                        ubicacion_texto = :ubicacion_texto,
                        ciudad = COALESCE(:ciudad, ciudad),
                        departamento = COALESCE(:departamento, departamento),
                        descripcion = :descripcion,
                        disponibilidad = :disponibilidad,
                        raza_id_raza = :raza_id_raza
                    WHERE id_caballo = :id_caballo
                """),
                {
                    "nombre": body.nombre.strip(),
                    "fecha_nacimiento": body.fecha_nacimiento,
                    "altura": body.altura,
                    "color": body.color.strip(),
                    "ubicacion": body.ubicacion.strip(),
                    "ubicacion_lat": ubicacion_lat,
                    "ubicacion_lng": ubicacion_lng,
                    "ubicacion_texto": ubicacion_texto,
                    "ciudad": ciudad,
                    "departamento": departamento,
                    "descripcion": body.descripcion.strip(),
                    "disponibilidad": body.disponibilidad,
                    "raza_id_raza": id_raza,
                    "id_caballo": id_caballo,
                },
            )

            # Reflejar cambios en la publicacion si es macho
            if es_macho:
                connection.execute(
                    text("""
                        UPDATE publicacion
                        SET
                            titulo = :titulo,
                            descripcion = :descripcion,
                            precio_referencia = :precio
                        WHERE caballo_id_caballo = :id_caballo
                          AND estado = 'Activa'
                    """),
                    {
                        "titulo": f"{body.nombre.strip()} - Macho",
                        "descripcion": body.descripcion.strip(),
                        "precio": precio_referencia,
                        "id_caballo": id_caballo,
                    },
                )

        return {
            "mensaje": "Caballo actualizado correctamente",
            "id_caballo": id_caballo,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar el caballo: {str(e)}",
        )


# ======================================================
# ELIMINAR UN CABALLO
# (soft delete del caballo, hard delete de la publicacion)
# ======================================================

@caballos_router.delete("/{id_caballo}")
def eliminar_caballo(
    id_caballo: int,
    request: Request,
):
    id_usuario = _obtener_id_usuario_autenticado(request)

    try:
        with engine.begin() as connection:

            caballo = connection.execute(
                text("""
                    SELECT id_caballo, disponibilidad
                    FROM caballo
                    WHERE id_caballo = :id
                      AND usuario_id_usuario = :uid
                """),
                {"id": id_caballo, "uid": id_usuario},
            ).first()

            if caballo is None:
                raise HTTPException(404, "Caballo no encontrado")

            if caballo.disponibilidad == "Eliminado":
                raise HTTPException(404, "Caballo no encontrado")

            connection.execute(
                text("""
                    DELETE FROM publicacion
                    WHERE caballo_id_caballo = :id_caballo
                """),
                {"id_caballo": id_caballo},
            )

            connection.execute(
                text("""
                    UPDATE caballo
                    SET disponibilidad = 'Eliminado'
                    WHERE id_caballo = :id_caballo
                """),
                {"id_caballo": id_caballo},
            )

        return {
            "mensaje": "Caballo eliminado correctamente",
            "id_caballo": id_caballo,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar el caballo: {str(e)}",
        )


# ======================================================
# ELIMINAR UNA FOTO
# ======================================================

@caballos_router.delete("/{id_caballo}/fotos/{id_foto}")
def eliminar_foto(
    id_caballo: int,
    id_foto: int,
    request: Request,
    service: SubirFotosService = Depends(get_subir_fotos_service),
):
    id_usuario = _obtener_id_usuario_autenticado(request)

    try:
        with engine.begin() as connection:

            caballo = connection.execute(
                text("""
                    SELECT id_caballo, disponibilidad
                    FROM caballo
                    WHERE id_caballo = :id
                      AND usuario_id_usuario = :uid
                """),
                {"id": id_caballo, "uid": id_usuario},
            ).first()

            if caballo is None:
                raise HTTPException(404, "Caballo no encontrado")

            if caballo.disponibilidad == "Eliminado":
                raise HTTPException(404, "Caballo no encontrado")

            foto = connection.execute(
                text("""
                    SELECT id_foto, ruta
                    FROM foto_caballo
                    WHERE id_foto = :id_foto
                      AND id_caballo = :id_caballo
                """),
                {"id_foto": id_foto, "id_caballo": id_caballo},
            ).first()

            if foto is None:
                raise HTTPException(404, "Foto no encontrada")

            connection.execute(
                text("DELETE FROM foto_caballo WHERE id_foto = :id_foto"),
                {"id_foto": id_foto},
            )

        try:
            service.eliminar_archivo(foto.ruta)
        except Exception as e:
            registrar_auditoria(
                accion="ELIMINAR_FOTOGRAFIA",
                modulo="FOTOGRAFIAS",
                resultado="FALLIDO",
                usuario_id=id_usuario,
                detalle=f"El registro de la fotografía {id_foto} fue eliminado de la base de datos, pero falló el borrado del archivo físico del caballo {id_caballo}: {e}",
            )
            raise HTTPException(
                status_code=500,
                detail="La fotografía fue retirada de la base de datos, pero no se pudo eliminar su archivo físico.",
            )

        service.promover_principal(id_caballo)

        registrar_auditoria(
            accion="ELIMINAR_FOTOGRAFIA",
            modulo="FOTOGRAFIAS",
            resultado="EXITOSO",
            usuario_id=id_usuario,
            detalle=f"Se eliminó la fotografía {id_foto} del caballo {id_caballo}.",
        )


        return {
            "mensaje": "Foto eliminada correctamente",
            "id_foto": id_foto,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar la foto: {str(e)}",
        )
