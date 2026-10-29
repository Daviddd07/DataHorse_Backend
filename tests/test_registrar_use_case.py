from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.application.use_cases.registrar_use_case import RegistrarUseCase
from app.domain.entities.ubicacion import UbicacionGeocodificada
from app.domain.exceptions import EmailAlreadyExistsError


@pytest.fixture
def dependencias():
    repositorio = Mock()
    hasher = Mock()
    hasher.hashear.return_value = "hash-prueba"
    repositorio.find_by_email.return_value = None
    geocoding = Mock()
    geocoding.geocodificar.return_value = None

    caso = RegistrarUseCase(repositorio, hasher, geocoding)
    caso.geocoding = geocoding
    comando = SimpleNamespace(
        nombre="  Ana Pérez  ",
        correo="  ANA@EXAMPLE.COM ",
        telefono=" 3001234567 ",
        ubicacion=None,
        contrasena="ClaveSegura123",
    )
    return caso, repositorio, hasher, comando


def test_registro_exitoso_normaliza_datos(dependencias):
    caso, repositorio, hasher, comando = dependencias
    repositorio.create.return_value = Mock()

    resultado = caso.ejecutar(comando)

    assert resultado is repositorio.create.return_value
    usuario = repositorio.create.call_args.args[0]
    assert usuario.nombre == "Ana Pérez"
    assert usuario.correo == "ana@example.com"
    assert usuario.telefono == "3001234567"
    assert usuario.contrasena == "hash-prueba"
    assert usuario.ubicacion_lat is None
    assert usuario.ubicacion_lng is None
    assert usuario.fecha_registro == date.today()
    hasher.hashear.assert_called_once_with("ClaveSegura123")


def test_registro_con_telefono_y_ubicacion_vacios(dependencias):
    caso, repositorio, _, comando = dependencias
    comando.telefono = "   "
    comando.ubicacion = "   "

    caso.ejecutar(comando)

    usuario = repositorio.create.call_args.args[0]
    assert usuario.telefono is None
    assert usuario.ubicacion is None
    assert usuario.ubicacion_texto is None
    assert usuario.ciudad is None
    assert usuario.departamento is None


def test_registro_con_geocodificacion_exitosa(dependencias):
    caso, repositorio, _, comando = dependencias
    comando.ubicacion = "Fusagasugá, Colombia"
    datos_geo = UbicacionGeocodificada(
        lat=4.3365,
        lng=-74.3638,
        texto="Fusagasugá, Cundinamarca, Colombia",
        ciudad="Fusagasugá",
        departamento="Cundinamarca",
    )
    caso.geocoding.geocodificar.return_value = datos_geo

    caso.ejecutar(comando)

    caso.geocoding.geocodificar.assert_called_once_with("Fusagasugá, Colombia")
    usuario = repositorio.create.call_args.args[0]
    assert usuario.ubicacion_lat == datos_geo.lat
    assert usuario.ubicacion_lng == datos_geo.lng
    assert usuario.ubicacion_texto == datos_geo.texto
    assert usuario.ciudad == datos_geo.ciudad
    assert usuario.departamento == datos_geo.departamento


def test_registro_con_geocodificacion_sin_resultados(dependencias):
    caso, repositorio, _, comando = dependencias
    comando.ubicacion = "Lugar desconocido"

    caso.ejecutar(comando)

    usuario = repositorio.create.call_args.args[0]
    assert usuario.ubicacion_lat is None
    assert usuario.ubicacion_lng is None
    assert usuario.ubicacion_texto == "Lugar desconocido"
    assert usuario.ciudad is None
    assert usuario.departamento is None


def test_registro_correo_existente_lanza_error(dependencias):
    caso, repositorio, hasher, comando = dependencias
    repositorio.find_by_email.return_value = Mock()

    with pytest.raises(EmailAlreadyExistsError):
        caso.ejecutar(comando)

    repositorio.create.assert_not_called()
    hasher.hashear.assert_not_called()
