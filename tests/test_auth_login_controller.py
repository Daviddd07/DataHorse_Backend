from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.responses import Response

from app.application.use_cases.login_use_case import InvalidCredentialsError
from app.infraestructure.adaptadores.inbound.rest import auth_controller as auth


def crear_body():
    return auth.LoginRequest(
        correo="prueba@ejemplo.com",
        password="ClaveSegura123",
    )


def crear_usuario(estado="activo"):
    return SimpleNamespace(
        id_usuario=10,
        correo="prueba@ejemplo.com",
        nombre="Usuario Prueba",
        estado=estado,
    )


def test_login_credenciales_incorrectas():
    use_case = MagicMock()
    use_case.execute.side_effect = InvalidCredentialsError("Credenciales incorrectas")
    repo = MagicMock()

    with (
        patch.object(auth, "registrar_auditoria") as auditoria,
        pytest.raises(HTTPException) as error,
    ):
        auth.login(crear_body(), Response(), use_case, repo)

    assert error.value.status_code == 401
    auditoria.assert_called_once()


def test_login_usuario_no_encontrado():
    use_case = MagicMock()
    use_case.execute.return_value = 10
    repo = MagicMock()
    repo.find_by_id.return_value = None

    with (
        patch.object(auth, "registrar_auditoria") as auditoria,
        pytest.raises(HTTPException) as error,
    ):
        auth.login(crear_body(), Response(), use_case, repo)

    assert error.value.status_code == 401
    assert error.value.detail == "Usuario no encontrado"
    auditoria.assert_called_once()


def test_login_usuario_pendiente_de_verificacion():
    use_case = MagicMock()
    use_case.execute.return_value = 10
    repo = MagicMock()
    repo.find_by_id.return_value = crear_usuario("pendiente")

    with (
        patch.object(auth, "registrar_auditoria") as auditoria,
        pytest.raises(HTTPException) as error,
    ):
        auth.login(crear_body(), Response(), use_case, repo)

    assert error.value.status_code == 403
    auditoria.assert_called_once()


def test_login_exitoso():
    use_case = MagicMock()
    use_case.execute.return_value = 10
    repo = MagicMock()
    repo.find_by_id.return_value = crear_usuario()

    with (
        patch.object(auth, "_crear_cookie") as crear_cookie,
        patch.object(auth, "registrar_auditoria") as auditoria,
    ):
        resultado = auth.login(crear_body(), Response(), use_case, repo)

    assert resultado == {"mensaje": "Login exitoso"}
    crear_cookie.assert_called_once()
    auditoria.assert_called_once()
    use_case.execute.assert_called_once_with(
        "prueba@ejemplo.com", "ClaveSegura123"
    )
