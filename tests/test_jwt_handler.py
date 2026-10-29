
from datetime import datetime, timezone
from unittest.mock import patch

import jwt

from app.infraestructure.adaptadores.outbound.security import (
    jwt_handler as modulo,
)


CLAVE_PRUEBA = "clave-de-prueba-segura-de-32-bytes-minimo"


def test_create_access_token():
    with patch.object(modulo, "SECRET_KEY", CLAVE_PRUEBA):
        token = modulo.create_access_token(123)

    payload = jwt.decode(
        token,
        CLAVE_PRUEBA,
        algorithms=[modulo.ALGORITHM],
    )

    assert payload["sub"] == "123"
    assert "exp" in payload


def test_create_access_token_con_id_texto():
    with patch.object(modulo, "SECRET_KEY", CLAVE_PRUEBA):
        token = modulo.create_access_token("usuario-abc")

    payload = jwt.decode(
        token,
        CLAVE_PRUEBA,
        algorithms=[modulo.ALGORITHM],
    )

    assert payload["sub"] == "usuario-abc"


def test_decode_access_token_valido():
    token = jwt.encode(
        {
            "sub": "123",
            "exp": datetime.now(timezone.utc).timestamp() + 300,
        },
        modulo.SECRET_KEY,
        algorithm=modulo.ALGORITHM,
    )

    assert modulo.decode_access_token(token) == "123"


def test_decode_access_token_sub_como_numero():
    token = jwt.encode(
        {
            "sub": 123,
            "exp": datetime.now(timezone.utc).timestamp() + 300,
        },
        modulo.SECRET_KEY,
        algorithm=modulo.ALGORITHM,
    )

    assert modulo.decode_access_token(token) is None


def test_decode_access_token_sin_sub():
    token = jwt.encode(
        {
            "exp": datetime.now(timezone.utc).timestamp() + 300,
        },
        modulo.SECRET_KEY,
        algorithm=modulo.ALGORITHM,
    )

    assert modulo.decode_access_token(token) is None


def test_decode_access_token_invalido():
    assert modulo.decode_access_token("token-invalido") is None


def test_jwt_token_service_delega_en_funciones():
    servicio = modulo.JwtTokenService()

    token = servicio.crear(7)

    assert servicio.decodificar(token) == "7"
    assert servicio.decodificar("token-invalido") is None
