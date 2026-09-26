from app.domain.entities.Caballo import Caballo
from app.domain.entities.Raza import Raza
from app.domain.exceptions import DatosInvalidosError
from app.domain.ports.in_.registrar_caballo_port import RegistrarCaballoComando, RegistrarCaballoPort
from app.domain.ports.out.caballo_repository_port import CaballoRepositoryPort
from app.domain.ports.out.raza_repository_port import RazaRepositoryPort

SEXOS_VALIDOS = {"Macho", "Hembra"}
DISPONIBILIDAD_VALIDA = {"Disponible", "No disponible"}
NOMBRE_RAZA_OTRO = "Otro"


class RegistrarCaballoUseCase(RegistrarCaballoPort):
    def __init__(self, caballo_repo: CaballoRepositoryPort, raza_repo: RazaRepositoryPort):
        self._caballo_repo = caballo_repo
        self._raza_repo = raza_repo

    def ejecutar(self, c: RegistrarCaballoComando) -> Caballo:
        nombre = c.nombre.strip()
        color = c.color.strip()
        ubicacion = c.ubicacion.strip()
        descripcion = c.descripcion.strip()
        raza_personalizada = (c.raza_personalizada or "").strip()

        if not nombre:
            raise DatosInvalidosError("nombre", "El nombre es obligatorio")
        if c.sexo not in SEXOS_VALIDOS:
            raise DatosInvalidosError("sexo", "Debe ser 'Macho' o 'Hembra'")
        if c.disponibilidad not in DISPONIBILIDAD_VALIDA:
            raise DatosInvalidosError("disponibilidad", "Debe ser 'Disponible' o 'No disponible'")
        if c.altura is None or c.altura <= 0:
            raise DatosInvalidosError("altura", "La altura debe ser mayor a 0")
        if not color or not ubicacion or not descripcion:
            raise DatosInvalidosError("datos", "Color, ubicación y descripción son obligatorios")
        if c.fecha_nacimiento is None:
            raise DatosInvalidosError("fecha_nacimiento", "La fecha de nacimiento es obligatoria (puede ser aproximada)")

        if c.id_raza is None and not raza_personalizada:
            raise DatosInvalidosError("raza", "Selecciona una raza o escribe una en 'Otro'")
        if c.id_raza is not None and raza_personalizada:
            raise DatosInvalidosError("raza", "Elige una raza existente o escribe una en 'Otro', no ambas")

        if raza_personalizada:
            # Cada "Otro" queda como su propia fila en Raza (nombre='Otro',
            # descripcion=texto libre del usuario), así no se pisan entre caballos.
            nueva_raza = self._raza_repo.create(
                Raza(id_raza=None, nombre=NOMBRE_RAZA_OTRO, descripcion=raza_personalizada)
            )
            id_raza = nueva_raza.id_raza
        else:
            raza_existente = self._raza_repo.find_by_id(c.id_raza)
            if raza_existente is None:
                raise DatosInvalidosError("raza", "La raza seleccionada no existe")
            id_raza = raza_existente.id_raza

        caballo = Caballo(
            id_caballo=None,
            id_raza=id_raza,
            id_propietario=c.id_propietario,
            nombre=nombre,
            sexo=c.sexo,
            fecha_nacimiento=c.fecha_nacimiento,
            altura=c.altura,
            color=color,
            ubicacion=ubicacion,
            descripcion=descripcion,
            disponibilidad=c.disponibilidad,
        )
        return self._caballo_repo.create(caballo)