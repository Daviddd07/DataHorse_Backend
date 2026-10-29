from datetime import date
from unittest.mock import Mock

import pytest

from app.application.use_cases.caballo_use_cases import (
    ActualizarCaballoUseCase,
    EliminarCaballoUseCase,
    ListarMisCaballosUseCase,
    ListarUbicacionesUseCase,
    ObtenerCaballoUseCase,
)
from app.application.use_cases.registrar_caballo_use_case import RegistrarCaballoUseCase
from app.domain.entities.Caballo import Caballo
from app.domain.entities.ubicacion import UbicacionGeocodificada
from app.domain.exceptions import DatosInvalidosError, RecursoNoEncontradoError
from app.domain.ports.in_.caballo_ports import ActualizarCaballoComando
from app.domain.ports.in_.registrar_caballo_port import RegistrarCaballoComando
from app.domain.ports.out.caballo_repository_port import CaballoRegistrado

GEO = UbicacionGeocodificada(
    lat=4.6, lng=-74.0, texto="Bogotá, Colombia", ciudad="Bogotá", departamento="Cundinamarca"
)


def caballo(**cambios):
    datos = dict(
        id_caballo=5,
        id_raza=1,
        id_propietario=10,
        nombre="Lucero",
        sexo="Macho",
        fecha_nacimiento=date(2020, 1, 1),
        altura=1.6,
        color="Castaño",
        ubicacion="Bogotá",
        descripcion="desc",
        disponibilidad="Disponible",
    )
    datos.update(cambios)
    return Caballo(**datos)


# ======================================================
# REGISTRAR
# ======================================================

@pytest.fixture
def registro():
    caballo_repo, raza_repo, usuario_repo, geocoding = Mock(), Mock(), Mock(), Mock()
    usuario_repo.find_by_id.return_value = Mock()
    raza_repo.find_by_id.return_value = Mock()
    geocoding.geocodificar.return_value = GEO
    caballo_repo.registrar.return_value = CaballoRegistrado(5, 1, 9)
    caso = RegistrarCaballoUseCase(caballo_repo, raza_repo, usuario_repo, geocoding)
    return caso, caballo_repo, raza_repo, usuario_repo, geocoding


def comando_registro(**cambios):
    datos = dict(
        id_propietario=10,
        nombre=" Lucero ",
        sexo="Macho",
        fecha_nacimiento=date(2020, 1, 1),
        altura=1.6,
        color=" Castaño ",
        ubicacion=" Bogotá ",
        descripcion=" desc ",
        disponibilidad="Disponible",
        id_raza=1,
        precio=1000,
    )
    datos.update(cambios)
    return RegistrarCaballoComando(**datos)


def test_registrar_macho_crea_publicacion_y_geocodifica(registro):
    caso, caballo_repo, *_ = registro

    resultado = caso.ejecutar(comando_registro())

    assert resultado == CaballoRegistrado(5, 1, 9)
    guardado, raza_nueva, publicacion = caballo_repo.registrar.call_args.args
    assert guardado.nombre == "Lucero"
    assert guardado.color == "Castaño"
    assert guardado.ciudad == "Bogotá"
    assert guardado.ubicacion_lat == 4.6
    assert raza_nueva is None
    assert publicacion.titulo == "Lucero - Macho"
    assert publicacion.precio_referencia == 1000


def test_registrar_hembra_sin_publicacion_y_sin_geo(registro):
    caso, caballo_repo, _, _, geocoding = registro
    geocoding.geocodificar.return_value = None

    caso.ejecutar(comando_registro(sexo="Hembra", precio=500))

    guardado, _, publicacion = caballo_repo.registrar.call_args.args
    assert publicacion is None
    assert guardado.ubicacion_texto == "Bogotá"
    assert guardado.ubicacion_lat is None


def test_registrar_con_raza_personalizada_no_valida_id(registro):
    caso, caballo_repo, raza_repo, *_ = registro

    caso.ejecutar(comando_registro(id_raza=None, raza_personalizada="  Criollo  "))

    guardado, raza_nueva, _ = caballo_repo.registrar.call_args.args
    assert raza_nueva == "Criollo"
    assert guardado.id_raza is None
    raza_repo.find_by_id.assert_not_called()


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"sexo": "Otro"}, "El sexo debe ser Macho o Hembra"),
        ({"nombre": "   "}, "El nombre es obligatorio"),
        ({"altura": 0}, "La altura debe ser mayor que cero"),
        ({"precio": None}, "Debes ingresar un precio para el caballo"),
        ({"precio": -1}, "Debes ingresar un precio para el caballo"),
        ({"id_raza": None}, "Debes seleccionar una raza"),
    ],
)
def test_registrar_rechaza_datos_invalidos(registro, cambios, mensaje):
    caso, caballo_repo, *_ = registro

    with pytest.raises(DatosInvalidosError) as error:
        caso.ejecutar(comando_registro(**cambios))

    assert error.value.mensaje == mensaje
    caballo_repo.registrar.assert_not_called()


def test_registrar_usuario_inexistente(registro):
    caso, _, _, usuario_repo, _ = registro
    usuario_repo.find_by_id.return_value = None

    with pytest.raises(RecursoNoEncontradoError, match="Usuario no encontrado"):
        caso.ejecutar(comando_registro())


def test_registrar_raza_inexistente(registro):
    caso, _, raza_repo, *_ = registro
    raza_repo.find_by_id.return_value = None

    with pytest.raises(RecursoNoEncontradoError, match="La raza seleccionada no existe"):
        caso.ejecutar(comando_registro())


# ======================================================
# ACTUALIZAR
# ======================================================

def comando_actualizar(**cambios):
    datos = dict(
        id_caballo=5,
        id_usuario=10,
        nombre=" Lucero ",
        fecha_nacimiento=date(2020, 1, 1),
        altura=1.6,
        color="Castaño",
        ubicacion="Bogotá",
        descripcion="desc",
        disponibilidad="Disponible",
        id_raza=1,
        precio=1000,
    )
    datos.update(cambios)
    return ActualizarCaballoComando(**datos)


@pytest.fixture
def actualizacion():
    repo, geocoding = Mock(), Mock()
    repo.obtener_de_propietario.return_value = caballo()
    geocoding.geocodificar.return_value = GEO
    return ActualizarCaballoUseCase(repo, geocoding), repo, geocoding


def test_actualizar_macho_sin_cambio_de_ubicacion(actualizacion):
    caso, repo, geocoding = actualizacion

    caso.ejecutar(comando_actualizar())

    geocoding.geocodificar.assert_not_called()
    guardado, raza_nueva, publicacion = repo.actualizar.call_args.args
    assert guardado.nombre == "Lucero"
    assert guardado.ubicacion_lat is None
    assert raza_nueva is None
    assert publicacion.titulo == "Lucero - Macho"


def test_actualizar_hembra_con_raza_nueva_y_ubicacion_nueva(actualizacion):
    caso, repo, geocoding = actualizacion
    repo.obtener_de_propietario.return_value = caballo(sexo="Hembra")

    caso.ejecutar(comando_actualizar(ubicacion="Medellín", id_raza=None, raza_personalizada="Nueva"))

    geocoding.geocodificar.assert_called_once_with("Medellín")
    guardado, raza_nueva, publicacion = repo.actualizar.call_args.args
    assert raza_nueva == "Nueva"
    assert guardado.id_raza is None
    assert guardado.departamento == "Cundinamarca"
    assert publicacion is None


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"nombre": " "}, "El nombre es obligatorio"),
        ({"altura": 0}, "La altura debe ser mayor que cero"),
        ({"disponibilidad": "Eliminado"}, "Disponibilidad invalida"),
        ({"id_raza": None}, "Debes seleccionar una raza"),
        ({"precio": 0}, "Debes ingresar un precio valido"),
    ],
)
def test_actualizar_rechaza_datos_invalidos(actualizacion, cambios, mensaje):
    caso, repo, _ = actualizacion

    with pytest.raises(DatosInvalidosError) as error:
        caso.ejecutar(comando_actualizar(**cambios))

    assert error.value.mensaje == mensaje
    repo.actualizar.assert_not_called()


@pytest.mark.parametrize("actual", [None, caballo(disponibilidad="Eliminado")])
def test_actualizar_caballo_no_encontrado(actualizacion, actual):
    caso, repo, _ = actualizacion
    repo.obtener_de_propietario.return_value = actual

    with pytest.raises(RecursoNoEncontradoError, match="Caballo no encontrado"):
        caso.ejecutar(comando_actualizar())


# ======================================================
# ELIMINAR / CONSULTAS
# ======================================================

def test_eliminar_caballo():
    repo = Mock()
    repo.obtener_de_propietario.return_value = caballo()

    EliminarCaballoUseCase(repo).ejecutar(5, 10)

    repo.obtener_de_propietario.assert_called_once_with(5, 10)
    repo.eliminar.assert_called_once_with(5)


def test_eliminar_caballo_ya_eliminado():
    repo = Mock()
    repo.obtener_de_propietario.return_value = caballo(disponibilidad="Eliminado")

    with pytest.raises(RecursoNoEncontradoError):
        EliminarCaballoUseCase(repo).ejecutar(5, 10)

    repo.eliminar.assert_not_called()


def test_listar_mis_caballos_delega():
    consultas = Mock()
    consultas.listar_de_propietario.return_value = [{"id_caballo": 1}]

    assert ListarMisCaballosUseCase(consultas).ejecutar(10) == [{"id_caballo": 1}]


def test_obtener_caballo():
    consultas = Mock()
    consultas.obtener_detalle_de_propietario.return_value = {"id_caballo": 5}

    assert ObtenerCaballoUseCase(consultas).ejecutar(5, 10) == {"id_caballo": 5}


def test_obtener_caballo_no_encontrado():
    consultas = Mock()
    consultas.obtener_detalle_de_propietario.return_value = None

    with pytest.raises(RecursoNoEncontradoError):
        ObtenerCaballoUseCase(consultas).ejecutar(5, 10)


def test_listar_ubicaciones():
    consultas = Mock()
    consultas.listar_departamentos.return_value = ["Cundinamarca"]
    consultas.listar_ciudades.return_value = ["Bogotá"]
    caso = ListarUbicacionesUseCase(consultas)

    assert caso.departamentos() == ["Cundinamarca"]
    assert caso.ciudades("Cundinamarca") == ["Bogotá"]
    consultas.listar_ciudades.assert_called_once_with("Cundinamarca")
