from unittest.mock import patch

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.infraestructure.adaptadores.inbound.rest import limitador_login as modulo
from app.infraestructure.adaptadores.inbound.rest.limitador_login import LimitadorPorIp


def test_permite_hasta_el_maximo_y_luego_bloquea():
    limitador = LimitadorPorIp(maximo=3, ventana_segundos=60)

    assert [limitador.registrar("1.1.1.1") for _ in range(3)] == [0, 0, 0]
    assert limitador.registrar("1.1.1.1") > 0


def test_cada_ip_lleva_su_propia_cuenta():
    limitador = LimitadorPorIp(maximo=1, ventana_segundos=60)

    assert limitador.registrar("1.1.1.1") == 0
    assert limitador.registrar("1.1.1.1") > 0
    assert limitador.registrar("2.2.2.2") == 0


def test_libera_al_pasar_la_ventana():
    limitador = LimitadorPorIp(maximo=1, ventana_segundos=60)
    with patch.object(modulo.time, "monotonic", return_value=1000.0):
        assert limitador.registrar("1.1.1.1") == 0
        assert limitador.registrar("1.1.1.1") == 61
    with patch.object(modulo.time, "monotonic", return_value=1060.0):
        assert limitador.registrar("1.1.1.1") == 0


def test_cero_lo_desactiva():
    assert not LimitadorPorIp(maximo=0, ventana_segundos=60).activo


def cliente_con_limite(maximo):
    app = FastAPI()

    @app.post("/login", dependencies=[Depends(modulo.limitar_login)])
    def login():
        return {"mensaje": "ok"}

    return TestClient(app), LimitadorPorIp(maximo=maximo, ventana_segundos=60)


def test_endpoint_responde_429_con_retry_after():
    cliente, limitador = cliente_con_limite(2)
    with patch.object(modulo, "limitador_login", limitador):
        codigos = [cliente.post("/login").status_code for _ in range(2)]
        bloqueada = cliente.post("/login")

    assert codigos == [200, 200]
    assert bloqueada.status_code == 429
    assert int(bloqueada.headers["retry-after"]) > 0


def test_endpoint_sin_limite_si_esta_desactivado():
    cliente, limitador = cliente_con_limite(0)
    with patch.object(modulo, "limitador_login", limitador):
        assert all(cliente.post("/login").status_code == 200 for _ in range(50))
