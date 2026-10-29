from dataclasses import replace
from typing import List, Optional

from app.domain.entities.Caballo import Caballo
from app.domain.exceptions import DatosInvalidosError, RecursoNoEncontradoError
from app.domain.ports.in_.caballo_ports import (
    ActualizarCaballoComando,
    ActualizarCaballoPort,
    EliminarCaballoPort,
    ListarMisCaballosPort,
    ListarUbicacionesPort,
    ObtenerCaballoPort,
)
from app.domain.ports.out.caballo_consultas_port import CaballoConsultasPort
from app.domain.ports.out.caballo_repository_port import (
    CaballoRepositoryPort,
    CambiosPublicacion,
)
from app.domain.ports.out.geocoding_port import GeocodingPort
from app.domain.ports.out.ubicacion_consultas_port import UbicacionConsultasPort

DISPONIBILIDAD_EDITABLE = ("Disponible", "No disponible")


def obtener_caballo_activo(
    repo: CaballoRepositoryPort,
    id_caballo: int,
    id_usuario: int,
) -> Caballo:
    """Devuelve el caballo del usuario o lanza 404 si no existe o fue eliminado."""
    caballo = repo.obtener_de_propietario(id_caballo, id_usuario)

    if caballo is None or caballo.eliminado:
        raise RecursoNoEncontradoError("Caballo no encontrado")

    return caballo


class ListarMisCaballosUseCase(ListarMisCaballosPort):
    def __init__(self, consultas: CaballoConsultasPort):
        self._consultas = consultas

    def ejecutar(self, id_usuario: int) -> List[dict]:
        return self._consultas.listar_de_propietario(id_usuario)


class ObtenerCaballoUseCase(ObtenerCaballoPort):
    def __init__(self, consultas: CaballoConsultasPort):
        self._consultas = consultas

    def ejecutar(self, id_caballo: int, id_usuario: int) -> dict:
        caballo = self._consultas.obtener_detalle_de_propietario(id_caballo, id_usuario)

        if caballo is None:
            raise RecursoNoEncontradoError("Caballo no encontrado")

        return caballo


class ActualizarCaballoUseCase(ActualizarCaballoPort):
    def __init__(self, caballo_repo: CaballoRepositoryPort, geocoding: GeocodingPort):
        self._caballo_repo = caballo_repo
        self._geocoding = geocoding

    def ejecutar(self, c: ActualizarCaballoComando) -> None:
        nombre = c.nombre.strip()
        ubicacion = c.ubicacion.strip()
        raza_nueva = (c.raza_personalizada or "").strip() or None

        if not nombre:
            raise DatosInvalidosError("nombre", "El nombre es obligatorio")
        if c.altura <= 0:
            raise DatosInvalidosError("altura", "La altura debe ser mayor que cero")
        if c.disponibilidad not in DISPONIBILIDAD_EDITABLE:
            raise DatosInvalidosError("disponibilidad", "Disponibilidad invalida")

        actual = obtener_caballo_activo(self._caballo_repo, c.id_caballo, c.id_usuario)

        if raza_nueva is None and c.id_raza is None:
            raise DatosInvalidosError("raza", "Debes seleccionar una raza")

        precio = c.precio if actual.es_macho else None

        if actual.es_macho and (precio is None or precio <= 0):
            raise DatosInvalidosError("precio", "Debes ingresar un precio valido")

        # Solo se vuelve a geocodificar si la ubicación cambió;
        # los campos en None conservan el valor guardado.
        geo = self._geocoding.geocodificar(c.ubicacion) if actual.ubicacion != ubicacion else None

        caballo = replace(
            actual,
            id_raza=None if raza_nueva else c.id_raza,
            nombre=nombre,
            fecha_nacimiento=c.fecha_nacimiento,
            altura=c.altura,
            color=c.color.strip(),
            ubicacion=ubicacion,
            descripcion=c.descripcion.strip(),
            disponibilidad=c.disponibilidad,
            ubicacion_lat=geo.lat if geo else None,
            ubicacion_lng=geo.lng if geo else None,
            ubicacion_texto=geo.texto if geo else ubicacion,
            ciudad=geo.ciudad if geo else None,
            departamento=geo.departamento if geo else None,
        )

        publicacion = (
            CambiosPublicacion(
                titulo=f"{nombre} - Macho",
                descripcion=caballo.descripcion,
                precio_referencia=precio,
            )
            if actual.es_macho
            else None
        )

        self._caballo_repo.actualizar(caballo, raza_nueva, publicacion)


class EliminarCaballoUseCase(EliminarCaballoPort):
    def __init__(self, caballo_repo: CaballoRepositoryPort):
        self._caballo_repo = caballo_repo

    def ejecutar(self, id_caballo: int, id_usuario: int) -> None:
        obtener_caballo_activo(self._caballo_repo, id_caballo, id_usuario)
        self._caballo_repo.eliminar(id_caballo)


class ListarUbicacionesUseCase(ListarUbicacionesPort):
    def __init__(self, consultas: UbicacionConsultasPort):
        self._consultas = consultas

    def departamentos(self) -> List[str]:
        return self._consultas.listar_departamentos()

    def ciudades(self, departamento: Optional[str] = None) -> List[str]:
        return self._consultas.listar_ciudades(departamento)
