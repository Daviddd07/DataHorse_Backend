from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.infraestructure.adaptadores.inbound.rest import controller


def crear_request():
    return Request({
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/20/favorito",
        "raw_path": b"/20/favorito",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    })


def preparar_conexion(resultados):
    conexion = MagicMock()
    conexion.execute.side_effect = resultados
    contexto = MagicMock()
    contexto.__enter__.return_value = conexion
    return contexto, conexion


def test_agregar_favorito_caballo_no_existe():
    contexto, _ = preparar_conexion([
        MagicMock(first=MagicMock(return_value=None))
    ])

    with (
        patch.object(controller, "_obtener_id_usuario_autenticado", return_value=10),
        patch.object(controller.engine, "begin", return_value=contexto),
        pytest.raises(HTTPException) as error,
    ):
        controller.agregar_favorito(20, crear_request())

    assert error.value.status_code == 404
    assert error.value.detail == "Caballo no encontrado"


def test_agregar_favorito_ya_existe():
    caballo = MagicMock()
    caballo.first.return_value = MagicMock()

    favorito = MagicMock()
    favorito.first.return_value = MagicMock()

    contexto, conexion = preparar_conexion([caballo, favorito])

    with (
        patch.object(controller, "_obtener_id_usuario_autenticado", return_value=10),
        patch.object(controller.engine, "begin", return_value=contexto),
    ):
        resultado = controller.agregar_favorito(20, crear_request())

    assert resultado == {"mensaje": "El caballo ya está en favoritos"}
    assert conexion.execute.call_count == 2


def test_agregar_favorito_correctamente():
    caballo = MagicMock()
    caballo.first.return_value = MagicMock()

    favorito = MagicMock()
    favorito.first.return_value = None

    siguiente = MagicMock()
    siguiente.scalar.return_value = 7

    contexto, conexion = preparar_conexion([
        caballo, favorito, siguiente, MagicMock()
    ])

    with (
        patch.object(controller, "_obtener_id_usuario_autenticado", return_value=10),
        patch.object(controller.engine, "begin", return_value=contexto),
        patch.object(controller, "registrar_auditoria") as auditoria,
    ):
        resultado = controller.agregar_favorito(20, crear_request())

    assert resultado == {
        "mensaje": "Agregado a favoritos",
        "id_favorito": 7,
    }
    assert conexion.execute.call_count == 4
    auditoria.assert_called_once()


def test_quitar_favorito_no_existente():
    resultado_delete = MagicMock()
    resultado_delete.rowcount = 0

    contexto, _ = preparar_conexion([resultado_delete])

    with (
        patch.object(controller, "_obtener_id_usuario_autenticado", return_value=10),
        patch.object(controller.engine, "begin", return_value=contexto),
    ):
        resultado = controller.quitar_favorito(20, crear_request())

    assert resultado == {"mensaje": "El caballo no estaba en favoritos"}


def test_quitar_favorito_correctamente():
    resultado_delete = MagicMock()
    resultado_delete.rowcount = 1

    contexto, conexion = preparar_conexion([resultado_delete])

    with (
        patch.object(controller, "_obtener_id_usuario_autenticado", return_value=10),
        patch.object(controller.engine, "begin", return_value=contexto),
        patch.object(controller, "registrar_auditoria") as auditoria,
    ):
        resultado = controller.quitar_favorito(20, crear_request())

    assert resultado == {"mensaje": "Eliminado de favoritos"}
    conexion.execute.assert_called_once()
    auditoria.assert_called_once()


def test_quitar_favorito_error_base_datos():
    with (
        patch.object(controller, "_obtener_id_usuario_autenticado", return_value=10),
        patch.object(
            controller.engine,
            "begin",
            side_effect=Exception("fallo de BD"),
        ),
        pytest.raises(HTTPException) as error,
    ):
        controller.quitar_favorito(20, crear_request())

    assert error.value.status_code == 500
    assert "fallo de BD" in error.value.detail

def test_agregar_favorito_error_base_datos():
    with (
        patch.object(
            controller,
            "_obtener_id_usuario_autenticado",
            return_value=10,
        ),
        patch.object(
            controller.engine,
            "begin",
            side_effect=Exception("fallo de BD"),
        ),
        pytest.raises(HTTPException) as error,
    ):
        controller.agregar_favorito(20, crear_request())

    assert error.value.status_code == 500
    assert "fallo de BD" in error.value.detail
