from unittest.mock import MagicMock, patch

import pytest
import requests

from app.domain.exceptions import (
    ConfiguracionError,
    NoAutenticadoError,
    ServicioExternoError,
)
from app.infraestructure.adaptadores.outbound.almacenamiento.almacenamiento_local import (
    AlmacenamientoLocal,
)
from app.infraestructure.adaptadores.outbound.correo import mailjet_enviador
from app.infraestructure.adaptadores.outbound.geocoding import nominatim_geocoding
from app.infraestructure.adaptadores.outbound.security import google_verificador
from app.infraestructure.adaptadores.outbound.security.hmac_codigo_hasher import HmacCodigoHasher


def respuesta_http(status=200, datos=None, ok=True):
    respuesta = MagicMock()
    respuesta.status_code = status
    respuesta.ok = ok
    respuesta.json.return_value = datos
    return respuesta


# ======================================================
# NOMINATIM
# ======================================================

RESULTADO_OSM = {
    "lat": "4.33",
    "lon": "-74.36",
    "display_name": "Fusagasugá, Cundinamarca",
    "address": {"town": "Fusagasugá", "state": "Cundinamarca"},
}


@pytest.mark.parametrize("texto", ["", "   ", None])
def test_geocoding_texto_vacio_no_consulta(texto):
    with patch.object(nominatim_geocoding.requests, "get") as get:
        assert nominatim_geocoding.NominatimGeocoding().geocodificar(texto) is None

    get.assert_not_called()


def test_geocoding_exitoso():
    with patch.object(nominatim_geocoding.requests, "get", return_value=respuesta_http(datos=[RESULTADO_OSM])) as get:
        geo = nominatim_geocoding.NominatimGeocoding(timeout=3).geocodificar(" Fusagasugá ")

    assert geo.lat == 4.33 and geo.lng == -74.36
    assert geo.ciudad == "Fusagasugá"
    assert geo.departamento == "Cundinamarca"
    assert get.call_args.kwargs["params"]["q"] == "Fusagasugá"
    assert get.call_args.kwargs["timeout"] == 3


@pytest.mark.parametrize(
    "respuesta",
    [respuesta_http(status=500), respuesta_http(datos=[]), respuesta_http(datos=[{"lat": "x", "lon": "1"}])],
)
def test_geocoding_sin_resultado_utilizable(respuesta):
    with patch.object(nominatim_geocoding.requests, "get", return_value=respuesta):
        assert nominatim_geocoding.NominatimGeocoding().geocodificar("Lugar") is None


def test_geocoding_error_de_red():
    with patch.object(nominatim_geocoding.requests, "get", side_effect=requests.Timeout()):
        assert nominatim_geocoding.NominatimGeocoding().geocodificar("Lugar") is None


# ======================================================
# MAILJET
# ======================================================

def enviador(**cambios):
    datos = dict(api_key="k", secret_key="s", remitente="no-reply@datahorse.com")
    datos.update(cambios)
    return mailjet_enviador.MailjetEnviadorCodigo(**datos)


@pytest.mark.parametrize("tipo", ["REGISTRO", "RECUPERAR_PASSWORD"])
def test_mailjet_envia_plantilla_correcta(tipo):
    with patch.object(mailjet_enviador.requests, "post", return_value=respuesta_http()) as post:
        enviador().enviar("ana@test.com", "Ana", "123456", tipo, 10)

    mensaje = post.call_args.kwargs["json"]["Messages"][0]
    assert mensaje["Subject"] == mailjet_enviador.PLANTILLAS[tipo][0]
    assert "123456" in mensaje["HTMLPart"]
    assert "10 minutos" in mensaje["TextPart"]
    assert post.call_args.kwargs["auth"] == ("k", "s")


def test_mailjet_sin_configuracion():
    with pytest.raises(ConfiguracionError):
        enviador(api_key=None).enviar("ana@test.com", "Ana", "123456", "REGISTRO", 10)


def test_mailjet_error_de_conexion():
    with patch.object(mailjet_enviador.requests, "post", side_effect=requests.ConnectionError()):
        with pytest.raises(ServicioExternoError, match="conectar"):
            enviador().enviar("ana@test.com", "Ana", "123456", "REGISTRO", 10)


def test_mailjet_rechaza_envio():
    with patch.object(mailjet_enviador.requests, "post", return_value=respuesta_http(status=401, ok=False)):
        with pytest.raises(ServicioExternoError, match="rechazó"):
            enviador().enviar("ana@test.com", "Ana", "123456", "REGISTRO", 10)


# ======================================================
# HMAC / GOOGLE
# ======================================================

def test_hmac_es_determinista_y_depende_del_secreto():
    hasher = HmacCodigoHasher("secreto")

    assert hasher.hashear("123456") == hasher.hashear("123456")
    assert hasher.hashear("123456") != HmacCodigoHasher("otro").hashear("123456")


def test_hmac_sin_secreto():
    with pytest.raises(ConfiguracionError, match="CODIGO_SECRET"):
        HmacCodigoHasher(None).hashear("123456")


def test_google_verifica_token():
    with patch.object(google_verificador.google_id_token, "verify_oauth2_token", return_value={"sub": "g"}) as verify:
        assert google_verificador.VerificadorGoogle("client").verificar("cred") == {"sub": "g"}

    assert verify.call_args.args[2] == "client"


def test_google_token_invalido():
    with patch.object(google_verificador.google_id_token, "verify_oauth2_token", side_effect=ValueError("malo")):
        with pytest.raises(NoAutenticadoError, match="Token de Google inválido"):
            google_verificador.VerificadorGoogle("client").verificar("cred")


def test_google_sin_client_id():
    with pytest.raises(ConfiguracionError, match="GOOGLE_CLIENT_ID"):
        google_verificador.VerificadorGoogle(None).verificar("cred")


# ======================================================
# ALMACENAMIENTO LOCAL
# ======================================================

def test_almacenamiento_guarda_y_elimina(tmp_path):
    almacenamiento = AlmacenamientoLocal(tmp_path / "caballos", "/uploads/caballos")

    ruta = almacenamiento.guardar(".jpg", b"data")

    assert ruta.startswith("uploads/caballos/") and ruta.endswith(".jpg")
    archivo = tmp_path / "caballos" / ruta.split("/")[-1]
    assert archivo.read_bytes() == b"data"

    almacenamiento.eliminar(ruta)
    assert not archivo.exists()


def test_almacenamiento_eliminar_inexistente_y_sin_salir_del_directorio(tmp_path):
    fuera = tmp_path / "secreto.txt"
    fuera.write_text("x")
    almacenamiento = AlmacenamientoLocal(tmp_path / "caballos", "uploads/caballos")

    almacenamiento.eliminar("uploads/caballos/no-existe.jpg")
    almacenamiento.eliminar("../secreto.txt")

    assert fuera.exists()
