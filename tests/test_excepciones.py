
import pytest

from app.domain.exceptions import (
    RegistroError,
    DatosInvalidosError,
    CorreoYaRegistradoError,
    InvalidCredentialsError,
    EmailAlreadyExistsError,
)


def test_datos_invalidos_guarda_campo_y_mensaje():
    error = DatosInvalidosError("correo", "El correo no es válido")

    assert error.campo == "correo"
    assert error.mensaje == "El correo no es válido"
    assert str(error) == "El correo no es válido"


def test_datos_invalidos_es_un_error_de_registro():
    error = DatosInvalidosError("nombre", "Nombre inválido")

    assert isinstance(error, RegistroError)


def test_correo_ya_registrado_es_una_excepcion():
    error = CorreoYaRegistradoError("El correo ya existe")

    assert isinstance(error, Exception)
    assert str(error) == "El correo ya existe"


def test_alias_email_already_exists():
    assert EmailAlreadyExistsError is CorreoYaRegistradoError


def test_credenciales_invalidas():
    error = InvalidCredentialsError("Credenciales incorrectas")

    assert isinstance(error, Exception)
    assert str(error) == "Credenciales incorrectas"
