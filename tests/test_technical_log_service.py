
from unittest.mock import MagicMock, patch

from app.infraestructure.adaptadores.outbound.persistence import (
    technical_log_service,
)


def test_guardar_log_tecnico_exitoso():
    conexion = MagicMock()
    transaccion = MagicMock()

    transaccion.__enter__.return_value = conexion
    transaccion.__exit__.return_value = False

    with patch.object(
        technical_log_service.engine,
        "begin",
        return_value=transaccion,
    ):
        technical_log_service.guardar_log_tecnico(
            nivel="info",
            modulo="pruebas",
            mensaje="Solicitud procesada",
            request_id="test-123",
            metodo_http="GET",
            ruta="/api/v1/ping",
            estado_http=200,
            duracion_ms=15.5,
        )

    conexion.execute.assert_called_once()

    consulta, parametros = conexion.execute.call_args.args

    assert "INSERT INTO logs_tecnicos" in str(consulta)
    assert parametros["nivel"] == "INFO"
    assert parametros["modulo"] == "pruebas"
    assert parametros["mensaje"] == "Solicitud procesada"
    assert parametros["request_id"] == "test-123"
    assert parametros["metodo_http"] == "GET"
    assert parametros["ruta"] == "/api/v1/ping"
    assert parametros["estado_http"] == 200
    assert parametros["duracion_ms"] == 15.5
    assert parametros["excepcion"] is None


def test_error_al_guardar_no_se_propaga():
    with patch.object(
        technical_log_service.engine,
        "begin",
        side_effect=RuntimeError("Error simulado de MySQL"),
    ), patch.object(
        technical_log_service.logger,
        "exception",
    ) as registrar_error:
        resultado = technical_log_service.guardar_log_tecnico(
            nivel="error",
            modulo="pruebas",
            mensaje="Error de prueba",
        )

    assert resultado is None
    registrar_error.assert_called_once_with(
        "No fue posible guardar el log técnico en MySQL."
    )
