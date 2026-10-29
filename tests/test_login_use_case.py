from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.application.use_cases.login_use_case import (
    InvalidCredentialsError,
    LoginUseCase,
)


def test_login_exitoso_normaliza_correo_y_devuelve_id():
    usuario_repo = Mock()
    hasher = Mock()

    usuario_repo.find_by_email.return_value = SimpleNamespace(
        id_usuario=123,
        contrasena="hash_guardado",
    )
    hasher.verificar.return_value = True

    caso_uso = LoginUseCase(usuario_repo, hasher)

    resultado = caso_uso.execute("  USUARIO@CORREO.COM  ", "ClaveSegura123")

    assert resultado == "123"
    usuario_repo.find_by_email.assert_called_once_with("usuario@correo.com")
    hasher.verificar.assert_called_once_with("ClaveSegura123", "hash_guardado")


def test_login_falla_si_usuario_no_existe():
    usuario_repo = Mock()
    hasher = Mock()
    usuario_repo.find_by_email.return_value = None

    caso_uso = LoginUseCase(usuario_repo, hasher)

    with pytest.raises(InvalidCredentialsError, match="Correo o contraseña incorrectos"):
        caso_uso.execute("inexistente@correo.com", "ClaveSegura123")

    hasher.verificar.assert_not_called()


def test_login_falla_si_contrasena_es_incorrecta():
    usuario_repo = Mock()
    hasher = Mock()

    usuario_repo.find_by_email.return_value = SimpleNamespace(
        id_usuario=123,
        contrasena="hash_guardado",
    )
    hasher.verificar.return_value = False

    caso_uso = LoginUseCase(usuario_repo, hasher)

    with pytest.raises(InvalidCredentialsError, match="Correo o contraseña incorrectos"):
        caso_uso.execute("usuario@correo.com", "Incorrecta123")

    hasher.verificar.assert_called_once_with("Incorrecta123", "hash_guardado")


