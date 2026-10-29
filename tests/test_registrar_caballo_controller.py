from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
import pytest

from app.infraestructure.adaptadores.inbound.rest import controller


def crear_request_registro():
    from starlette.requests import Request

    return Request({
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/caballos",
        "raw_path": b"/caballos",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    })


def crear_body_registro(**cambios):
    datos = {
        "id_raza": 1,
        "raza_personalizada": None,
        "nombre": "Lucero",
        "sexo": "Macho",
        "fecha_nacimiento": date(2020, 1, 1),
        "altura": 1.6,
        "color": "Castaño",
        "ubicacion": "Fusagasugá",
        "descripcion": "Caballo de prueba",
        "disponibilidad": "Disponible",
        "precio": 1500000,
    }
    datos.update(cambios)
    return controller.CaballoCreateRequest(**datos)


def preparar_registro_caballo():
    conexion = MagicMock()

    usuario_resultado = MagicMock()
    usuario_resultado.first.return_value = SimpleNamespace(id_usuario=10)

    raza_resultado = MagicMock()
    raza_resultado.first.return_value = SimpleNamespace(id_raza=1)

    caballo_resultado = MagicMock()
    caballo_resultado.scalar.return_value = 21

    publicacion_resultado = MagicMock()
    publicacion_resultado.scalar.return_value = 31

    conexion.execute.side_effect = [
        usuario_resultado,
        raza_resultado,
        caballo_resultado,
        MagicMock(),  # INSERT caballo
        publicacion_resultado,
        MagicMock(),  # INSERT publicación
    ]

    contexto = MagicMock()
    contexto.__enter__.return_value = conexion
    return contexto, conexion


def test_registrar_caballo_macho_crea_publicacion():
    contexto, conexion = preparar_registro_caballo()
    geo = {
        "lat": 4.34,
        "lng": -74.36,
        "texto": "Fusagasugá, Cundinamarca",
        "ciudad": "Fusagasugá",
        "departamento": "Cundinamarca",
    }

    with (
        patch.object(controller, "_obtener_id_usuario_autenticado", return_value=10),
        patch.object(controller.engine, "begin", return_value=contexto),
        patch.object(controller, "GeocodingService") as geocoding_class,
    ):
        geocoding_class.return_value.geocodificar.return_value = geo
        resultado = controller.registrar_caballo(
            crear_body_registro(),
            crear_request_registro(),
        )

    assert resultado["mensaje"] == "Publicación registrada correctamente"
    assert resultado["id_caballo"] == 21
    assert resultado["id_publicacion"] == 31
    assert resultado["id_raza"] == 1
    assert resultado["id_usuario"] == 10
    assert conexion.execute.call_count == 6


def test_registrar_caballo_yegua_no_crea_publicacion():
    conexion = MagicMock()

    usuario_resultado = MagicMock()
    usuario_resultado.first.return_value = SimpleNamespace(id_usuario=10)

    raza_resultado = MagicMock()
    raza_resultado.first.return_value = SimpleNamespace(id_raza=1)

    caballo_resultado = MagicMock()
    caballo_resultado.scalar.return_value = 22

    conexion.execute.side_effect = [
        usuario_resultado,
        raza_resultado,
        caballo_resultado,
        MagicMock(),  # INSERT caballo
    ]

    contexto = MagicMock()
    contexto.__enter__.return_value = conexion

    with (
        patch.object(controller, "_obtener_id_usuario_autenticado", return_value=10),
        patch.object(controller.engine, "begin", return_value=contexto),
        patch.object(controller, "GeocodingService") as geocoding_class,
    ):
        geocoding_class.return_value.geocodificar.return_value = None
        resultado = controller.registrar_caballo(
            crear_body_registro(
                sexo="Hembra",
                precio=900000,
            ),
            crear_request_registro(),
        )

    assert resultado["mensaje"] == "Yegua registrada correctamente"
    assert resultado["id_caballo"] == 22
    assert resultado["id_publicacion"] is None
    assert resultado["precio"] is None
    assert conexion.execute.call_count == 4


def test_registrar_caballo_usuario_no_existe():
    conexion = MagicMock()
    resultado_usuario = MagicMock()
    resultado_usuario.first.return_value = None
    conexion.execute.return_value = resultado_usuario

    contexto = MagicMock()
    contexto.__enter__.return_value = conexion

    with (
        patch.object(controller, "_obtener_id_usuario_autenticado", return_value=10),
        patch.object(controller.engine, "begin", return_value=contexto),
        pytest.raises(HTTPException) as error,
    ):
        controller.registrar_caballo(
            crear_body_registro(),
            crear_request_registro(),
        )

    assert error.value.status_code == 404
    assert error.value.detail == "Usuario no encontrado"


def test_registrar_caballo_raza_inexistente():
    conexion = MagicMock()

    resultado_usuario = MagicMock()
    resultado_usuario.first.return_value = SimpleNamespace(id_usuario=10)

    resultado_raza = MagicMock()
    resultado_raza.first.return_value = None

    conexion.execute.side_effect = [resultado_usuario, resultado_raza]

    contexto = MagicMock()
    contexto.__enter__.return_value = conexion

    with (
        patch.object(controller, "_obtener_id_usuario_autenticado", return_value=10),
        patch.object(controller.engine, "begin", return_value=contexto),
        pytest.raises(HTTPException) as error,
    ):
        controller.registrar_caballo(
            crear_body_registro(),
            crear_request_registro(),
        )

    assert error.value.status_code == 404
    assert error.value.detail == "La raza seleccionada no existe"
