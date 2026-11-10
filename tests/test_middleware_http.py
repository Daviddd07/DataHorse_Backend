
import pytest
from unittest.mock import AsyncMock, patch
from starlette.requests import Request
from starlette.responses import Response

import main


def crear_request():
    return Request({
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/prueba",
        "raw_path": b"/prueba",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 1234),
        "server": ("testserver", 80),
    })


@pytest.mark.anyio
async def test_middleware_registra_solicitud_exitosa():
    request = crear_request()
    response_esperada = Response(status_code=200)
    call_next = AsyncMock(return_value=response_esperada)

    with patch.object(main, "guardar_log_tecnico") as guardar_log:
        response = await main.registrar_solicitud_http(
            request,
            call_next,
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    guardar_log.assert_called_once()

    datos = guardar_log.call_args.kwargs
    assert datos["nivel"] == "INFO"
    assert datos["metodo_http"] == "GET"
    assert datos["ruta"] == "/prueba"
    assert datos["estado_http"] == 200
    assert datos["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.anyio
async def test_middleware_registra_error_y_lo_propaga():
    request = crear_request()
    error = RuntimeError("Error simulado")
    call_next = AsyncMock(side_effect=error)

    with patch.object(main, "guardar_log_tecnico") as guardar_log:
        with patch.object(main.logger, "exception"):
            with pytest.raises(RuntimeError, match="Error simulado"):
                await main.registrar_solicitud_http(
                    request,
                    call_next,
                )

    guardar_log.assert_called_once()
    datos = guardar_log.call_args.kwargs
    assert datos["nivel"] == "ERROR"
    assert datos["metodo_http"] == "GET"
    assert datos["ruta"] == "/prueba"
    assert datos["excepcion"] == (
        "Error durante el procesamiento de la solicitud HTTP"
    )


@pytest.mark.anyio
async def test_middleware_guarda_el_log_sin_bloquear_el_servidor():
    """Mientras MySQL guarda el log (lento), el bucle de eventos sigue atendiendo."""
    import asyncio
    import time

    request = crear_request()
    call_next = AsyncMock(return_value=Response(status_code=200))
    latidos = []

    async def latir():
        for _ in range(5):
            latidos.append(time.perf_counter())
            await asyncio.sleep(0.02)

    def guardar_lento(**_):
        time.sleep(0.3)  # simula una escritura lenta en la base

    with patch.object(main, "guardar_log_tecnico", side_effect=guardar_lento):
        inicio = time.perf_counter()
        await asyncio.gather(main.registrar_solicitud_http(request, call_next), latir())

    # Si el log bloqueara el bucle, los latidos ocurrirían recién después de 0.3 s
    assert len(latidos) == 5
    assert latidos[-1] - inicio < 0.25
