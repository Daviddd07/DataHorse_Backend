from unittest.mock import Mock, patch

from argon2.exceptions import InvalidHashError, VerificationError

from app.infraestructure.adaptadores.outbound.argon2_password_hasher import (
    Argon2PasswordHasher,
)


def test_hashear_contrasena():
    hasher = Argon2PasswordHasher()

    resultado = hasher.hashear("ClaveSegura123")

    assert resultado != "ClaveSegura123"
    assert hasher.verificar("ClaveSegura123", resultado) is True


def test_verificar_contrasena_correcta():
    hasher = Argon2PasswordHasher()
    hasher._ph = Mock()
    hasher._ph.verify.return_value = True

    assert hasher.verificar("correcta", "hash-guardado") is True
    hasher._ph.verify.assert_called_once_with("hash-guardado", "correcta")


def test_verificar_contrasena_incorrecta():
    hasher = Argon2PasswordHasher()
    hasher._ph = Mock()
    hasher._ph.verify.side_effect = VerificationError

    assert hasher.verificar("incorrecta", "hash-guardado") is False


def test_verificar_hash_invalido():
    hasher = Argon2PasswordHasher()
    hasher._ph = Mock()
    hasher._ph.verify.side_effect = InvalidHashError

    assert hasher.verificar("clave", "hash-invalido") is False
