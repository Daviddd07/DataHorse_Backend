from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.application.use_cases.registrar_caballo_use_case import (
    RegistrarCaballoUseCase,
)
from app.domain.exceptions import DatosInvalidosError
from app.domain.ports.in_.registrar_caballo_port import RegistrarCaballoComando


@pytest.fixture
def repos():
    caballo = MagicMock()
    raza = MagicMock()
    publicacion = MagicMock()

    raza.find_by_id.return_value = SimpleNamespace(id_raza=3)
    raza.create.return_value = SimpleNamespace(id_raza=9)

    caballo.create.side_effect = lambda c: SimpleNamespace(
        id_caballo=25,
        id_raza=c.id_raza,
        id_propietario=c.id_propietario,
        nombre=c.nombre,
        sexo=c.sexo,
        fecha_nacimiento=c.fecha_nacimiento,
        altura=c.altura,
        color=c.color,
        ubicacion=c.ubicacion,
        descripcion=c.descripcion,
        disponibilidad=c.disponibilidad,
    )

    return caballo, raza, publicacion


def comando(**cambios):
    datos = {
        "id_propietario": 7,
        "nombre": "  Relámpago  ",
        "sexo": "Hembra",
        "fecha_nacimiento": date(2020, 5, 10),
        "altura": 1.55,
        "color": "  Negro  ",
        "ubicacion": "  Bogotá  ",
        "descripcion": "  Caballo de prueba  ",
        "disponibilidad": "Disponible",
        "id_raza": 3,
        "raza_personalizada": None,
        "precio": None,
    }
    datos.update(cambios)
    return RegistrarCaballoComando(**datos)


def crear_caso(repos):
    return RegistrarCaballoUseCase(*repos)


def test_registrar_hembra_sin_publicacion(repos):
    caso = crear_caso(repos)

    resultado = caso.ejecutar(comando())

    assert resultado.id_caballo == 25
    assert resultado.nombre == "Relámpago"
    assert resultado.color == "Negro"
    assert resultado.ubicacion == "Bogotá"
    repos[0].create.assert_called_once()
    repos[1].find_by_id.assert_called_once_with(3)
    repos[2].create.assert_not_called()


def test_registrar_macho_crea_publicacion(repos):
    caso = crear_caso(repos)

    resultado = caso.ejecutar(comando(sexo="Macho", precio=15000000))

    assert resultado.id_caballo == 25
    repos[0].create.assert_called_once()
    repos[2].create.assert_called_once()

    publicacion = repos[2].create.call_args.args[0]
    assert publicacion.id_caballo == 25
    assert publicacion.id_usuario == 7
    assert publicacion.titulo == "Relámpago"
    assert publicacion.precio_referencia == 15000000
    assert publicacion.estado == "Activa"


def test_registrar_con_raza_personalizada(repos):
    caso = crear_caso(repos)

    resultado = caso.ejecutar(
        comando(id_raza=None, raza_personalizada="  Criollo colombiano  ")
    )

    repos[1].create.assert_called_once()
    raza_creada = repos[1].create.call_args.args[0]
    assert raza_creada.nombre == "Otro"
    assert raza_creada.descripcion == "Criollo colombiano"
    assert resultado.id_raza == 9
    repos[1].find_by_id.assert_not_called()


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"nombre": "   "}, "nombre"),
        ({"sexo": "Desconocido"}, "sexo"),
        ({"disponibilidad": "Vendido"}, "disponibilidad"),
        ({"altura": 0}, "altura"),
        ({"altura": None}, "altura"),
        ({"color": "   "}, "datos"),
        ({"ubicacion": "   "}, "datos"),
        ({"descripcion": "   "}, "datos"),
        ({"fecha_nacimiento": None}, "fecha_nacimiento"),
        ({"id_raza": None, "raza_personalizada": None}, "raza"),
        ({"id_raza": 3, "raza_personalizada": "Criollo"}, "raza"),
        ({"sexo": "Macho", "precio": None}, "precio"),
        ({"sexo": "Macho", "precio": 0}, "precio"),
    ],
)
def test_validaciones_rechazan_datos_invalidos(repos, cambios, campo):
    caso = crear_caso(repos)

    with pytest.raises(DatosInvalidosError) as exc:
        caso.ejecutar(comando(**cambios))

    assert exc.value.campo == campo
    repos[0].create.assert_not_called()
    repos[2].create.assert_not_called()


def test_raza_existente_inexistente_lanza_error(repos):
    repos[1].find_by_id.return_value = None
    caso = crear_caso(repos)

    with pytest.raises(DatosInvalidosError) as exc:
        caso.ejecutar(comando(id_raza=999))

    assert exc.value.campo == "raza"
    repos[0].create.assert_not_called()


def test_nombre_raza_personalizada_se_limpia(repos):
    caso = crear_caso(repos)

    caso.ejecutar(
        comando(id_raza=None, raza_personalizada="  Árabe  ")
    )

    raza_creada = repos[1].create.call_args.args[0]
    assert raza_creada.descripcion == "Árabe"


def test_macho_con_precio_negativo_es_rechazado(repos):
    caso = crear_caso(repos)

    with pytest.raises(DatosInvalidosError) as exc:
        caso.ejecutar(comando(sexo="Macho", precio=-100))

    assert exc.value.campo == "precio"
    repos[0].create.assert_not_called()
    repos[2].create.assert_not_called()
