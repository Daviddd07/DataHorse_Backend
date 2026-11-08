"""Pruebas de reseñas al finalizar un chat y del estado en línea / última conexión."""
from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

import main
from app.application.use_cases.conversacion_use_cases import (
    AbrirConversacionUseCase,
    EnviarMensajeUseCase,
    FinalizarConversacionUseCase,
    ListarConversacionesUseCase,
    ObtenerConversacionUseCase,
)
from app.application.use_cases.resena_use_cases import (
    CalificarUsuarioUseCase,
    ObtenerCalificacionUseCase,
    ObtenerEstadoConexionUseCase,
    RegistrarConexionUseCase,
)
from app.config import dependencies as deps
from app.domain.entities.conversacion import Conversacion
from app.domain.entities.resena import EstadoConexion, Resena, ResumenCalificacion
from app.domain.exceptions import ConflictoError, SolicitudInvalidaError
from app.infraestructure.adaptadores.inbound.rest import conversacion_controller
from app.infraestructure.adaptadores.inbound.websocket.connection_manager import (
    ConnectionManager,
    notificaciones_manager,
)
from app.infraestructure.adaptadores.inbound.websocket.presencia import EnLineaPorWebSocket
from app.infraestructure.adaptadores.outbound.persistence import (
    conversacion_repository_mysql,
    resena_repository_mysql,
    ultima_conexion_repository_mysql,
)
from app.infraestructure.adaptadores.outbound.persistence.conversacion_repository_mysql import (
    ConversacionRepositoryMySQL,
)
from app.infraestructure.adaptadores.outbound.persistence.resena_repository_mysql import (
    ResenaRepositoryMySQL,
)
from app.infraestructure.adaptadores.outbound.persistence.ultima_conexion_repository_mysql import (
    UltimaConexionRepositoryMySQL,
)
from tests.conftest import fila, resultado

AHORA = datetime(2026, 11, 8, 15, 30, 0)
ACTIVA = Conversacion(
    id_conversacion=3, id_publicacion=8, id_interesado=7, id_vendedor=10,
    nombre_interesado="Ana", nombre_vendedor="Vendedor", titulo_publicacion="Lucero",
)
FINALIZADA = Conversacion(
    id_conversacion=3, id_publicacion=8, id_interesado=7, id_vendedor=10,
    nombre_interesado="Ana", nombre_vendedor="Vendedor", titulo_publicacion="Lucero",
    estado="finalizada",
)
RESENA = Resena(
    id_resena=1, id_conversacion=3, id_evaluador=7, id_evaluado=10,
    calificacion=5, comentario="Muy serio", fecha=date(2026, 11, 8),
)


# ======================================================
# ENTIDADES
# ======================================================

def test_conversacion_finalizada():
    assert not ACTIVA.esta_finalizada()
    assert FINALIZADA.esta_finalizada()


def test_resena_a_dict():
    assert RESENA.a_dict() == {
        "id_resena": 1, "id_conversacion": 3, "id_evaluador": 7, "id_evaluado": 10,
        "calificacion": 5, "comentario": "Muy serio", "fecha": "2026-11-08",
    }


@pytest.mark.parametrize(
    ("promedio", "total", "esperado"),
    [(4.333, 3, {"promedio": 4.3, "total": 3}), (None, 0, {"promedio": None, "total": 0}),
     (5, None, {"promedio": None, "total": 0})],
)
def test_resumen_calificacion(promedio, total, esperado):
    assert ResumenCalificacion.desde(promedio, total).a_dict() == esperado


def test_estado_conexion_a_dict():
    assert EstadoConexion(True, AHORA).a_dict() == {
        "en_linea": True, "ultima_conexion": "2026-11-08T15:30:00",
    }
    assert EstadoConexion(False, None).a_dict() == {"en_linea": False, "ultima_conexion": None}


# ======================================================
# CASOS DE USO: CONVERSACIÓN
# ======================================================

def test_abrir_conversacion_existente_la_reabre():
    repo = Mock()
    repo.buscar_id.return_value = 3
    assert AbrirConversacionUseCase(repo, Mock(), lambda: AHORA).ejecutar(7, 8) == 3
    repo.cambiar_estado.assert_called_once_with(3, "activa")


def test_finalizar_conversacion():
    repo, verificador, auditoria = Mock(), Mock(), Mock()
    verificador.ejecutar.return_value = ACTIVA
    repo.cambiar_estado.return_value = True

    assert FinalizarConversacionUseCase(repo, verificador, auditoria).ejecutar(7, 3) is ACTIVA
    repo.cambiar_estado.assert_called_once_with(3, "finalizada")
    assert auditoria.registrar.call_args.kwargs["accion"] == "FINALIZAR_CONVERSACION"


def test_finalizar_dos_veces_no_audita_de_nuevo():
    repo, verificador, auditoria = Mock(), Mock(), Mock()
    verificador.ejecutar.return_value = FINALIZADA
    repo.cambiar_estado.return_value = False
    FinalizarConversacionUseCase(repo, verificador, auditoria).ejecutar(7, 3)
    auditoria.registrar.assert_not_called()


def test_no_se_puede_escribir_en_un_chat_finalizado():
    repo, verificador = Mock(), Mock()
    verificador.ejecutar.return_value = FINALIZADA
    with pytest.raises(ConflictoError):
        EnviarMensajeUseCase(repo, verificador, lambda: AHORA).ejecutar(7, 3, "Hola")
    repo.guardar_mensaje.assert_not_called()


def test_listar_agrega_el_estado_de_conexion():
    repo, estado = Mock(), Mock()
    repo.listar_de_usuario.return_value = [{"otro_usuario": {"id": 10}}, {"otro_usuario": {"id": 11}}]
    estado.ejecutar.return_value = {10: EstadoConexion(True, AHORA)}

    lista = ListarConversacionesUseCase(repo, estado).ejecutar(7)

    estado.ejecutar.assert_called_once_with([10, 11])
    assert lista[0]["otro_usuario"]["conexion"] == {"en_linea": True, "ultima_conexion": "2026-11-08T15:30:00"}
    assert lista[1]["otro_usuario"]["conexion"] is None


def test_listar_sin_conversaciones_no_consulta_conexion():
    repo, estado = Mock(), Mock()
    repo.listar_de_usuario.return_value = []
    assert ListarConversacionesUseCase(repo, estado).ejecutar(7) == []
    estado.ejecutar.assert_not_called()


def test_obtener_conversacion_indica_si_ya_califique_y_la_conexion():
    repo, verificador, resenas, estado = Mock(), Mock(), Mock(), Mock()
    repo.obtener_resumen.return_value = {"otro_usuario": {"id": 10}}
    repo.listar_mensajes.return_value = []
    resenas.existe.return_value = True
    estado.ejecutar.return_value = {10: EstadoConexion(False, AHORA)}

    datos = ObtenerConversacionUseCase(repo, verificador, resenas, estado).ejecutar(7, 3)

    assert datos["conversacion"]["ya_califique"] is True
    assert datos["conversacion"]["otro_usuario"]["conexion"]["en_linea"] is False
    resenas.existe.assert_called_once_with(3, 7)


def test_obtener_conversacion_sin_resumen():
    repo, resenas = Mock(), Mock()
    repo.obtener_resumen.return_value = None
    repo.listar_mensajes.return_value = []
    assert ObtenerConversacionUseCase(repo, Mock(), resenas, Mock()).ejecutar(7, 3)["conversacion"] is None
    resenas.existe.assert_not_called()


# ======================================================
# CASOS DE USO: RESEÑAS Y PRESENCIA
# ======================================================

@pytest.fixture
def calificar():
    verificador, repo, auditoria = Mock(), Mock(), Mock()
    verificador.ejecutar.return_value = FINALIZADA
    repo.existe.return_value = False
    repo.crear.return_value = RESENA
    caso = CalificarUsuarioUseCase(verificador, repo, auditoria, lambda: AHORA)
    caso.repo, caso.verificador, caso.auditoria = repo, verificador, auditoria
    return caso


def test_calificar_al_otro_participante(calificar):
    assert calificar.ejecutar(7, 3, 5, "  Muy serio  ") is RESENA
    calificar.repo.crear.assert_called_once_with(3, 7, 10, 5, "Muy serio", date(2026, 11, 8))
    assert calificar.auditoria.registrar.call_args.kwargs["accion"] == "CALIFICAR_USUARIO"


def test_el_vendedor_califica_al_interesado(calificar):
    calificar.ejecutar(10, 3, 4, None)
    calificar.repo.crear.assert_called_once_with(3, 10, 7, 4, None, date(2026, 11, 8))


def test_comentario_vacio_se_guarda_como_nulo(calificar):
    calificar.ejecutar(7, 3, 3, "   ")
    assert calificar.repo.crear.call_args.args[4] is None


@pytest.mark.parametrize("estrellas", [0, 6, -1, 4.5, "5", True, None])
def test_calificacion_fuera_de_rango(calificar, estrellas):
    with pytest.raises(SolicitudInvalidaError):
        calificar.ejecutar(7, 3, estrellas, None)
    calificar.repo.crear.assert_not_called()


def test_comentario_demasiado_largo(calificar):
    with pytest.raises(SolicitudInvalidaError):
        calificar.ejecutar(7, 3, 5, "x" * 1001)


def test_solo_se_califica_un_chat_finalizado(calificar):
    calificar.verificador.ejecutar.return_value = ACTIVA
    with pytest.raises(SolicitudInvalidaError):
        calificar.ejecutar(7, 3, 5, None)


def test_no_se_califica_dos_veces(calificar):
    calificar.repo.existe.return_value = True
    with pytest.raises(ConflictoError):
        calificar.ejecutar(7, 3, 5, None)
    calificar.repo.crear.assert_not_called()


def test_obtener_calificacion():
    repo = Mock()
    repo.resumen_de.return_value = ResumenCalificacion(4.5, 2)
    assert ObtenerCalificacionUseCase(repo).ejecutar(10) == ResumenCalificacion(4.5, 2)


def test_estado_conexion_de_varios_usuarios():
    en_linea, ultimas = Mock(), Mock()
    en_linea.esta_en_linea.side_effect = lambda u: u == 10
    ultimas.obtener.return_value = {10: AHORA, 11: None}

    estados = ObtenerEstadoConexionUseCase(en_linea, ultimas).ejecutar([10, 11, 10])

    ultimas.obtener.assert_called_once_with([10, 11])
    assert estados == {10: EstadoConexion(True, AHORA), 11: EstadoConexion(False, None)}


def test_estado_conexion_sin_usuarios():
    ultimas = Mock()
    assert ObtenerEstadoConexionUseCase(Mock(), ultimas).ejecutar([]) == {}
    ultimas.obtener.assert_not_called()


def test_registrar_conexion():
    ultimas = Mock()
    RegistrarConexionUseCase(ultimas, lambda: AHORA).ejecutar(7)
    ultimas.registrar.assert_called_once_with(7, AHORA)


# ======================================================
# REPOSITORIOS MYSQL
# ======================================================

@pytest.mark.parametrize(("filas", "esperado"), [(1, True), (0, False)])
def test_repo_cambiar_estado(motor_falso, filas, esperado):
    conexion = motor_falso(conversacion_repository_mysql, resultado(rowcount=filas))
    assert ConversacionRepositoryMySQL().cambiar_estado(3, "finalizada") is esperado
    assert conexion.execute.call_args.args[1] == {"estado": "finalizada", "id_conversacion": 3}


def test_repo_contactos(motor_falso):
    motor_falso(conversacion_repository_mysql, resultado(filas=[fila(id_contacto=10), fila(id_contacto=11)]))
    assert ConversacionRepositoryMySQL().contactos_de(7) == [10, 11]


@pytest.mark.parametrize(("encontrada", "esperado"), [(fila(id_resena=1), True), (None, False)])
def test_repo_resena_existe(motor_falso, encontrada, esperado):
    motor_falso(resena_repository_mysql, resultado(first=encontrada))
    assert ResenaRepositoryMySQL().existe(3, 7) is esperado


def test_repo_resena_crear(motor_falso):
    conexion = motor_falso(resena_repository_mysql, resultado(lastrowid=1))
    assert ResenaRepositoryMySQL().crear(3, 7, 10, 5, "Muy serio", date(2026, 11, 8)) == RESENA
    assert conexion.execute.call_args.args[1]["id_conversacion"] == 3


def test_repo_resena_duplicada_es_conflicto(motor_falso):
    motor_falso(resena_repository_mysql, IntegrityError("INSERT", {}, Exception("duplicado")))
    with pytest.raises(ConflictoError):
        ResenaRepositoryMySQL().crear(3, 7, 10, 5, None, date(2026, 11, 8))


def test_repo_resumen(motor_falso):
    motor_falso(resena_repository_mysql, resultado(first=fila(promedio=4.666, total=3)))
    assert ResenaRepositoryMySQL().resumen_de(10) == ResumenCalificacion(4.7, 3)


def test_repo_ultima_conexion(motor_falso):
    conexion = motor_falso(
        ultima_conexion_repository_mysql,
        resultado(),
        resultado(filas=[fila(id_usuario=10, ultima_conexion=AHORA), fila(id_usuario=11, ultima_conexion=None)]),
    )
    repo = UltimaConexionRepositoryMySQL()
    repo.registrar(7, AHORA)
    assert conexion.execute.call_args.args[1] == {"momento": AHORA, "id_usuario": 7}
    assert repo.obtener([10, 11]) == {10: AHORA, 11: None}
    assert repo.obtener([]) == {}


@pytest.mark.anyio
async def test_en_linea_por_websocket():
    manager = ConnectionManager()
    adaptador = EnLineaPorWebSocket(manager)
    assert adaptador.esta_en_linea(7) is False
    await manager.conectar(7, AsyncMock())
    assert adaptador.esta_en_linea(7) is True


# ======================================================
# API REST
# ======================================================

@pytest.fixture
def api():
    tokens = Mock()
    tokens.decodificar.side_effect = lambda t: {"valido": "7", "vendedor": "10"}.get(t)
    main.app.dependency_overrides[deps.get_token_service] = lambda: tokens

    with patch.object(main, "guardar_log_tecnico"):
        cliente = TestClient(main.app)

        def usar(proveedor, caso=None):
            caso = caso or Mock()
            main.app.dependency_overrides[proveedor] = lambda: caso
            return caso

        cliente.usar = usar
        cliente.tokens = tokens
        cliente.cookies.set("access_token", "valido")
        yield cliente

    main.app.dependency_overrides.clear()


def test_rest_finalizar_avisa_a_los_dos(api):
    caso = api.usar(deps.get_finalizar_conversacion_use_case)
    caso.ejecutar.return_value = ACTIVA
    with patch.object(conversacion_controller, "manager") as chat, \
         patch.object(conversacion_controller, "notificaciones_manager") as avisos:
        chat.difundir = AsyncMock()
        avisos.difundir = AsyncMock()
        respuesta = api.post("/api/v1/conversaciones/3/finalizar")

    assert respuesta.json() == {"id_conversacion": 3, "estado": "finalizada"}
    chat.difundir.assert_awaited_once_with(3, {"tipo": "finalizada", "por": 7})
    avisos.difundir.assert_awaited_once_with(
        10, {"tipo": "conversacion_finalizada", "id_conversacion": 3, "por": "Ana"}
    )


def test_rest_calificar(api):
    caso = api.usar(deps.get_calificar_usuario_use_case)
    caso.ejecutar.return_value = RESENA
    resumen = api.usar(deps.get_obtener_calificacion_use_case)
    resumen.ejecutar.return_value = ResumenCalificacion(5.0, 1)

    respuesta = api.post("/api/v1/conversaciones/3/resena", json={"calificacion": 5, "comentario": "Muy serio"})

    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "resena": RESENA.a_dict(), "calificacion_evaluado": {"promedio": 5.0, "total": 1},
    }
    caso.ejecutar.assert_called_once_with(7, 3, 5, "Muy serio")
    resumen.ejecutar.assert_called_once_with(10)


@pytest.mark.parametrize("cuerpo", [{"calificacion": 0}, {"calificacion": 6}, {}, {"calificacion": 5, "comentario": "x" * 1001}])
def test_rest_calificar_valida_el_cuerpo(api, cuerpo):
    api.usar(deps.get_calificar_usuario_use_case)
    assert api.post("/api/v1/conversaciones/3/resena", json=cuerpo).status_code == 422


def test_rest_calificar_dos_veces_es_409(api):
    caso = api.usar(deps.get_calificar_usuario_use_case)
    caso.ejecutar.side_effect = ConflictoError("Ya calificaste")
    api.usar(deps.get_obtener_calificacion_use_case)
    assert api.post("/api/v1/conversaciones/3/resena", json={"calificacion": 4}).status_code == 409


def test_rest_calificacion_de_un_usuario(api):
    caso = api.usar(deps.get_obtener_calificacion_use_case)
    caso.ejecutar.return_value = ResumenCalificacion(4.5, 2)
    assert api.get("/api/v1/usuarios/10/calificacion").json() == {"promedio": 4.5, "total": 2}
    caso.ejecutar.assert_called_once_with(10)


def test_rest_calificacion_exige_sesion(api):
    api.cookies.clear()
    assert api.get("/api/v1/usuarios/10/calificacion").status_code == 401


# ======================================================
# WEBSOCKET DE AVISOS: PRESENCIA
# ======================================================

def test_presencia_se_anuncia_al_conectar_y_al_desconectar(api):
    registrar = api.usar(deps.get_registrar_conexion_use_case)
    estado = api.usar(deps.get_estado_conexion_use_case)
    main.app.dependency_overrides[deps.get_buscar_contactos] = lambda: (lambda u: {7: [10], 10: [7]}[u])
    estado.ejecutar.side_effect = lambda ids: {
        i: EstadoConexion(notificaciones_manager.cantidad(i) > 0, AHORA) for i in ids
    }

    with api:
        api.cookies.set("access_token", "vendedor")
        with api.websocket_connect("/ws/notificaciones") as avisos_vendedor:
            api.cookies.set("access_token", "valido")
            with api.websocket_connect("/ws/notificaciones") as avisos_interesado:
                assert avisos_vendedor.receive_json() == {
                    "tipo": "presencia", "id_usuario": 7, "en_linea": True,
                    "ultima_conexion": "2026-11-08T15:30:00",
                }
                # Se cierra desde el cliente (como el navegador al salir) y el servidor avisa
                avisos_interesado.close()
                assert avisos_vendedor.receive_json() == {
                    "tipo": "presencia", "id_usuario": 7, "en_linea": False,
                    "ultima_conexion": "2026-11-08T15:30:00",
                }
            avisos_vendedor.close()

    # Conexión y desconexión del interesado (7) y del vendedor (10)
    assert sorted(c.args[0] for c in registrar.ejecutar.call_args_list) == [7, 7, 10, 10]


def test_presencia_tolera_fallos_de_la_bd(api):
    registrar = api.usar(deps.get_registrar_conexion_use_case)
    registrar.ejecutar.side_effect = RuntimeError("bd caída")
    api.usar(deps.get_estado_conexion_use_case)
    main.app.dependency_overrides[deps.get_buscar_contactos] = lambda: (lambda u: [])

    with api.websocket_connect("/ws/notificaciones") as socket:
        socket.send_text("ping")
    assert notificaciones_manager.cantidad(7) == 0
