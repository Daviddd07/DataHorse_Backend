from fastapi import APIRouter, Depends

from app.config.dependencies import (
    get_actualizar_caballo_use_case,
    get_eliminar_caballo_use_case,
    get_listar_mis_caballos_use_case,
    get_listar_ubicaciones_use_case,
    get_obtener_caballo_use_case,
    get_registrar_caballo_use_case,
)
from app.domain.ports.in_.caballo_ports import (
    ActualizarCaballoComando,
    ActualizarCaballoPort,
    EliminarCaballoPort,
    ListarMisCaballosPort,
    ListarUbicacionesPort,
    ObtenerCaballoPort,
)
from app.domain.ports.in_.registrar_caballo_port import (
    RegistrarCaballoComando,
    RegistrarCaballoPort,
)
from app.infraestructure.adaptadores.inbound.rest.errores import error_interno
from app.infraestructure.adaptadores.inbound.rest.schemas import (
    CaballoCreateRequest,
    CaballoUpdateRequest,
)
from app.infraestructure.adaptadores.inbound.rest.seguridad import obtener_id_usuario_autenticado

router = APIRouter(prefix="/caballos", tags=["caballos"])


# ======================================================
# UBICACIONES (departamentos y ciudades)
# ======================================================

@router.get("/ubicaciones/departamentos")
def listar_departamentos(
    use_case: ListarUbicacionesPort = Depends(get_listar_ubicaciones_use_case),
):
    with error_interno("Error al consultar departamentos"):
        return [{"departamento": d} for d in use_case.departamentos()]


@router.get("/ubicaciones/ciudades")
def listar_ciudades(
    departamento: str | None = None,
    use_case: ListarUbicacionesPort = Depends(get_listar_ubicaciones_use_case),
):
    with error_interno("Error al consultar ciudades"):
        return [{"ciudad": c} for c in use_case.ciudades(departamento)]


# ======================================================
# REGISTRAR CABALLO (+ PUBLICACIÓN SI ES MACHO)
# ======================================================

@router.post("", status_code=201)
def registrar_caballo(
    body: CaballoCreateRequest,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: RegistrarCaballoPort = Depends(get_registrar_caballo_use_case),
):
    with error_interno("Error al guardar publicación"):
        registrado = use_case.ejecutar(
            RegistrarCaballoComando(id_propietario=id_usuario, **body.model_dump())
        )

    es_macho = body.sexo == "Macho"

    return {
        "mensaje": (
            "Publicación registrada correctamente" if es_macho else "Yegua registrada correctamente"
        ),
        "id_publicacion": registrado.id_publicacion,
        "id_caballo": registrado.id_caballo,
        "id_raza": registrado.id_raza,
        "id_usuario": id_usuario,
        "nombre": body.nombre,
        "sexo": body.sexo,
        "precio": body.precio if es_macho else None,
    }


# ======================================================
# MIS CABALLOS
# (se declara antes de /{id_caballo} para que "mios" no se tome como id)
# ======================================================

@router.get("/mios")
def listar_mis_caballos(
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ListarMisCaballosPort = Depends(get_listar_mis_caballos_use_case),
):
    with error_interno("Error al consultar tus caballos"):
        return use_case.ejecutar(id_usuario)


@router.get("/{id_caballo}")
def obtener_caballo(
    id_caballo: int,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ObtenerCaballoPort = Depends(get_obtener_caballo_use_case),
):
    with error_interno("Error al consultar el caballo"):
        return use_case.ejecutar(id_caballo, id_usuario)


@router.put("/{id_caballo}")
def actualizar_caballo(
    id_caballo: int,
    body: CaballoUpdateRequest,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ActualizarCaballoPort = Depends(get_actualizar_caballo_use_case),
):
    with error_interno("Error al actualizar el caballo"):
        use_case.ejecutar(
            ActualizarCaballoComando(
                id_caballo=id_caballo,
                id_usuario=id_usuario,
                **body.model_dump(),
            )
        )

    return {"mensaje": "Caballo actualizado correctamente", "id_caballo": id_caballo}


# Soft delete del caballo y hard delete de su publicación.
@router.delete("/{id_caballo}")
def eliminar_caballo(
    id_caballo: int,
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: EliminarCaballoPort = Depends(get_eliminar_caballo_use_case),
):
    with error_interno("Error al eliminar el caballo"):
        use_case.ejecutar(id_caballo, id_usuario)

    return {"mensaje": "Caballo eliminado correctamente", "id_caballo": id_caballo}
