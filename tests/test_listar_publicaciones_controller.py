from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.infraestructure.adaptadores.inbound.rest import controller


def crear_request_publicaciones():
    return Request({
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/publicaciones",
        "raw_path": b"/publicaciones",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    })


def crear_fila_publicacion(**cambios):
    datos = {
        "id_publicacion": 5,
        "titulo": "Caballo disponible",
        "descripcion": "Descripción de prueba",
        "fecha_publicacion": datetime(2026, 1, 15),
        "estado": "Activa",
        "precio_referencia": 1500000,
        "usuario_id_usuario": 10,
        "id_caballo": 20,
        "nombre": "Lucero",
        "sexo": "Macho",
        "fecha_nacimiento": date(2020, 1, 1),
        "altura": 1.6,
        "color": "Castaño",
        "ubicacion_texto": "Fusagasugá",
        "ciudad": "Fusagasugá",
        "departamento": "Cundinamarca",
        "ubicacion_lat": 4.34,
        "ubicacion_lng": -74.36,
        "ubicacion": "Fusagasugá, Cundinamarca",
        "disponibilidad": "Disponible",
        "id_raza": 1,
        "raza": "Criollo",
        "propietario": "Usuario Prueba",
        "foto_ruta": "uploads/lucero.jpg",
        "es_favorita": 1,
    }
    datos.update(cambios)
    return SimpleNamespace(**datos)


def preparar_conexion(resultado):
    conexion = MagicMock()
    conexion.execute.return_value = resultado
    contexto = MagicMock()
    contexto.__enter__.return_value = conexion
    return contexto, conexion


def test_listar_publicaciones_correctamente():
    fila = crear_fila_publicacion()
    contexto, conexion = preparar_conexion([fila])

    with (
        patch.object(controller, "_obtener_id_usuario_autenticado", return_value=10),
        patch.object(controller.engine, "connect", return_value=contexto),
    ):
        resultado = controller.listar_publicaciones(crear_request_publicaciones())

    assert len(resultado) == 1
    publicacion = resultado[0]
    assert publicacion["id_publicacion"] == 5
    assert publicacion["id_caballo"] == 20
    assert publicacion["precio"] == 1500000.0
    assert publicacion["es_mia"] is True
    assert publicacion["es_favorita"] is True
    assert publicacion["foto_principal"] == "/uploads/lucero.jpg"
    conexion.execute.assert_called_once()


def test_listar_publicaciones_campos_opcionales_vacios():
    fila = crear_fila_publicacion(
        usuario_id_usuario=12,
        precio_referencia=None,
        ubicacion_lat=None,
        ubicacion_lng=None,
        foto_ruta=None,
        es_favorita=0,
    )
    contexto, _ = preparar_conexion([fila])

    with (
        patch.object(controller, "_obtener_id_usuario_autenticado", return_value=10),
        patch.object(controller.engine, "connect", return_value=contexto),
    ):
        resultado = controller.listar_publicaciones(crear_request_publicaciones())

    publicacion = resultado[0]
    assert publicacion["precio"] is None
    assert publicacion["ubicacion_lat"] is None
    assert publicacion["ubicacion_lng"] is None
    assert publicacion["foto_principal"] is None
    assert publicacion["es_mia"] is False
    assert publicacion["es_favorita"] is False


def test_listar_publicaciones_sin_resultados():
    contexto, _ = preparar_conexion([])

    with (
        patch.object(controller, "_obtener_id_usuario_autenticado", return_value=10),
        patch.object(controller.engine, "connect", return_value=contexto),
    ):
        resultado = controller.listar_publicaciones(crear_request_publicaciones())

    assert resultado == []


def test_listar_publicaciones_error_base_datos():
    with (
        patch.object(controller, "_obtener_id_usuario_autenticado", return_value=10),
        patch.object(
            controller.engine,
            "connect",
            side_effect=Exception("fallo de BD"),
        ),
        pytest.raises(HTTPException) as error,
    ):
        controller.listar_publicaciones(crear_request_publicaciones())

    assert error.value.status_code == 500
    assert "fallo de BD" in error.value.detail
