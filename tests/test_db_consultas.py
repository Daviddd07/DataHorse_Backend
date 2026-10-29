
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.infraestructure.adaptadores.outbound.persistence import db_consultas


def crear_db():
    return MagicMock()


def probar_insercion(nombre_funcion, nombre_modelo):
    db = crear_db()
    datos = {"correo": "prueba@test.com"}
    fila = object()

    with patch.object(
        db_consultas, nombre_modelo, return_value=fila
    ) as modelo:
        resultado = getattr(db_consultas, nombre_funcion)(db, datos)

    modelo.assert_called_once_with(**datos)
    db.add.assert_called_once_with(fila)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(fila)
    assert resultado is fila


def test_insertar_raza():
    probar_insercion("insertar_raza", "RazaModel")


def test_obtener_razas():
    db = crear_db()
    razas = [object(), object()]
    db.execute.return_value.scalars.return_value.all.return_value = razas

    resultado = db_consultas.obtener_razas(db)

    assert resultado == razas


def test_obtener_raza_por_id():
    db = crear_db()
    raza = object()
    db.execute.return_value.scalar_one_or_none.return_value = raza

    resultado = db_consultas.obtener_raza_por_id(db, 1)

    assert resultado is raza
