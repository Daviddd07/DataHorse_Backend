from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

import main
from app.application.use_cases.registrar_logs_use_case import RegistrarLogsUseCase
from app.config import dependencies as deps
from app.domain.entities.log_frontend import LogFrontend
from app.domain.exceptions import DatosInvalidosError
from app.infraestructure.adaptadores.inbound.rest.log_controller import _a_utc_sin_zona
from app.infraestructure.adaptadores.outbound.persistence import db_consultas
from app.infraestructure.adaptadores.outbound.persistence import log_repository_mysql as repo_mod


def log(**cambios):
    datos = dict(
        id_log=None, id_usuario=None, nivel="info", mensaje="prueba", contexto=None,
        url="/login", user_agent="curl", sesion_id="test-1", fecha=datetime(2026, 10, 29, 14, 55),
    )
    datos.update(cambios)
    return LogFrontend(**datos)


def log_json(**cambios):
    datos = {
        "nivel": "info", "mensaje": "prueba", "contexto": None, "url": "/login",
        "user_agent": "curl", "sesion_id": "test-1", "fecha": "2026-10-29T14:55:00.000Z",
    }
    datos.update(cambios)
    return datos


# ======================================================
# CASO DE USO
# ======================================================

def test_asigna_el_usuario_del_servidor_a_cada_log():
    repo = Mock()
    repo.guardar_lote.return_value = 2

    guardados = RegistrarLogsUseCase(repo).ejecutar([log(id_usuario=99), log()], 7)

    assert guardados == 2
    assert [l.id_usuario for l in repo.guardar_lote.call_args.args[0]] == [7, 7]


@pytest.mark.parametrize("cantidad", [0, 51])
def test_rechaza_lotes_vacios_o_demasiado_grandes(cantidad):
    repo = Mock()

    with pytest.raises(DatosInvalidosError):
        RegistrarLogsUseCase(repo).ejecutar([log()] * cantidad, None)

    repo.guardar_lote.assert_not_called()


# ======================================================
# PERSISTENCIA
# ======================================================

def test_insertar_logs_en_un_solo_commit():
    db = MagicMock()

    assert db_consultas.insertar_logs(db, [{"nivel": "info"}, {"nivel": "error"}]) == 2
    assert len(db.add_all.call_args.args[0]) == 2
    db.commit.assert_called_once()


def test_repositorio_mapea_y_cierra_la_sesion():
    db = MagicMock()

    with patch.object(repo_mod, "SessionLocal", return_value=db), \
         patch.object(repo_mod, "insertar_logs", return_value=1) as insertar:
        assert repo_mod.LogRepositoryMySQL().guardar_lote([log(id_usuario=7, contexto={"a": 1})]) == 1

    fila = insertar.call_args.args[1][0]
    assert fila["id_usuario"] == 7 and fila["contexto"] == {"a": 1}
    assert "id_log" not in fila
    db.close.assert_called_once()


def test_repositorio_hace_rollback_si_falla():
    db = MagicMock()

    with patch.object(repo_mod, "SessionLocal", return_value=db), \
         patch.object(repo_mod, "insertar_logs", side_effect=RuntimeError("BD")):
        with pytest.raises(RuntimeError):
            repo_mod.LogRepositoryMySQL().guardar_lote([log()])

    db.rollback.assert_called_once()
    db.close.assert_called_once()


# ======================================================
# ENDPOINT
# ======================================================

@pytest.fixture
def api():
    caso = Mock()
    tokens = Mock()
    tokens.decodificar.side_effect = lambda t: {"valido": "7", "raro": "abc"}.get(t)
    main.app.dependency_overrides[deps.get_registrar_logs_use_case] = lambda: caso
    main.app.dependency_overrides[deps.get_token_service] = lambda: tokens

    with patch.object(main, "guardar_log_tecnico"):
        cliente = TestClient(main.app)
        cliente.caso = caso
        yield cliente

    main.app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("cookie", "id_esperado"),
    [(None, None), ("valido", 7), ("vencido", None), ("raro", None)],
)
def test_acepta_logs_con_o_sin_sesion(api, cookie, id_esperado):
    if cookie:
        api.cookies.set("access_token", cookie)

    respuesta = api.post("/api/v1/logs", json={"logs": [log_json(contexto={"status": 500})]})

    assert respuesta.status_code == 204
    assert respuesta.content == b""
    logs, id_usuario = api.caso.ejecutar.call_args.args
    assert id_usuario == id_esperado
    assert logs[0].fecha == datetime(2026, 10, 29, 14, 55)
    assert logs[0].fecha.tzinfo is None
    assert logs[0].contexto == {"status": 500}


@pytest.mark.parametrize(
    "body",
    [
        {"logs": [log_json(nivel="fatal")]},
        {"logs": []},
        {"logs": [log_json()] * 51},
        {"logs": [log_json(mensaje="")]},
        {"logs": [log_json(sesion_id="x" * 51)]},
        {},
    ],
)
def test_datos_invalidos_responden_422(api, body):
    assert api.post("/api/v1/logs", json=body).status_code == 422
    api.caso.ejecutar.assert_not_called()


def test_fallo_de_bd_responde_500_con_formato_problem(api):
    api.caso.ejecutar.side_effect = RuntimeError("BD caída")

    respuesta = api.post("/api/v1/logs", json={"logs": [log_json()]})

    assert respuesta.status_code == 500
    assert respuesta.headers["content-type"] == "application/problem+json"
    assert respuesta.json()["detail"] == "Error al guardar los logs"


def test_convierte_fechas_con_zona_a_utc():
    from datetime import timedelta, timezone

    bogota = timezone(timedelta(hours=-5))

    assert _a_utc_sin_zona(datetime(2026, 10, 29, 9, 55, tzinfo=bogota)) == datetime(2026, 10, 29, 14, 55)
    assert _a_utc_sin_zona(datetime(2026, 10, 29, 14, 55)) == datetime(2026, 10, 29, 14, 55)


def test_dependencia_construye_el_caso_de_uso():
    assert isinstance(deps.get_registrar_logs_use_case(), RegistrarLogsUseCase)
