"""Pruebas del módulo de conversaciones: casos de uso, repositorio, REST y WebSocket."""
from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from starlette.websockets import WebSocketDisconnect

import main
from app.application.use_cases.conversacion_use_cases import (
    AbrirConversacionUseCase,
    EnviarMensajeUseCase,
    ListarConversacionesUseCase,
    ObtenerConversacionUseCase,
    VerificarParticipanteUseCase,
    reloj_local,
)
from app.config import dependencies as deps
from app.domain.entities.conversacion import Conversacion, Mensaje
from app.domain.exceptions import (
    AccesoDenegadoError,
    RecursoNoEncontradoError,
    SolicitudInvalidaError,
)
from app.application.use_cases.conversacion_use_cases import (
    ContarNoLeidosUseCase,
    MarcarLeidosUseCase,
)
from app.infraestructure.adaptadores.inbound.websocket import conversacion_ws, seguridad_ws
from app.infraestructure.adaptadores.inbound.websocket.connection_manager import (
    ConnectionManager,
    manager,
    notificaciones_manager,
)
from app.infraestructure.adaptadores.outbound.persistence import conversacion_repository_mysql
from app.infraestructure.adaptadores.outbound.persistence.conversacion_repository_mysql import (
    ConversacionRepositoryMySQL,
)
from tests.conftest import fila, resultado

AHORA = datetime(2026, 11, 4, 10, 30, 0)
CONVERSACION = Conversacion(
    id_conversacion=3, id_publicacion=8, id_interesado=7, id_vendedor=10,
    nombre_interesado="Ana", nombre_vendedor="Vendedor", titulo_publicacion="Lucero en venta",
)
MENSAJE = Mensaje(
    id_mensaje=1, id_conversacion=3, id_usuario=7, contenido="Hola",
    fecha_envio=AHORA, estado_lectura="no_leido",
)


# ======================================================
# ENTIDADES
# ======================================================

def test_participantes_de_la_conversacion():
    assert CONVERSACION.es_participante(7)
    assert CONVERSACION.es_participante(10)
    assert not CONVERSACION.es_participante(99)


def test_otro_participante_y_nombres():
    assert CONVERSACION.otro_participante(7) == 10
    assert CONVERSACION.otro_participante(10) == 7
    assert CONVERSACION.nombre_de(7) == "Ana"
    assert CONVERSACION.nombre_de(10) == "Vendedor"


def test_mensaje_a_dict():
    assert MENSAJE.a_dict() == {
        "id_mensaje": 1, "id_conversacion": 3, "id_usuario": 7, "contenido": "Hola",
        "fecha_envio": "2026-11-04T10:30:00", "estado_lectura": "no_leido",
    }


def test_reloj_local_devuelve_hora_sin_zona():
    ahora = reloj_local(-5)()
    assert ahora.tzinfo is None
    assert ahora.microsecond == 0


# ======================================================
# CASOS DE USO
# ======================================================

def test_abrir_conversacion_reutiliza_la_existente():
    repo, auditoria = Mock(), Mock()
    repo.buscar_id.return_value = 3

    assert AbrirConversacionUseCase(repo, auditoria, lambda: AHORA).ejecutar(7, 8) == 3
    repo.crear.assert_not_called()
    auditoria.registrar.assert_not_called()


def test_abrir_conversacion_crea_una_nueva():
    repo, auditoria = Mock(), Mock()
    repo.buscar_id.return_value = None
    repo.obtener_dueno_publicacion_activa.return_value = 10
    repo.crear.return_value = 4

    assert AbrirConversacionUseCase(repo, auditoria, lambda: AHORA).ejecutar(7, 8) == 4
    repo.crear.assert_called_once_with(8, 7, date(2026, 11, 4))
    assert auditoria.registrar.call_args.kwargs["accion"] == "ABRIR_CONVERSACION"


@pytest.mark.parametrize(
    ("dueno", "error"),
    [(None, RecursoNoEncontradoError), (7, SolicitudInvalidaError)],
)
def test_abrir_conversacion_rechaza_publicacion_inexistente_o_propia(dueno, error):
    repo = Mock()
    repo.buscar_id.return_value = None
    repo.obtener_dueno_publicacion_activa.return_value = dueno

    with pytest.raises(error):
        AbrirConversacionUseCase(repo, Mock(), lambda: AHORA).ejecutar(7, 8)
    repo.crear.assert_not_called()


def test_listar_conversaciones():
    repo = Mock()
    repo.listar_de_usuario.return_value = [{"id_conversacion": 3}]
    assert ListarConversacionesUseCase(repo).ejecutar(7) == [{"id_conversacion": 3}]


@pytest.mark.parametrize(
    ("conversacion", "usuario", "error"),
    [(None, 7, RecursoNoEncontradoError), (CONVERSACION, 99, AccesoDenegadoError)],
)
def test_verificar_participante_rechaza(conversacion, usuario, error):
    repo = Mock()
    repo.obtener.return_value = conversacion
    with pytest.raises(error):
        VerificarParticipanteUseCase(repo).ejecutar(usuario, 3)


def test_verificar_participante_acepta_a_ambos():
    repo = Mock()
    repo.obtener.return_value = CONVERSACION
    caso = VerificarParticipanteUseCase(repo)
    assert caso.ejecutar(7, 3) is CONVERSACION
    assert caso.ejecutar(10, 3) is CONVERSACION


def test_obtener_conversacion_devuelve_cabecera_e_historial():
    repo, verificador = Mock(), Mock()
    repo.obtener_resumen.return_value = {"id_conversacion": 3}
    repo.listar_mensajes.return_value = [MENSAJE]

    datos = ObtenerConversacionUseCase(repo, verificador).ejecutar(7, 3)

    verificador.ejecutar.assert_called_once_with(7, 3)
    assert datos == {"conversacion": {"id_conversacion": 3}, "mensajes": [MENSAJE.a_dict()]}


def test_obtener_conversacion_exige_participar():
    verificador = Mock()
    verificador.ejecutar.side_effect = AccesoDenegadoError()
    repo = Mock()
    with pytest.raises(AccesoDenegadoError):
        ObtenerConversacionUseCase(repo, verificador).ejecutar(99, 3)
    repo.listar_mensajes.assert_not_called()


def test_enviar_mensaje_guarda_el_texto_limpio():
    repo, verificador = Mock(), Mock()
    verificador.ejecutar.return_value = CONVERSACION
    repo.guardar_mensaje.return_value = MENSAJE

    assert EnviarMensajeUseCase(repo, verificador, lambda: AHORA).ejecutar(7, 3, "  Hola  ") is MENSAJE
    verificador.ejecutar.assert_called_once_with(7, 3)
    repo.guardar_mensaje.assert_called_once_with(3, 7, "Hola", AHORA)


def test_contar_no_leidos():
    repo = Mock()
    repo.contar_no_leidos.return_value = 4
    assert ContarNoLeidosUseCase(repo).ejecutar(7) == 4


def test_marcar_leidos_exige_participar():
    repo, verificador = Mock(), Mock()
    repo.marcar_leidos.return_value = 2
    assert MarcarLeidosUseCase(repo, verificador).ejecutar(7, 3) == 2
    verificador.ejecutar.assert_called_once_with(7, 3)
    repo.marcar_leidos.assert_called_once_with(3, 7)

    verificador.ejecutar.side_effect = AccesoDenegadoError()
    with pytest.raises(AccesoDenegadoError):
        MarcarLeidosUseCase(repo, verificador).ejecutar(99, 3)


@pytest.mark.parametrize("contenido", ["", "   ", None, "x" * 2001])
def test_enviar_mensaje_rechaza_contenido_invalido(contenido):
    repo, verificador = Mock(), Mock()
    with pytest.raises(SolicitudInvalidaError):
        EnviarMensajeUseCase(repo, verificador, lambda: AHORA).ejecutar(7, 3, contenido)
    repo.guardar_mensaje.assert_not_called()


# ======================================================
# REPOSITORIO MYSQL
# ======================================================

MODULO_REPO = conversacion_repository_mysql


def fila_resumen(**cambios):
    datos = dict(
        id_conversacion=3, publicacion_id_publicacion=8, fecha_creacion=date(2026, 11, 4),
        titulo="Lucero en venta", id_vendedor=10, nombre_vendedor="Vendedor",
        id_interesado=7, nombre_interesado="Ana", ultimo_mensaje="Hola",
        foto_vendedor="uploads/perfiles/vendedor.jpg", foto_interesado=None,
        fecha_ultimo_mensaje=AHORA, id_autor_ultimo=7, no_leidos=2,
        estado="activa", promedio_otro=4.5, total_otro=2,
    )
    datos.update(cambios)
    return fila(**datos)


@pytest.mark.parametrize(("encontrada", "esperado"), [(fila(usuario_id_usuario=10), 10), (None, None)])
def test_repo_dueno_publicacion(motor_falso, encontrada, esperado):
    motor_falso(MODULO_REPO, resultado(first=encontrada))
    assert ConversacionRepositoryMySQL().obtener_dueno_publicacion_activa(8) == esperado


@pytest.mark.parametrize(("encontrada", "esperado"), [(fila(id_conversacion=3), 3), (None, None)])
def test_repo_buscar_id(motor_falso, encontrada, esperado):
    motor_falso(MODULO_REPO, resultado(first=encontrada))
    assert ConversacionRepositoryMySQL().buscar_id(8, 7) == esperado


def test_repo_crear(motor_falso):
    conexion = motor_falso(MODULO_REPO, resultado(lastrowid=4))
    assert ConversacionRepositoryMySQL().crear(8, 7, date(2026, 11, 4)) == 4
    assert conexion.execute.call_args.args[1]["estado"] == "activa"


def test_repo_crear_ante_carrera_devuelve_la_existente(motor_falso):
    conflicto = IntegrityError("INSERT", {}, Exception("duplicado"))
    motor_falso(MODULO_REPO, conflicto, resultado(first=fila(id_conversacion=3)))
    assert ConversacionRepositoryMySQL().crear(8, 7, date(2026, 11, 4)) == 3


def test_repo_crear_relanza_si_no_era_carrera(motor_falso):
    conflicto = IntegrityError("INSERT", {}, Exception("fk"))
    motor_falso(MODULO_REPO, conflicto, resultado(first=None))
    with pytest.raises(IntegrityError):
        ConversacionRepositoryMySQL().crear(8, 7, date(2026, 11, 4))


def test_repo_obtener(motor_falso):
    motor_falso(MODULO_REPO, resultado(first=fila(
        id_conversacion=3, publicacion_id_publicacion=8, usuario_id_interesado=7, id_vendedor=10,
        titulo="Lucero en venta", nombre_interesado="Ana", nombre_vendedor="Vendedor",
        estado="activa",
    )), resultado(first=None))
    repo = ConversacionRepositoryMySQL()
    assert repo.obtener(3) == CONVERSACION
    assert repo.obtener(99) is None


def test_repo_resumen_visto_por_cada_participante(motor_falso):
    motor_falso(MODULO_REPO, resultado(first=fila_resumen()), resultado(first=fila_resumen()),
                resultado(first=None))
    repo = ConversacionRepositoryMySQL()

    interesado = repo.obtener_resumen(3, 7)
    assert interesado["otro_usuario"] == {
        "id": 10, "nombre": "Vendedor", "foto_perfil": "/uploads/perfiles/vendedor.jpg",
        "calificacion": {"promedio": 4.5, "total": 2},
    }
    assert interesado["estado"] == "activa"
    assert interesado["finalizada"] is False
    assert interesado["soy_vendedor"] is False
    assert interesado["ultimo_mensaje_es_mio"] is True
    assert interesado["fecha_ultimo_mensaje"] == "2026-11-04T10:30:00"
    assert interesado["no_leidos"] == 2

    vendedor = repo.obtener_resumen(3, 10)
    assert vendedor["otro_usuario"] == {
        "id": 7, "nombre": "Ana", "foto_perfil": None,
        "calificacion": {"promedio": 4.5, "total": 2},
    }
    assert vendedor["soy_vendedor"] is True

    assert repo.obtener_resumen(99, 7) is None


def test_repo_listar_de_usuario_sin_mensajes(motor_falso):
    motor_falso(MODULO_REPO, resultado(filas=[
        fila_resumen(ultimo_mensaje=None, fecha_ultimo_mensaje=None, id_autor_ultimo=None,
                     no_leidos=None),
    ]))
    [conversacion] = ConversacionRepositoryMySQL().listar_de_usuario(7)
    assert conversacion["ultimo_mensaje"] is None
    assert conversacion["fecha_ultimo_mensaje"] is None
    assert conversacion["ultimo_mensaje_es_mio"] is False
    assert conversacion["no_leidos"] == 0


@pytest.mark.parametrize(("total", "esperado"), [(5, 5), (None, 0)])
def test_repo_contar_no_leidos(motor_falso, total, esperado):
    conexion = motor_falso(MODULO_REPO, resultado(scalar=total))
    assert ConversacionRepositoryMySQL().contar_no_leidos(7) == esperado
    assert conexion.execute.call_args.args[1] == {"id_usuario": 7, "no_leido": "no_leido"}


def test_repo_marcar_leidos(motor_falso):
    conexion = motor_falso(MODULO_REPO, resultado(rowcount=2))
    assert ConversacionRepositoryMySQL().marcar_leidos(3, 7) == 2
    assert conexion.execute.call_args.args[1] == {
        "leido": "leido", "no_leido": "no_leido", "id_conversacion": 3, "id_usuario": 7,
    }


def test_repo_listar_mensajes_en_orden_cronologico(motor_falso):
    def fila_mensaje(id_mensaje):
        return fila(id_mensaje=id_mensaje, conversacion_id_conversacion=3, usuario_id_usuario=7,
                    contenido=f"m{id_mensaje}", fecha_envio=AHORA, estado_lectura="no_leido")

    conexion = motor_falso(MODULO_REPO, resultado(filas=[fila_mensaje(2), fila_mensaje(1)]))
    mensajes = ConversacionRepositoryMySQL().listar_mensajes(3, 200)
    assert [m.id_mensaje for m in mensajes] == [1, 2]
    assert conexion.execute.call_args.args[1] == {"id_conversacion": 3, "limite": 200}


def test_repo_guardar_mensaje(motor_falso):
    motor_falso(MODULO_REPO, resultado(lastrowid=1))
    assert ConversacionRepositoryMySQL().guardar_mensaje(3, 7, "Hola", AHORA) == MENSAJE


# ======================================================
# API REST
# ======================================================

@pytest.fixture
def tokens():
    servicio = Mock()
    servicio.decodificar.side_effect = lambda t: {"valido": "7", "raro": "abc"}.get(t)
    return servicio


@pytest.fixture
def api(tokens):
    main.app.dependency_overrides[deps.get_token_service] = lambda: tokens

    with patch.object(main, "guardar_log_tecnico"):
        cliente = TestClient(main.app)

        def usar(proveedor, caso=None):
            caso = caso or Mock()
            main.app.dependency_overrides[proveedor] = lambda: caso
            return caso

        cliente.usar = usar
        cliente.cookies.set("access_token", "valido")
        yield cliente

    main.app.dependency_overrides.clear()


def test_rest_abrir_conversacion(api):
    caso = api.usar(deps.get_abrir_conversacion_use_case)
    caso.ejecutar.return_value = 3

    respuesta = api.post("/api/v1/conversaciones", json={"id_publicacion": 8})

    assert respuesta.status_code == 200
    assert respuesta.json() == {"id_conversacion": 3}
    caso.ejecutar.assert_called_once_with(7, 8)


def test_rest_abrir_conversacion_valida_el_cuerpo(api):
    api.usar(deps.get_abrir_conversacion_use_case)
    assert api.post("/api/v1/conversaciones", json={"id_publicacion": 0}).status_code == 422


def test_rest_abrir_conversacion_propia(api):
    caso = api.usar(deps.get_abrir_conversacion_use_case)
    caso.ejecutar.side_effect = SolicitudInvalidaError("propia")
    assert api.post("/api/v1/conversaciones", json={"id_publicacion": 8}).status_code == 400


def test_rest_listar_conversaciones(api):
    caso = api.usar(deps.get_listar_conversaciones_use_case)
    caso.ejecutar.return_value = [{"id_conversacion": 3}]

    respuesta = api.get("/api/v1/conversaciones")

    assert respuesta.json() == [{"id_conversacion": 3}]
    caso.ejecutar.assert_called_once_with(7)


@pytest.mark.parametrize(
    ("error", "estado"),
    [(None, 200), (AccesoDenegadoError(), 403), (RecursoNoEncontradoError(), 404)],
)
def test_rest_obtener_mensajes(api, error, estado):
    caso = api.usar(deps.get_obtener_conversacion_use_case)
    caso.ejecutar.return_value = {"conversacion": {}, "mensajes": []}
    caso.ejecutar.side_effect = error

    assert api.get("/api/v1/conversaciones/3/mensajes").status_code == estado


def test_rest_contar_no_leidos(api):
    caso = api.usar(deps.get_contar_no_leidos_use_case)
    caso.ejecutar.return_value = 4
    assert api.get("/api/v1/conversaciones/no-leidos").json() == {"total": 4}
    caso.ejecutar.assert_called_once_with(7)


@pytest.mark.parametrize(("error", "estado"), [(None, 200), (AccesoDenegadoError(), 403)])
def test_rest_marcar_leidos(api, error, estado):
    caso = api.usar(deps.get_marcar_leidos_use_case)
    caso.ejecutar.return_value = 2
    caso.ejecutar.side_effect = error

    respuesta = api.post("/api/v1/conversaciones/3/leer")

    assert respuesta.status_code == estado
    if estado == 200:
        assert respuesta.json() == {"marcados": 2}
        caso.ejecutar.assert_called_once_with(7, 3)


def test_rest_exige_sesion(api):
    api.cookies.clear()
    assert api.get("/api/v1/conversaciones").status_code == 401


# ======================================================
# WEBSOCKET
# ======================================================

RUTA_WS = "/ws/conversaciones/3"


@pytest.fixture
def ws(api):
    """Cliente con verificador y envío simulados; `ws.conectar()` abre el WebSocket."""
    verificador = api.usar(deps.get_verificar_participante_use_case)
    verificador.ejecutar.return_value = CONVERSACION
    enviar = api.usar(deps.get_enviar_mensaje_use_case)
    enviar.ejecutar.return_value = MENSAJE

    def conectar(cookie="valido", origen=None):
        cabeceras = {"origin": origen} if origen else {}
        api.cookies.clear()
        if cookie:
            api.cookies.set("access_token", cookie)
        return api.websocket_connect(RUTA_WS, headers=cabeceras)

    api.conectar = conectar
    api.verificador = verificador
    api.enviar = enviar
    return api


def codigo_de_cierre(conexion):
    with pytest.raises(WebSocketDisconnect) as info:
        with conexion as socket:
            socket.receive_json()
    return info.value.code


def test_ws_envia_y_recibe_el_mensaje_guardado(ws):
    with ws.conectar(origen="http://localhost:4200") as socket:
        socket.send_json({"tipo": "mensaje", "contenido": "Hola"})
        assert socket.receive_json() == {"tipo": "mensaje", "mensaje": MENSAJE.a_dict()}

    ws.verificador.ejecutar.assert_called_once_with(7, 3)
    ws.enviar.ejecutar.assert_called_once_with(7, 3, "Hola")


@pytest.mark.parametrize("cookie", [None, "vencido", "raro"])
def test_ws_sin_sesion_cierra_4401(ws, cookie):
    assert codigo_de_cierre(ws.conectar(cookie=cookie)) == 4401
    ws.verificador.ejecutar.assert_not_called()


@pytest.mark.parametrize(
    ("error", "codigo"),
    [(AccesoDenegadoError(), 4403), (RecursoNoEncontradoError(), 4404), (RuntimeError("bd"), 1011)],
)
def test_ws_rechaza_a_quien_no_participa(ws, error, codigo):
    ws.verificador.ejecutar.side_effect = error
    assert codigo_de_cierre(ws.conectar()) == codigo


def test_ws_rechaza_origen_no_permitido(ws):
    assert codigo_de_cierre(ws.conectar(origen="http://malicioso.com")) == 1008


@pytest.mark.parametrize(
    ("enviado", "detalle"),
    [
        ("no es json", "Formato inválido"),
        ('["lista"]', "Tipo de mensaje no soportado"),
        ('{"tipo": "otro"}', "Tipo de mensaje no soportado"),
        ('{"tipo": "mensaje", "contenido": 5}', "El mensaje debe ser texto"),
    ],
)
def test_ws_responde_error_ante_datos_invalidos(ws, enviado, detalle):
    with ws.conectar() as socket:
        socket.send_text(enviado)
        assert socket.receive_json() == {"tipo": "error", "detalle": detalle}
    ws.enviar.ejecutar.assert_not_called()


@pytest.mark.parametrize(
    ("error", "detalle"),
    [(SolicitudInvalidaError("El mensaje no puede estar vacío"), "El mensaje no puede estar vacío"),
     (RuntimeError("bd caída"), "No se pudo enviar el mensaje")],
)
def test_ws_informa_si_no_se_pudo_guardar(ws, error, detalle):
    ws.enviar.ejecutar.side_effect = error
    with ws.conectar() as socket:
        socket.send_json({"tipo": "mensaje", "contenido": "Hola"})
        assert socket.receive_json() == {"tipo": "error", "detalle": detalle}


def test_ws_cierra_si_deja_de_participar(ws):
    ws.enviar.ejecutar.side_effect = AccesoDenegadoError()
    with pytest.raises(WebSocketDisconnect) as info:
        with ws.conectar() as socket:
            socket.send_json({"tipo": "mensaje", "contenido": "Hola"})
            socket.receive_json()
    assert info.value.code == 4403


def test_ws_cierra_si_la_sesion_caduca(ws, tokens):
    with pytest.raises(WebSocketDisconnect) as info:
        with ws.conectar() as socket:
            tokens.decodificar.side_effect = lambda t: None
            socket.send_json({"tipo": "mensaje", "contenido": "Hola"})
            socket.receive_json()
    assert info.value.code == 4401
    ws.enviar.ejecutar.assert_not_called()


def test_ws_libera_la_conexion_al_desconectar(ws):
    with ws.conectar() as socket:
        socket.send_json({"tipo": "mensaje", "contenido": "Hola"})
        socket.receive_json()
        assert conversacion_ws.manager.cantidad(3) == 1
    assert conversacion_ws.manager.cantidad(3) == 0


@pytest.mark.parametrize(
    ("variable", "esperado"),
    [("", {"http://localhost:4200", "http://127.0.0.1:4200"}),
     ("http://localhost, http://x.com ,", {"http://localhost", "http://x.com"})],
)
def test_ws_origenes_permitidos(monkeypatch, variable, esperado):
    monkeypatch.setenv("ALLOWED_ORIGINS", variable)
    assert seguridad_ws.origenes_permitidos() == esperado


# ======================================================
# WEBSOCKET DE AVISOS
# ======================================================

RUTA_AVISOS = "/ws/notificaciones"


def test_avisos_llegan_al_otro_participante(ws, tokens):
    tokens.decodificar.side_effect = lambda t: {"valido": "7", "vendedor": "10"}.get(t)
    # Una sola instancia de TestClient en contexto: ambos sockets comparten el mismo bucle
    with ws:
        ws.cookies.set("access_token", "vendedor")
        with ws.websocket_connect(RUTA_AVISOS) as avisos_vendedor:
            ws.cookies.set("access_token", "valido")
            with ws.websocket_connect(RUTA_WS) as chat_interesado:
                chat_interesado.send_json({"tipo": "mensaje", "contenido": "Hola"})
                assert chat_interesado.receive_json()["tipo"] == "mensaje"

            assert avisos_vendedor.receive_json() == {
                "tipo": "nuevo_mensaje",
                "mensaje": MENSAJE.a_dict(),
                "remitente": "Ana",
                "titulo_publicacion": "Lucero en venta",
            }
            assert notificaciones_manager.cantidad(10) == 1
            avisos_vendedor.send_text("ignorado")  # lo que mande el cliente no rompe nada
    assert notificaciones_manager.cantidad(10) == 0
    assert manager.cantidad(3) == 0


@pytest.mark.parametrize("cookie", [None, "vencido"])
def test_avisos_sin_sesion_cierra_4401(api, cookie):
    api.cookies.clear()
    if cookie:
        api.cookies.set("access_token", cookie)
    assert codigo_de_cierre(api.websocket_connect(RUTA_AVISOS)) == 4401


def test_avisos_rechaza_origen_no_permitido(api):
    conexion = api.websocket_connect(RUTA_AVISOS, headers={"origin": "http://malicioso.com"})
    assert codigo_de_cierre(conexion) == 1008


# ======================================================
# CONNECTION MANAGER
# ======================================================

@pytest.mark.anyio
async def test_manager_difunde_a_todos_los_participantes():
    manager = ConnectionManager()
    interesado, vendedor, otra = AsyncMock(), AsyncMock(), AsyncMock()
    await manager.conectar(3, interesado)
    await manager.conectar(3, vendedor)
    await manager.conectar(4, otra)

    await manager.difundir(3, {"tipo": "mensaje"})

    interesado.send_json.assert_awaited_once_with({"tipo": "mensaje"})
    vendedor.send_json.assert_awaited_once_with({"tipo": "mensaje"})
    otra.send_json.assert_not_awaited()


@pytest.mark.anyio
async def test_manager_descarta_conexiones_caidas():
    manager = ConnectionManager()
    viva, caida = AsyncMock(), AsyncMock()
    caida.send_json.side_effect = RuntimeError("cerrada")
    await manager.conectar(3, viva)
    await manager.conectar(3, caida)

    await manager.difundir(3, {"tipo": "mensaje"})

    assert manager.cantidad(3) == 1
    viva.send_json.assert_awaited_once()


@pytest.mark.anyio
async def test_manager_desconectar():
    manager = ConnectionManager()
    socket = AsyncMock()
    await manager.conectar(3, socket)
    await manager.desconectar(3, socket)
    await manager.desconectar(3, socket)  # repetir no falla
    await manager.desconectar(9, socket)  # conversación sin conexiones tampoco
    assert manager.cantidad(3) == 0
    await manager.difundir(3, {"tipo": "mensaje"})  # sin destinatarios no hace nada
