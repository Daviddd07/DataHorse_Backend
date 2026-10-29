from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.infraestructure.adaptadores.inbound.rest import auth_controller as auth


def usuario_prueba(estado="pendiente"):
    return SimpleNamespace(
        id_usuario=10,
        correo="prueba@ejemplo.com",
        nombre="Usuario Prueba",
        estado=estado,
    )


def test_forgot_password_usuario_existente():
    repo = MagicMock()
    repo.find_by_email.return_value = usuario_prueba()

    with patch.object(auth, "_crear_codigo_verificacion") as crear_codigo:
        resultado = auth.forgot_password(
            auth.CorreoRequest(correo="PRUEBA@ejemplo.com"),
            repo,
        )

    assert "recibirás un código" in resultado["mensaje"]
    crear_codigo.assert_called_once_with(
        10, "prueba@ejemplo.com", "Usuario Prueba", "RECUPERAR_PASSWORD"
    )


def test_forgot_password_usuario_inexistente():
    repo = MagicMock()
    repo.find_by_email.return_value = None

    with patch.object(auth, "_crear_codigo_verificacion") as crear_codigo:
        resultado = auth.forgot_password(
            auth.CorreoRequest(correo="prueba@ejemplo.com"),
            repo,
        )

    assert "recibirás un código" in resultado["mensaje"]
    crear_codigo.assert_not_called()


def test_resend_code_usuario_inexistente():
    repo = MagicMock()
    repo.find_by_email.return_value = None

    with pytest.raises(HTTPException) as error:
        auth.resend_code(auth.CorreoRequest(correo="prueba@ejemplo.com"), repo)

    assert error.value.status_code == 404


def test_resend_code_usuario_activo():
    repo = MagicMock()
    repo.find_by_email.return_value = usuario_prueba("activo")

    with patch.object(auth, "_crear_codigo_verificacion") as crear_codigo:
        resultado = auth.resend_code(
            auth.CorreoRequest(correo="prueba@ejemplo.com"),
            repo,
        )

    assert resultado["mensaje"] == "La cuenta ya estÃ¡ verificada"
    crear_codigo.assert_not_called()


def test_resend_code_usuario_pendiente():
    repo = MagicMock()
    repo.find_by_email.return_value = usuario_prueba()

    with patch.object(auth, "_crear_codigo_verificacion") as crear_codigo:
        resultado = auth.resend_code(
            auth.CorreoRequest(correo="prueba@ejemplo.com"),
            repo,
        )

    assert resultado["mensaje"] == "CÃ³digo reenviado correctamente"
    crear_codigo.assert_called_once_with(
        10, "prueba@ejemplo.com", "Usuario Prueba", "REGISTRO"
    )


def test_verify_email_usuario_inexistente():
    repo = MagicMock()
    repo.find_by_email.return_value = None

    with pytest.raises(HTTPException) as error:
        auth.verify_email(
            auth.VerificarCodigoRequest(
                correo="prueba@ejemplo.com", codigo="123456"
            ),
            repo,
        )

    assert error.value.status_code == 404


def test_verify_email_usuario_activo():
    repo = MagicMock()
    repo.find_by_email.return_value = usuario_prueba("activo")

    with patch.object(auth, "_validar_codigo") as validar_codigo:
        resultado = auth.verify_email(
            auth.VerificarCodigoRequest(
                correo="prueba@ejemplo.com", codigo="123456"
            ),
            repo,
        )

    assert resultado["mensaje"] == "La cuenta ya estÃ¡ verificada"
    validar_codigo.assert_not_called()


def test_verify_email_usuario_pendiente():
    repo = MagicMock()
    repo.find_by_email.return_value = usuario_prueba()
    conexion = MagicMock()
    contexto = MagicMock()
    contexto.__enter__.return_value = conexion

    with (
        patch.object(auth, "_validar_codigo") as validar_codigo,
        patch.object(auth.engine, "begin", return_value=contexto),
    ):
        resultado = auth.verify_email(
            auth.VerificarCodigoRequest(
                correo="prueba@ejemplo.com", codigo="123456"
            ),
            repo,
        )

    assert resultado["mensaje"] == "Correo verificado correctamente"
    validar_codigo.assert_called_once_with(10, "123456", "REGISTRO")
    conexion.execute.assert_called_once()


def test_reset_password_usuario_inexistente():
    repo = MagicMock()
    repo.find_by_email.return_value = None

    with pytest.raises(HTTPException) as error:
        auth.reset_password(
            auth.ResetPasswordRequest(
                correo="prueba@ejemplo.com",
                codigo="123456",
                nueva_password="ClaveSegura123",
            ),
            repo,
        )

    assert error.value.status_code == 400


def test_reset_password_actualiza_contrasena():
    repo = MagicMock()
    repo.find_by_email.return_value = usuario_prueba()
    conexion = MagicMock()
    contexto = MagicMock()
    contexto.__enter__.return_value = conexion
    hasher = MagicMock()
    hasher.hashear.return_value = "hash_nuevo"

    with (
        patch.object(auth, "_validar_password") as validar_password,
        patch.object(auth, "_validar_codigo") as validar_codigo,
        patch.object(auth, "Argon2PasswordHasher", return_value=hasher),
        patch.object(auth.engine, "begin", return_value=contexto),
    ):
        resultado = auth.reset_password(
            auth.ResetPasswordRequest(
                correo="prueba@ejemplo.com",
                codigo="123456",
                nueva_password="ClaveSegura123",
            ),
            repo,
        )

    assert resultado["mensaje"] == "ContraseÃ±a actualizada correctamente"
    validar_password.assert_called_once_with("ClaveSegura123")
    validar_codigo.assert_called_once_with(10, "123456", "RECUPERAR_PASSWORD")
    hasher.hashear.assert_called_once_with("ClaveSegura123")
    conexion.execute.assert_called_once()

