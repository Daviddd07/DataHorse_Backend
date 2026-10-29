
from unittest.mock import MagicMock, patch

from app.domain.entities.Caballo import Caballo
from app.infraestructure.adaptadores.outbound.persistence import (
    caballo_repository_mysql as modulo,
)


def crear_caballo():
    return Caballo(
        id_caballo=None,
        id_raza=1,
        id_propietario=2,
        nombre="Relámpago",
        sexo="Macho",
        fecha_nacimiento=None,
        altura=1.55,
        color="Negro",
        ubicacion="Cundinamarca",
        descripcion="Caballo de prueba",
        disponibilidad=True,
    )


def crear_fila():
    return MagicMock(
        id_caballo=10,
        id_raza=1,
        id_propietario=2,
        nombre="Relámpago",
        sexo="Macho",
        fecha_nacimiento=None,
        altura="1.55",
        color="Negro",
        ubicacion="Cundinamarca",
        descripcion="Caballo de prueba",
        disponibilidad=True,
    )


def test_create():
    caballo = crear_caballo()
    fila = crear_fila()
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(modulo, "insertar_caballo", return_value=fila) as insertar,
    ):
        resultado = modulo.CaballoRepositoryMySQL().create(caballo)

    assert isinstance(resultado, Caballo)
    assert resultado.id_caballo == 10
    assert resultado.altura == 1.55

    insertar.assert_called_once_with(
        db,
        {
            "id_raza": 1,
            "id_propietario": 2,
            "nombre": "Relámpago",
            "sexo": "Macho",
            "fecha_nacimiento": None,
            "altura": 1.55,
            "color": "Negro",
            "ubicacion": "Cundinamarca",
            "descripcion": "Caballo de prueba",
            "disponibilidad": True,
        },
    )
    db.close.assert_called_once()


def test_create_cierra_db_si_falla():
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(
            modulo,
            "insertar_caballo",
            side_effect=RuntimeError("Error de inserción"),
        ),
    ):
        try:
            modulo.CaballoRepositoryMySQL().create(crear_caballo())
            assert False, "Se esperaba RuntimeError"
        except RuntimeError as error:
            assert str(error) == "Error de inserción"

    db.close.assert_called_once()


def test_find_all():
    filas = [crear_fila(), crear_fila()]
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(modulo, "obtener_caballos", return_value=filas),
    ):
        resultado = modulo.CaballoRepositoryMySQL().find_all()

    assert len(resultado) == 2
    assert all(isinstance(caballo, Caballo) for caballo in resultado)
    assert resultado[0].altura == 1.55
    db.close.assert_called_once()


def test_find_all_sin_caballos():
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(modulo, "obtener_caballos", return_value=[]),
    ):
        resultado = modulo.CaballoRepositoryMySQL().find_all()

    assert resultado == []
    db.close.assert_called_once()


def test_find_all_cierra_db_si_falla():
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(
            modulo,
            "obtener_caballos",
            side_effect=RuntimeError("Error de consulta"),
        ),
    ):
        try:
            modulo.CaballoRepositoryMySQL().find_all()
            assert False, "Se esperaba RuntimeError"
        except RuntimeError as error:
            assert str(error) == "Error de consulta"

    db.close.assert_called_once()
