from fastapi import Response
from app.infraestructure.adaptadores.inbound.rest import auth_controller as auth


def test_logout_elimina_cookie(monkeypatch):
    monkeypatch.setattr(auth.os, "getenv", lambda key: "development")
    response = Response()

    resultado = auth.logout(response)

    assert "access_token" in response.headers.get("set-cookie", "")
    assert resultado["mensaje"].startswith("Sesi")
    assert resultado["mensaje"].endswith("cerrada correctamente")


def test_logout_produccion(monkeypatch):
    monkeypatch.setattr(auth.os, "getenv", lambda key: "production")
    response = Response()

    auth.logout(response)

    cookie = response.headers.get("set-cookie", "").lower()
    assert "secure" in cookie
    assert "samesite=none" in cookie
