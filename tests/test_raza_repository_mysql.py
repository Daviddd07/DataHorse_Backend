
from unittest.mock import MagicMock, patch

from app.domain.entities.Raza import Raza
from app.infraestructure.adaptadores.outbound.persistence import (
    raza_repository_mysql as modulo,
)


def test_find_all():
    filas = [
        MagicMock(id_raza=1, nombre="Criolla", descripcion="Raza local"),
        MagicMock(id_raza=2, nombre="Árabe", descripcion="Raza equina"),
    ]
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(modulo, "obtener_razas", return_value=filas),
    ):
        resultado = modulo.RazaRepositoryMySQL().find_all()

    assert len(resultado) == 2
    assert all(isinstance(raza, Raza) for raza in resultado)
    assert resultado[0].nombre == "Criolla"
    assert resultado[1].nombre == "Árabe"
    db.close.assert_called_once()


def test_find_all_sin_razas():
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(modulo, "obtener_razas", return_value=[]),
    ):
        resultado = modulo.RazaRepositoryMySQL().find_all()

    assert resultado == []
    db.close.assert_called_once()


def test_find_by_id_encontrada():
    fila = MagicMock(id_raza=1, nombre="Criolla", descripcion="Raza local")
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(modulo, "obtener_raza_por_id", return_value=fila) as consulta,
    ):
        resultado = modulo.RazaRepositoryMySQL().find_by_id(1)

    assert isinstance(resultado, Raza)
    assert resultado.id_raza == 1
    assert resultado.nombre == "Criolla"
    consulta.assert_called_once_with(db, 1)
    db.close.assert_called_once()


def test_find_by_id_no_encontrada():
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(modulo, "obtener_raza_por_id", return_value=None),
    ):
        resultado = modulo.RazaRepositoryMySQL().find_by_id(999)

    assert resultado is None
    db.close.assert_called_once()


def test_create():
    raza = Raza(id_raza=None, nombre="Criolla", descripcion="Raza local")
    fila = MagicMock(id_raza=3, nombre="Criolla", descripcion="Raza local")
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(modulo, "insertar_raza", return_value=fila) as insertar,
    ):
        resultado = modulo.RazaRepositoryMySQL().create(raza)

    assert isinstance(resultado, Raza)
    assert resultado.id_raza == 3
    assert resultado.nombre == "Criolla"
    insertar.assert_called_once_with(
        db,
        {"nombre": "Criolla", "descripcion": "Raza local"},
    )
    db.close.assert_called_once()


def test_find_all_cierra_db_si_falla():
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(modulo, "obtener_razas", side_effect=RuntimeError("Error de consulta")),
    ):
        try:
            modulo.RazaRepositoryMySQL().find_all()
            assert False, "Se esperaba RuntimeError"
        except RuntimeError as error:
            assert str(error) == "Error de consulta"

    db.close.assert_called_once()
