from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.infraestructure.adaptadores.inbound.rest import controller


def crear_request(cookies=None):
    cookies = cookies or {}
    cookie_header = "; ".join(
        f"{nombre}={valor}" for nombre, valor in cookies.items()
    )

    headers = []
    if cookie_header:
        headers.append((b"cookie", cookie_header.encode("latin-1")))

    return Request({
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    })


def test_obtener_usuario_sin_cookie():
    with pytest.raises(HTTPException) as exc:
        controller._obtener_id_usuario_autenticado(crear_request())

    assert exc.value.status_code == 401
    assert exc.value.detail == "No autenticado"


def test_obtener_usuario_token_invalido():
    request = crear_request({"access_token": "token-invalido"})

    with patch.object(controller, "decode_access_token", return_value=None):
        with pytest.raises(HTTPException) as exc:
            controller._obtener_id_usuario_autenticado(request)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Sesión inválida o expirada"


def test_obtener_usuario_token_no_numerico():
    request = crear_request({"access_token": "token"})

    with patch.object(controller, "decode_access_token", return_value="abc"):
        with pytest.raises(HTTPException) as exc:
            controller._obtener_id_usuario_autenticado(request)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Sesión inválida"


def test_obtener_usuario_autenticado_correctamente():
    request = crear_request({"access_token": "token-valido"})

    with patch.object(controller, "decode_access_token", return_value="27"):
        resultado = controller._obtener_id_usuario_autenticado(request)

    assert resultado == 27


def test_listar_departamentos_correctamente():
    filas = [
        SimpleNamespace(departamento="Cundinamarca"),
        SimpleNamespace(departamento="Tolima"),
    ]
    conexion = MagicMock()
    conexion.execute.return_value = filas

    with patch.object(controller.engine, "connect") as conectar:
        conectar.return_value.__enter__.return_value = conexion
        resultado = controller.listar_departamentos()

    assert resultado == [
        {"departamento": "Cundinamarca"},
        {"departamento": "Tolima"},
    ]


def test_listar_departamentos_error_bd():
    with patch.object(
        controller.engine, "connect", side_effect=Exception("fallo de BD")
    ):
        with pytest.raises(HTTPException) as exc:
            controller.listar_departamentos()

    assert exc.value.status_code == 500
    assert "fallo de BD" in exc.value.detail


def test_listar_ciudades_por_departamento():
    filas = [
        SimpleNamespace(ciudad="Fusagasugá"),
        SimpleNamespace(ciudad="Girardot"),
    ]
    conexion = MagicMock()
    conexion.execute.return_value = filas

    with patch.object(controller.engine, "connect") as conectar:
        conectar.return_value.__enter__.return_value = conexion
        resultado = controller.listar_ciudades("Cundinamarca")

    assert resultado == [
        {"ciudad": "Fusagasugá"},
        {"ciudad": "Girardot"},
    ]
    assert conexion.execute.call_args.args[1] == {
        "departamento": "Cundinamarca"
    }


def test_listar_ciudades_sin_departamento():
    filas = [SimpleNamespace(ciudad="Bogotá")]
    conexion = MagicMock()
    conexion.execute.return_value = filas

    with patch.object(controller.engine, "connect") as conectar:
        conectar.return_value.__enter__.return_value = conexion
        resultado = controller.listar_ciudades()

    assert resultado == [{"ciudad": "Bogotá"}]
    assert len(conexion.execute.call_args.args) == 1


def test_listar_ciudades_error_bd():
    with patch.object(
        controller.engine, "connect", side_effect=Exception("fallo de BD")
    ):
        with pytest.raises(HTTPException) as exc:
            controller.listar_ciudades()

    assert exc.value.status_code == 500
    assert "fallo de BD" in exc.value.detail
