from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from app.infraestructure.adaptadores.inbound.rest import auth_controller as auth


def test_generar_codigo_tiene_seis_digitos(monkeypatch):
    monkeypatch.setattr(auth.secrets, "randbelow", lambda n: 42)
    assert auth._generar_codigo() == "000042"


def test_hash_codigo_falla_si_no_hay_secreto(monkeypatch):
    monkeypatch.setattr(auth, "CODIGO_SECRET", "")
    with pytest.raises(HTTPException) as exc:
        auth._hash_codigo("123456")
    assert exc.value.status_code == 500


def test_hash_codigo_genera_hash(monkeypatch):
    monkeypatch.setattr(auth, "CODIGO_SECRET", "secreto-prueba")
    resultado = auth._hash_codigo("123456")
    assert isinstance(resultado, str)
    assert len(resultado) == 64
    assert resultado == auth._hash_codigo("123456")


@pytest.mark.parametrize(
    "password",
    ["abc", "abcdefgh", "Abcdefgh", "ABCDEFGH1"],
)
def test_validar_password_rechaza_password_insegura(password):
    with pytest.raises(HTTPException) as exc:
        auth._validar_password(password)
    assert exc.value.status_code == 422


def test_validar_password_acepta_password_valida():
    assert auth._validar_password("Clave123") is None


def test_crear_cookie_configuracion_desarrollo(monkeypatch):
    monkeypatch.setattr(auth, "create_access_token", lambda uid: "token-prueba")
    monkeypatch.setattr(auth.os, "getenv", lambda key: "development")
    response = Response()

    auth._crear_cookie(response, 7)

    assert "access_token" in response.headers.get("set-cookie", "")
    assert "httponly" in response.headers.get("set-cookie", "").lower()


def test_crear_cookie_configuracion_produccion(monkeypatch):
    monkeypatch.setattr(auth, "create_access_token", lambda uid: "token-prueba")
    monkeypatch.setattr(auth.os, "getenv", lambda key: "production")
    response = Response()

    auth._crear_cookie(response, 7)

    cookie = response.headers.get("set-cookie", "").lower()
    assert "secure" in cookie
    assert "samesite=none" in cookie


def test_usuario_actual_id_sin_cookie():
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
    })

    with pytest.raises(HTTPException) as exc:
        auth._usuario_actual_id(request)

    assert exc.value.status_code == 401


def test_usuario_actual_id_token_invalido(monkeypatch):
    monkeypatch.setattr(auth, "decode_access_token", lambda token: None)
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"cookie", b"access_token=token-malo")],
        "query_string": b"",
    })

    with pytest.raises(HTTPException) as exc:
        auth._usuario_actual_id(request)

    assert exc.value.status_code == 401


def test_usuario_actual_id_retorna_entero(monkeypatch):
    monkeypatch.setattr(auth, "decode_access_token", lambda token: "23")
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"cookie", b"access_token=token-valido")],
        "query_string": b"",
    })

    assert auth._usuario_actual_id(request) == 23


@pytest.mark.parametrize("valor", ["abc", None])
def test_usuario_actual_id_rechaza_identificador_no_numerico(monkeypatch, valor):
    monkeypatch.setattr(auth, "decode_access_token", lambda token: valor)
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"cookie", b"access_token=token")],
        "query_string": b"",
    })

    with pytest.raises(HTTPException) as exc:
        auth._usuario_actual_id(request)

    assert exc.value.status_code == 401


def test_enviar_codigo_falla_si_mailjet_no_esta_configurado(monkeypatch):
    monkeypatch.setattr(auth, "MAILJET_API_KEY", "")
    monkeypatch.setattr(auth, "MAILJET_SECRET_KEY", "secret")
    monkeypatch.setattr(auth, "MAILJET_SENDER_EMAIL", "test@example.com")

    with pytest.raises(HTTPException) as exc:
        auth._enviar_codigo("destino@example.com", "Prueba", "123456", "REGISTRO")

    assert exc.value.status_code == 500


@pytest.mark.parametrize(
    "tipo,asunto_esperado",
    [
        ("REGISTRO", "Verifica tu cuenta de DataHorse"),
        ("RECUPERAR_PASSWORD", "Recuperación de contraseña - DataHorse"),
    ],
)
def test_enviar_codigo_envia_payload_correcto(monkeypatch, tipo, asunto_esperado):
    monkeypatch.setattr(auth, "MAILJET_API_KEY", "api-key")
    monkeypatch.setattr(auth, "MAILJET_SECRET_KEY", "api-secret")
    monkeypatch.setattr(auth, "MAILJET_SENDER_EMAIL", "origen@example.com")
    monkeypatch.setattr(auth, "MAILJET_SENDER_NAME", "DataHorse")
    monkeypatch.setattr(auth, "CODIGO_EXPIRA_MINUTOS", 10)

    respuesta = SimpleNamespace(ok=True)
    post_mock = MagicMock(return_value=respuesta)
    monkeypatch.setattr(auth.requests, "post", post_mock)

    auth._enviar_codigo("destino@example.com", "Usuario", "123456", tipo)

    post_mock.assert_called_once()
    payload = post_mock.call_args.kwargs["json"]
    mensaje = payload["Messages"][0]
    assert mensaje["Subject"].encode("latin1").decode("utf-8") == asunto_esperado
    assert mensaje["To"][0]["Email"] == "destino@example.com"
    assert "123456" in mensaje["TextPart"]


def test_enviar_codigo_maneja_error_de_conexion(monkeypatch):
    import requests

    monkeypatch.setattr(auth, "MAILJET_API_KEY", "api-key")
    monkeypatch.setattr(auth, "MAILJET_SECRET_KEY", "api-secret")
    monkeypatch.setattr(auth, "MAILJET_SENDER_EMAIL", "origen@example.com")
    monkeypatch.setattr(
        auth.requests,
        "post",
        MagicMock(side_effect=requests.RequestException("sin conexión")),
    )

    with pytest.raises(HTTPException) as exc:
        auth._enviar_codigo("destino@example.com", "Usuario", "123456", "REGISTRO")

    assert exc.value.status_code == 502


def test_enviar_codigo_maneja_rechazo_de_mailjet(monkeypatch):
    monkeypatch.setattr(auth, "MAILJET_API_KEY", "api-key")
    monkeypatch.setattr(auth, "MAILJET_SECRET_KEY", "api-secret")
    monkeypatch.setattr(auth, "MAILJET_SENDER_EMAIL", "origen@example.com")
    monkeypatch.setattr(
        auth.requests,
        "post",
        MagicMock(return_value=SimpleNamespace(ok=False, status_code=400, text="error")),
    )

    with pytest.raises(HTTPException) as exc:
        auth._enviar_codigo("destino@example.com", "Usuario", "123456", "REGISTRO")

    assert exc.value.status_code == 502


def test_logout_elimina_cookie(monkeypatch):
    monkeypatch.setattr(auth.os, "getenv", lambda key: "development")
    response = Response()

    resultado = auth.logout(response)

    assert "access_token" in response.headers.get("set-cookie", "")
    assert resultado["mensaje"].endswith("cerrada correctamente")


def test_logout_produccion(monkeypatch):
    monkeypatch.setattr(auth.os, "getenv", lambda key: "production")
    response = Response()

    auth.logout(response)

    cookie = response.headers.get("set-cookie", "").lower()
    assert "secure" in cookie
    assert "samesite=none" in cookie


