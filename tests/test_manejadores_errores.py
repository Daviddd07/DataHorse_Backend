
import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from main import (
    TITULOS_HTTP,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)
from tests.test_middleware_http import crear_request


@pytest.mark.anyio
async def test_manejador_http_exception():
    request = crear_request()
    exc = HTTPException(status_code=404, detail="No encontrado")

    response = await http_exception_handler(request, exc)

    assert response.status_code == 404
    assert response.media_type == "application/problem+json"

    contenido = response.body.decode("utf-8")
    assert '"title":"Not Found"' in contenido
    assert '"detail":"No encontrado"' in contenido
    assert '"instance":"/prueba"' in contenido


@pytest.mark.anyio
async def test_manejador_http_exception_estado_desconocido():
    request = crear_request()
    exc = HTTPException(status_code=418, detail="Error de prueba")

    response = await http_exception_handler(request, exc)

    assert response.status_code == 418
    assert "Error" in response.body.decode("utf-8")


@pytest.mark.anyio
async def test_manejador_validacion_con_errores():
    request = crear_request()
    exc = RequestValidationError([
        {
            "type": "missing",
            "loc": ("body", "correo"),
            "msg": "Field required",
            "input": None,
        }
    ])

    response = await validation_exception_handler(request, exc)

    assert response.status_code == 422
    assert response.media_type == "application/problem+json"
    assert "Field required" in response.body.decode("utf-8")


@pytest.mark.anyio
async def test_manejador_validacion_sin_errores():
    request = crear_request()
    exc = RequestValidationError([])

    response = await validation_exception_handler(request, exc)

    assert response.status_code == 422
    assert "Datos de entrada" in response.body.decode("utf-8")


@pytest.mark.anyio
async def test_manejador_error_interno():
    request = crear_request()
    exc = RuntimeError("Error simulado")

    from unittest.mock import patch

    with patch("main.logger.exception") as registrar_error:
        response = await general_exception_handler(request, exc)

    assert response.status_code == 500
    assert response.media_type == "application/problem+json"
    assert "Internal Server Error" in response.body.decode("utf-8")
    registrar_error.assert_called_once()


def test_titulos_http_definidos():
    assert TITULOS_HTTP[404] == "Not Found"
    assert TITULOS_HTTP[422] == "Unprocessable Entity"
    assert TITULOS_HTTP[500] == "Internal Server Error"
