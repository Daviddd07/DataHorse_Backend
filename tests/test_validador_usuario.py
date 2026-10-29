
import pytest

from app.domain.services.validador_usuario import validar_registro
from app.domain.exceptions import DatosInvalidosError


def test_registro_valido():
    resultado = validar_registro(
        nombre="María Pérez",
        correo="maria@example.com",
        contrasena="ClaveSegura123",
        telefono="3001234567",
        ubicacion="Fusagasugá",
    )

    assert resultado is None


def test_registro_valido_sin_telefono_ni_ubicacion():
    resultado = validar_registro(
        nombre="María",
        correo="maria@example.com",
        contrasena="ClaveSegura123",
        telefono=None,
        ubicacion=None,
    )

    assert resultado is None


@pytest.mark.parametrize("nombre", ["A", ""])
def test_nombre_demasiado_corto(nombre):
    with pytest.raises(DatosInvalidosError):
        validar_registro(
            nombre=nombre,
            correo="maria@example.com",
            contrasena="ClaveSegura123",
            telefono=None,
            ubicacion=None,
        )


def test_correo_invalido():
    with pytest.raises(DatosInvalidosError):
        validar_registro(
            nombre="María",
            correo="correo-invalido",
            contrasena="ClaveSegura123",
            telefono=None,
            ubicacion=None,
        )


@pytest.mark.parametrize(
    "contrasena",
    [
        "cort1",
        "solominusculas123",
        "SOLOMAYUSCULAS123",
        "SinNumerosABC",
    ],
)
def test_contrasena_invalida(contrasena):
    with pytest.raises(DatosInvalidosError):
        validar_registro(
            nombre="María",
            correo="maria@example.com",
            contrasena=contrasena,
            telefono=None,
            ubicacion=None,
        )


def test_telefono_invalido():
    with pytest.raises(DatosInvalidosError):
        validar_registro(
            nombre="María",
            correo="maria@example.com",
            contrasena="ClaveSegura123",
            telefono="abc",
            ubicacion=None,
        )


def test_ubicacion_demasiado_larga():
    with pytest.raises(DatosInvalidosError):
        validar_registro(
            nombre="María",
            correo="maria@example.com",
            contrasena="ClaveSegura123",
            telefono=None,
            ubicacion="A" * 181,
        )
