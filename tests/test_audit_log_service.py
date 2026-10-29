from unittest.mock import MagicMock, patch

from app.infraestructure.adaptadores.outbound.persistence import audit_log_service


def test_registrar_auditoria_exitosamente():
    conexion = MagicMock()
    contexto = MagicMock()
    contexto.__enter__.return_value = conexion

    with patch.object(
        audit_log_service.engine, "begin", return_value=contexto
    ):
        audit_log_service.registrar_auditoria(
            accion="CREAR",
            modulo="usuarios",
            resultado="OK",
            usuario_id=1,
            detalle="Usuario creado",
            request_id="req-123",
        )

    conexion.execute.assert_called_once()
    consulta, parametros = conexion.execute.call_args.args

    assert "INSERT INTO audit_logs" in str(consulta)
    assert parametros["usuario_id"] == 1
    assert parametros["accion"] == "CREAR"
    assert parametros["modulo"] == "usuarios"
    assert parametros["resultado"] == "OK"
    assert parametros["detalle"] == "Usuario creado"
    assert parametros["request_id"] == "req-123"


def test_registrar_auditoria_con_campos_opcionales_vacios():
    conexion = MagicMock()
    contexto = MagicMock()
    contexto.__enter__.return_value = conexion

    with patch.object(
        audit_log_service.engine, "begin", return_value=contexto
    ):
        audit_log_service.registrar_auditoria(
            accion="LOGIN",
            modulo="auth",
            resultado="OK",
        )

    _, parametros = conexion.execute.call_args.args

    assert parametros["usuario_id"] is None
    assert parametros["detalle"] is None
    assert parametros["request_id"] is None


def test_registrar_auditoria_maneja_error_de_base_de_datos():
    with (
        patch.object(
            audit_log_service.engine,
            "begin",
            side_effect=Exception("Error de conexión"),
        ),
        patch.object(audit_log_service.logger, "exception") as log_error,
    ):
        resultado = audit_log_service.registrar_auditoria(
            accion="CREAR",
            modulo="usuarios",
            resultado="ERROR",
        )

    assert resultado is None
    log_error.assert_called_once_with(
        "No fue posible guardar el evento de auditoría."
    )
