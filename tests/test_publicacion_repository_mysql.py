
from unittest.mock import MagicMock, patch

from app.domain.entities.Publicaciones import Publicacion
from app.infraestructure.adaptadores.outbound.persistence import (
    publicacion_repository_mysql as modulo,
)


def test_create():
    publicacion = Publicacion(
        id_publicacion=None,
        id_caballo=2,
        id_usuario=3,
        titulo="Caballo en venta",
        descripcion="Ejemplar de prueba",
        precio_referencia=1500000,
        estado="Activa",
        fecha_publicacion=None,
    )
    fila = MagicMock(
        id_publicacion=10,
        caballo_id_caballo=2,
        usuario_id_usuario=3,
        titulo="Caballo en venta",
        descripcion="Ejemplar de prueba",
        precio_referencia=1500000,
        estado="Activa",
        fecha_publicacion=None,
    )
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(modulo, "insertar_publicacion", return_value=fila) as insertar,
    ):
        resultado = modulo.PublicacionRepositoryMySQL().create(publicacion)

    assert isinstance(resultado, Publicacion)
    assert resultado.id_publicacion == 10
    assert resultado.id_caballo == 2
    assert resultado.id_usuario == 3
    assert resultado.precio_referencia == 1500000.0

    insertar.assert_called_once_with(
        db,
        {
            "caballo_id_caballo": 2,
            "usuario_id_usuario": 3,
            "titulo": "Caballo en venta",
            "descripcion": "Ejemplar de prueba",
            "precio_referencia": 1500000,
            "estado": "Activa",
            "fecha_publicacion": None,
        },
    )
    db.close.assert_called_once()


def test_create_cierra_db_si_falla():
    publicacion = Publicacion(
        id_publicacion=None,
        id_caballo=2,
        id_usuario=3,
        titulo="Caballo en venta",
        descripcion="Ejemplar de prueba",
        precio_referencia=1500000,
        estado="Activa",
        fecha_publicacion=None,
    )
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(
            modulo,
            "insertar_publicacion",
            side_effect=RuntimeError("Error de inserción"),
        ),
    ):
        try:
            modulo.PublicacionRepositoryMySQL().create(publicacion)
            assert False, "Se esperaba RuntimeError"
        except RuntimeError as error:
            assert str(error) == "Error de inserción"

    db.close.assert_called_once()


def test_find_all_activas():
    publicaciones = [
        {"id_publicacion": 1, "titulo": "Caballo en venta"},
        {"id_publicacion": 2, "titulo": "Caballo de cría"},
    ]
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(
            modulo, "obtener_publicaciones_activas", return_value=publicaciones
        ) as consulta,
    ):
        resultado = modulo.PublicacionRepositoryMySQL().find_all_activas()

    assert resultado == publicaciones
    consulta.assert_called_once_with(db)
    db.close.assert_called_once()


def test_find_all_activas_cierra_db_si_falla():
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(
            modulo,
            "obtener_publicaciones_activas",
            side_effect=RuntimeError("Error de consulta"),
        ),
    ):
        try:
            modulo.PublicacionRepositoryMySQL().find_all_activas()
            assert False, "Se esperaba RuntimeError"
        except RuntimeError as error:
            assert str(error) == "Error de consulta"

    db.close.assert_called_once()
