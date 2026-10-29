from datetime import date

from app.domain.entities.Caballo import Caballo
from app.domain.exceptions import DatosInvalidosError, RecursoNoEncontradoError
from app.domain.ports.in_.registrar_caballo_port import RegistrarCaballoComando, RegistrarCaballoPort
from app.domain.ports.out.caballo_repository_port import (
    CaballoRegistrado,
    CaballoRepositoryPort,
    NuevaPublicacion,
)
from app.domain.ports.out.geocoding_port import GeocodingPort
from app.domain.ports.out.raza_repository_port import RazaRepositoryPort
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort

SEXOS_VALIDOS = ("Macho", "Hembra")


class RegistrarCaballoUseCase(RegistrarCaballoPort):
    """Registra un caballo. Los machos además se publican en el marketplace."""

    def __init__(
        self,
        caballo_repo: CaballoRepositoryPort,
        raza_repo: RazaRepositoryPort,
        usuario_repo: UsuarioRepositoryPort,
        geocoding: GeocodingPort,
    ):
        self._caballo_repo = caballo_repo
        self._raza_repo = raza_repo
        self._usuario_repo = usuario_repo
        self._geocoding = geocoding

    def ejecutar(self, c: RegistrarCaballoComando) -> CaballoRegistrado:
        nombre = c.nombre.strip()
        raza_nueva = (c.raza_personalizada or "").strip() or None

        if c.sexo not in SEXOS_VALIDOS:
            raise DatosInvalidosError("sexo", "El sexo debe ser Macho o Hembra")
        if not nombre:
            raise DatosInvalidosError("nombre", "El nombre es obligatorio")
        if c.altura <= 0:
            raise DatosInvalidosError("altura", "La altura debe ser mayor que cero")

        es_macho = c.sexo == "Macho"
        precio = c.precio if es_macho else None

        if es_macho and (precio is None or precio <= 0):
            raise DatosInvalidosError("precio", "Debes ingresar un precio para el caballo")

        if self._usuario_repo.find_by_id(c.id_propietario) is None:
            raise RecursoNoEncontradoError("Usuario no encontrado")

        if raza_nueva is None:
            if c.id_raza is None:
                raise DatosInvalidosError("raza", "Debes seleccionar una raza")
            if self._raza_repo.find_by_id(c.id_raza) is None:
                raise RecursoNoEncontradoError("La raza seleccionada no existe")

        geo = self._geocoding.geocodificar(c.ubicacion)

        caballo = Caballo(
            id_caballo=None,
            id_raza=None if raza_nueva else c.id_raza,
            id_propietario=c.id_propietario,
            nombre=nombre,
            sexo=c.sexo,
            fecha_nacimiento=c.fecha_nacimiento,
            altura=c.altura,
            color=c.color.strip(),
            ubicacion=c.ubicacion.strip(),
            descripcion=c.descripcion.strip(),
            disponibilidad=c.disponibilidad,
            ubicacion_lat=geo.lat if geo else None,
            ubicacion_lng=geo.lng if geo else None,
            ubicacion_texto=geo.texto if geo else c.ubicacion.strip(),
            ciudad=geo.ciudad if geo else None,
            departamento=geo.departamento if geo else None,
        )

        publicacion = (
            NuevaPublicacion(
                titulo=f"{nombre} - {c.sexo}",
                descripcion=caballo.descripcion,
                precio_referencia=precio,
                fecha_publicacion=date.today(),
            )
            if es_macho
            else None
        )

        return self._caballo_repo.registrar(caballo, raza_nueva, publicacion)
