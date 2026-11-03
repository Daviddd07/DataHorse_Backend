"""Pruebas de la evaluación de compatibilidad. Ninguna llama a Groq de verdad."""
import json
from dataclasses import replace
from datetime import date, datetime, timezone
from unittest.mock import Mock

import httpx
import pytest
from conftest import fila, resultado

from app.application.use_cases.compatibilidad_use_cases import (
    AVISO,
    ConsultarCupoCompatibilidadUseCase,
    EvaluarCompatibilidadUseCase,
    ListarResultadosCompatibilidadUseCase,
    ObtenerResultadoCompatibilidadUseCase,
)
from app.domain.entities.compatibilidad import (
    DatosEvaluacion,
    EjemplarEvaluado,
    EvaluacionGuardada,
    ResultadoCompatibilidad,
)
from app.domain.entities.descendencia import Descendencia
from app.domain.exceptions import (
    ConfiguracionError,
    DemasiadosIntentosError,
    RecursoNoEncontradoError,
    ServicioExternoError,
    SolicitudInvalidaError,
)
from app.domain.services.datos_compatibilidad import (
    construir_datos,
    describir_edad,
    distancia_km,
    edad_en_meses,
    resultado_es_valido,
)
from app.infraestructure.adaptadores.outbound.ia import groq_evaluador as groq
from app.infraestructure.adaptadores.outbound.persistence import (
    compatibilidad_repository_mysql as repo_mysql,
)

HOY = date(2026, 11, 2)


def ejemplar(**cambios) -> EjemplarEvaluado:
    datos = dict(
        id_caballo=10, id_raza=3, id_propietario=2, nombre="Juan", sexo="Macho", raza="Criollo",
        fecha_nacimiento=date(2022, 1, 6), altura=1.5, color="Castaño", descripcion="Noble",
        disponibilidad="Disponible", propietario="David", publicado=True,
        ciudad="Medellín", departamento="Antioquia", ubicacion_lat=6.25, ubicacion_lng=-75.56,
    )
    datos.update(cambios)
    return EjemplarEvaluado(**datos)


CABALLO = ejemplar()
YEGUA = ejemplar(
    id_caballo=8, id_raza=5, id_propietario=14, nombre="Sara", sexo="Hembra", raza="Cuarto de Milla",
    fecha_nacimiento=date(2018, 3, 9), altura=1.42, propietario="Data Horse",
    ciudad="Bogotá", departamento="Cundinamarca", ubicacion_lat=4.61, ubicacion_lng=-74.08,
    descendencia=Descendencia(padre_nombre="Doc", temperamento="Tranquilo"),
)


def resultado_ia(**cambios) -> ResultadoCompatibilidad:
    datos = dict(
        puntuacion=78, raza_puntos=80, madurez_puntos=90, altura_puntos=85, ubicacion_puntos=40,
        otros_puntos=70, nivel_confianza="media", resumen_cria="Cría equilibrada.",
        fortalezas=["Buena edad"], riesgos=["Faltan abuelos"], recomendaciones=["Prueba genética"],
        datos_faltantes_importantes=["Abuelos"], modelo="openai/gpt-oss-120b",
    )
    datos.update(cambios)
    return ResultadoCompatibilidad(**datos)


# ======================================================
# DOMINIO
# ======================================================

@pytest.mark.parametrize(
    ("nacimiento", "meses", "texto"),
    [
        (date(2022, 1, 6), 57, "4 años y 9 meses"),
        (date(2025, 11, 2), 12, "1 año"),
        (date(2026, 9, 3), 1, "1 mes"),
        (date(2026, 10, 20), 0, "0 meses"),
        (date(2027, 1, 1), 0, "0 meses"),  # fecha futura no da edad negativa
    ],
)
def test_edad(nacimiento, meses, texto):
    assert edad_en_meses(nacimiento, HOY) == meses
    assert describir_edad(meses) == texto


def test_describir_edad_plurales():
    assert describir_edad(25) == "2 años y 1 mes"


def test_distancia_km():
    assert distancia_km(CABALLO, YEGUA) == pytest.approx(240, abs=15)  # Medellín - Bogotá
    assert distancia_km(CABALLO, replace(YEGUA, ubicacion_lat=None)) is None


def test_construir_datos_no_envia_datos_del_dueno():
    datos = construir_datos(CABALLO, YEGUA, 85.0, HOY)
    texto = json.dumps(datos.como_dict(), ensure_ascii=False, default=str)

    assert datos.diferencia_altura_cm == 8.0
    assert datos.porcentaje_referencia_razas == 85.0
    assert datos.yegua["edad"] == "8 años y 7 meses"
    assert datos.yegua["descendencia"] == {"padre_nombre": "Doc", "temperamento": "Tranquilo"}
    assert "madre_nombre" in datos.yegua["descendencia_campos_sin_dato"]
    assert datos.caballo["descendencia"] == {}
    assert "David" not in texto
    assert "Data Horse" not in texto


def test_huella_cambia_solo_si_cambian_los_datos():
    a = construir_datos(CABALLO, YEGUA, 85.0, HOY)

    assert a.huella() == construir_datos(CABALLO, YEGUA, 85.0, HOY).huella()
    assert len(a.huella()) == 64
    assert a.huella() != construir_datos(CABALLO, replace(YEGUA, altura=1.5), 85.0, HOY).huella()


@pytest.mark.parametrize(
    ("cambios", "valido"),
    [
        ({}, True),
        ({"puntuacion": 101}, False),
        ({"raza_puntos": -1}, False),
        ({"otros_puntos": 50.5}, False),
        ({"nivel_confianza": "total"}, False),
        ({"resumen_cria": "   "}, False),
    ],
)
def test_resultado_es_valido(cambios, valido):
    assert resultado_es_valido(resultado_ia(**cambios)) is valido


# ======================================================
# CASO DE USO
# ======================================================

AHORA = datetime(2026, 11, 3, 2, 0, tzinfo=timezone.utc)  # 2 nov 21:00 en Colombia


@pytest.fixture
def evaluacion():
    repo, evaluador = Mock(), Mock()
    repo.obtener_ejemplar.side_effect = {10: CABALLO, 8: YEGUA}.get
    repo.porcentaje_razas.return_value = 85.0
    repo.buscar_resultado.return_value = None
    repo.contar_evaluaciones_desde.return_value = 1
    evaluador.evaluar.return_value = resultado_ia()
    caso = EvaluarCompatibilidadUseCase(repo, evaluador, 5, -5, reloj=lambda: AHORA)
    return caso, repo, evaluador


def test_evaluar_llama_a_la_ia_y_guarda(evaluacion):
    caso, repo, evaluador = evaluacion

    respuesta = caso.ejecutar(14, 10, 8)

    assert respuesta["resultado"]["puntuacion"] == 78
    assert respuesta["caballo"] == {"id_caballo": 10, "nombre": "Juan", "raza": "Criollo", "propietario": "David"}
    assert respuesta["yegua"]["propietario"] == "Data Horse"
    assert respuesta["desde_cache"] is False
    assert respuesta["evaluaciones_restantes_hoy"] == 3
    assert respuesta["aviso"] == AVISO
    datos = evaluador.evaluar.call_args.args[0]
    assert isinstance(datos, DatosEvaluacion)
    repo.porcentaje_razas.assert_called_once_with(5, 3)  # (raza yegua, raza caballo)
    # "Hoy" empieza a la medianoche de Colombia (05:00 UTC)
    repo.contar_evaluaciones_desde.assert_called_once_with(14, datetime(2026, 11, 2, 5, 0))
    usuario, caballo, yegua, huella, fecha, guardado = repo.guardar.call_args.args
    assert (usuario, caballo, yegua, fecha) == (14, 10, 8, date(2026, 11, 2))
    assert huella == datos.huella()
    assert guardado.puntuacion == 78


def test_evaluar_reutiliza_el_resultado_guardado(evaluacion):
    caso, repo, evaluador = evaluacion
    repo.buscar_resultado.return_value = resultado_ia(puntuacion=60)
    repo.contar_evaluaciones_desde.return_value = 5  # aunque no le queden, el guardado no cuenta

    respuesta = caso.ejecutar(14, 10, 8)

    assert respuesta["desde_cache"] is True
    assert respuesta["resultado"]["puntuacion"] == 60
    assert respuesta["evaluaciones_restantes_hoy"] == 0
    evaluador.evaluar.assert_not_called()
    repo.guardar.assert_not_called()


def test_evaluar_respeta_el_limite_diario(evaluacion):
    caso, repo, evaluador = evaluacion
    repo.contar_evaluaciones_desde.return_value = 5

    with pytest.raises(DemasiadosIntentosError, match="límite de 5"):
        caso.ejecutar(14, 10, 8)

    evaluador.evaluar.assert_not_called()


def test_evaluar_no_guarda_un_resultado_fuera_de_rango(evaluacion):
    caso, repo, evaluador = evaluacion
    evaluador.evaluar.return_value = resultado_ia(puntuacion=150)

    with pytest.raises(ServicioExternoError, match="no válida"):
        caso.ejecutar(14, 10, 8)

    repo.guardar.assert_not_called()


@pytest.mark.parametrize(
    ("caballo", "error", "mensaje"),
    [
        (None, RecursoNoEncontradoError, "Caballo no encontrado"),
        (replace(CABALLO, disponibilidad="Eliminado"), RecursoNoEncontradoError, "Caballo no encontrado"),
        (replace(CABALLO, sexo="Hembra"), SolicitudInvalidaError, "macho"),
        (replace(CABALLO, publicado=False), SolicitudInvalidaError, "publicación activa"),
    ],
)
def test_evaluar_valida_el_caballo(evaluacion, caballo, error, mensaje):
    caso, repo, _ = evaluacion
    repo.obtener_ejemplar.side_effect = {10: caballo, 8: YEGUA}.get

    with pytest.raises(error, match=mensaje):
        caso.ejecutar(14, 10, 8)


@pytest.mark.parametrize(
    ("yegua", "error", "mensaje"),
    [
        (None, RecursoNoEncontradoError, "Yegua no encontrada"),
        (replace(YEGUA, id_propietario=99), RecursoNoEncontradoError, "Yegua no encontrada"),
        (replace(YEGUA, disponibilidad="Eliminado"), RecursoNoEncontradoError, "Yegua no encontrada"),
        (replace(YEGUA, sexo="Macho"), SolicitudInvalidaError, "tus yeguas"),
    ],
)
def test_evaluar_valida_la_yegua(evaluacion, yegua, error, mensaje):
    caso, repo, _ = evaluacion
    repo.obtener_ejemplar.side_effect = {10: CABALLO, 8: yegua}.get

    with pytest.raises(error, match=mensaje):
        caso.ejecutar(14, 10, 8)


def test_evaluar_permite_ejemplares_del_mismo_dueno(evaluacion):
    caso, repo, _ = evaluacion
    repo.obtener_ejemplar.side_effect = {10: CABALLO, 8: replace(YEGUA, id_propietario=2)}.get

    assert caso.ejecutar(2, 10, 8)["desde_cache"] is False


def test_reloj_por_defecto_usa_utc():
    caso = EvaluarCompatibilidadUseCase(Mock(), Mock(), 5, -5)

    assert caso._reloj().tzinfo == timezone.utc
    assert ConsultarCupoCompatibilidadUseCase(Mock(), 5, -5)._reloj().tzinfo == timezone.utc


@pytest.mark.parametrize(("usadas", "restantes"), [(0, 5), (2, 3), (5, 0), (7, 0)])
def test_consultar_cupo(usadas, restantes):
    repo = Mock()
    repo.contar_evaluaciones_desde.return_value = usadas
    caso = ConsultarCupoCompatibilidadUseCase(repo, 5, -5, reloj=lambda: AHORA)

    assert caso.ejecutar(14) == {"limite": 5, "usadas": usadas, "restantes": restantes}
    repo.contar_evaluaciones_desde.assert_called_once_with(14, datetime(2026, 11, 2, 5, 0))


# ======================================================
# ADAPTADOR DE GROQ (servidor simulado)
# ======================================================

DATOS = construir_datos(CABALLO, YEGUA, 85.0, HOY)
RESPUESTA_IA = {k: v for k, v in vars(resultado_ia()).items() if k != "modelo"}


def respuesta_groq(contenido) -> httpx.Response:
    texto = contenido if isinstance(contenido, str) else json.dumps(contenido)
    return httpx.Response(200, json={"choices": [{"message": {"content": texto}}]})


def evaluador_con(*respuestas, api_key="gsk_prueba"):
    pedidos = []
    cola = list(respuestas)

    def manejar(request: httpx.Request) -> httpx.Response:
        pedidos.append(request)
        siguiente = cola.pop(0)
        if isinstance(siguiente, Exception):
            raise siguiente
        return siguiente

    cliente = httpx.Client(transport=httpx.MockTransport(manejar))
    evaluador = groq.GroqEvaluadorCompatibilidad(api_key, ("modelo-a", "modelo-b"), 5, cliente)
    return evaluador, pedidos


def test_groq_envia_esquema_estricto_y_devuelve_resultado():
    evaluador, pedidos = evaluador_con(respuesta_groq(RESPUESTA_IA))

    resultado_obtenido = evaluador.evaluar(DATOS)

    assert resultado_obtenido.puntuacion == 78
    assert resultado_obtenido.modelo == "modelo-a"
    pedido = pedidos[0]
    assert str(pedido.url) == groq.URL_GROQ
    assert pedido.headers["Authorization"] == "Bearer gsk_prueba"
    cuerpo = json.loads(pedido.content)
    assert cuerpo["model"] == "modelo-a"
    formato = cuerpo["response_format"]["json_schema"]
    assert formato["strict"] is True
    assert set(formato["schema"]["required"]) == set(RESPUESTA_IA)
    assert cuerpo["messages"][0]["content"] == groq.INSTRUCCIONES
    assert "ignóralas" in groq.INSTRUCCIONES
    assert cuerpo["messages"][1]["content"].startswith("DATOS:")


def test_groq_sin_api_key():
    evaluador, pedidos = evaluador_con(api_key="  ")

    with pytest.raises(ConfiguracionError, match="GROQ_API_KEY"):
        evaluador.evaluar(DATOS)

    assert pedidos == []


def test_groq_usa_el_modelo_de_respaldo_si_no_hay_cupo():
    evaluador, pedidos = evaluador_con(httpx.Response(429), respuesta_groq(RESPUESTA_IA))

    assert evaluador.evaluar(DATOS).modelo == "modelo-b"
    assert [json.loads(p.content)["model"] for p in pedidos] == ["modelo-a", "modelo-b"]


def test_groq_sin_cupo_en_ningun_modelo():
    evaluador, _ = evaluador_con(httpx.Response(503), httpx.Response(429))

    with pytest.raises(DemasiadosIntentosError, match="ocupado"):
        evaluador.evaluar(DATOS)


@pytest.mark.parametrize(
    ("respuesta", "mensaje"),
    [
        (httpx.Response(401, text="invalid api key"), "no está disponible"),
        (httpx.TimeoutException("lento"), "tardó demasiado"),
        (httpx.ConnectError("sin red"), "no está disponible"),
        (respuesta_groq("esto no es json"), "no válida"),
        (respuesta_groq({"puntuacion": 50}), "no válida"),
        (httpx.Response(200, json={"choices": []}), "no válida"),
    ],
)
def test_groq_errores(respuesta, mensaje):
    evaluador, _ = evaluador_con(respuesta)

    with pytest.raises(ServicioExternoError, match=mensaje):
        evaluador.evaluar(DATOS)


def test_groq_crea_su_propio_cliente():
    assert isinstance(groq.GroqEvaluadorCompatibilidad("k", ("m",))._cliente, httpx.Client)


# ======================================================
# REPOSITORIO MYSQL
# ======================================================

def fila_ejemplar(**cambios):
    datos = dict(
        id_caballo=10, raza_id_raza=3, usuario_id_usuario=2, nombre="Juan", sexo="Macho",
        fecha_nacimiento=date(2022, 1, 6), altura="1.50", color="Castaño", descripcion="Noble",
        disponibilidad="Disponible", ciudad="Medellín", departamento="Antioquia",
        ubicacion_lat="6.25", ubicacion_lng=None, raza="Criollo", propietario="David", publicado=1,
    )
    datos.update(cambios)
    return fila(**datos)


def test_repo_obtener_ejemplar_con_descendencia(motor_falso):
    guardada = fila(**{c: None for c in Descendencia.campos()} | {"padre_nombre": "Tormenta"})
    motor_falso(repo_mysql, resultado(first=fila_ejemplar()), resultado(first=guardada))

    e = repo_mysql.CompatibilidadRepositoryMySQL().obtener_ejemplar(10)

    assert (e.altura, e.ubicacion_lat, e.ubicacion_lng, e.publicado) == (1.5, 6.25, None, True)
    assert e.descendencia.padre_nombre == "Tormenta"


def test_repo_obtener_ejemplar_sin_descendencia(motor_falso):
    motor_falso(repo_mysql, resultado(first=fila_ejemplar(publicado=0)), resultado(first=None))

    e = repo_mysql.CompatibilidadRepositoryMySQL().obtener_ejemplar(10)

    assert e.descendencia is None
    assert e.publicado is False


def test_repo_obtener_ejemplar_inexistente(motor_falso):
    motor_falso(repo_mysql, resultado(first=None))

    assert repo_mysql.CompatibilidadRepositoryMySQL().obtener_ejemplar(99) is None


@pytest.mark.parametrize(("valor", "esperado"), [("85.00", 85.0), (None, None)])
def test_repo_porcentaje_razas(motor_falso, valor, esperado):
    conexion = motor_falso(repo_mysql, resultado(scalar=valor))

    assert repo_mysql.CompatibilidadRepositoryMySQL().porcentaje_razas(5, 3) == esperado
    assert conexion.execute.call_args.args[1] == {"yegua": 5, "caballo": 3}


def test_repo_buscar_resultado(motor_falso):
    motor_falso(
        repo_mysql,
        resultado(first=fila(resultado=json.dumps(RESPUESTA_IA), modelo="modelo-a")),
    )

    encontrado = repo_mysql.CompatibilidadRepositoryMySQL().buscar_resultado(10, 8, "h" * 64)

    assert encontrado == resultado_ia(modelo="modelo-a")


def test_repo_buscar_resultado_inexistente_o_sin_modelo(motor_falso):
    motor_falso(repo_mysql, resultado(first=None), resultado(first=fila(resultado=json.dumps(RESPUESTA_IA), modelo=None)))
    repo = repo_mysql.CompatibilidadRepositoryMySQL()

    assert repo.buscar_resultado(10, 8, "h") is None
    assert repo.buscar_resultado(10, 8, "h").modelo == ""


@pytest.mark.parametrize(("valor", "esperado"), [(3, 3), (None, 0)])
def test_repo_contar_evaluaciones(motor_falso, valor, esperado):
    motor_falso(repo_mysql, resultado(scalar=valor))

    assert repo_mysql.CompatibilidadRepositoryMySQL().contar_evaluaciones_desde(14, datetime(2026, 11, 2, 5)) == esperado


def test_repo_guardar_solicitud_y_resultado(motor_falso):
    conexion = motor_falso(repo_mysql, resultado(lastrowid=7), resultado())

    id_solicitud = repo_mysql.CompatibilidadRepositoryMySQL().guardar(
        14, 10, 8, "h" * 64, date(2026, 11, 2), resultado_ia()
    )

    assert id_solicitud == 7
    solicitud = conexion.execute.call_args_list[0].args[1]
    assert (solicitud["usuario"], solicitud["caballo"], solicitud["yegua"]) == (14, 10, 8)
    assert solicitud["modelo"] == "openai/gpt-oss-120b"
    assert json.loads(solicitud["resultado"]) == RESPUESTA_IA
    fila_resultado = conexion.execute.call_args_list[1].args[1]
    assert (fila_resultado["id_solicitud"], fila_resultado["puntuacion"]) == (7, 78)
    assert fila_resultado["confianza"] == "media"


# ======================================================
# MIS RESULTADOS (estudios guardados)
# ======================================================

FECHA_UTC = datetime(2026, 11, 3, 2, 18, tzinfo=timezone.utc)


def guardada(**cambios) -> EvaluacionGuardada:
    datos = dict(
        id_solicitud=1, id_usuario=14, id_caballo=10, id_yegua=8,
        creado_en=FECHA_UTC, resultado=resultado_ia(),
    )
    datos.update(cambios)
    return EvaluacionGuardada(**datos)


def test_listar_resultados_delega_en_el_repositorio():
    repo = Mock()
    repo.listar_de_usuario.return_value = [{"id_solicitud": 1}]

    assert ListarResultadosCompatibilidadUseCase(repo).ejecutar(14) == [{"id_solicitud": 1}]
    repo.listar_de_usuario.assert_called_once_with(14)


def test_obtener_resultado_guardado_sin_llamar_a_la_ia():
    repo = Mock()
    repo.obtener_evaluacion.return_value = guardada()
    repo.obtener_ejemplar.side_effect = {10: CABALLO, 8: YEGUA}.get

    respuesta = ObtenerResultadoCompatibilidadUseCase(repo).ejecutar(14, 1)

    assert respuesta["id_solicitud"] == 1
    assert respuesta["fecha"] == FECHA_UTC
    assert respuesta["resultado"]["puntuacion"] == 78
    assert respuesta["caballo"]["nombre"] == "Juan"
    assert respuesta["yegua"]["propietario"] == "Data Horse"
    assert respuesta["desde_cache"] is True
    assert respuesta["aviso"] == AVISO


@pytest.mark.parametrize(
    ("evaluacion", "ejemplares"),
    [
        (None, {10: CABALLO, 8: YEGUA}),
        (guardada(id_usuario=99), {10: CABALLO, 8: YEGUA}),  # es de otro usuario
        (guardada(), {8: YEGUA}),  # el caballo ya no existe
    ],
)
def test_obtener_resultado_no_encontrado(evaluacion, ejemplares):
    repo = Mock()
    repo.obtener_evaluacion.return_value = evaluacion
    repo.obtener_ejemplar.side_effect = ejemplares.get
    caso = ObtenerResultadoCompatibilidadUseCase(repo)

    with pytest.raises(RecursoNoEncontradoError, match="Estudio no encontrado"):
        caso.ejecutar(14, 1)


def fila_listado(**cambios):
    datos = dict(
        id_solicitud=1, creado_en=datetime(2026, 11, 3, 2, 18), puntuacion="81.00",
        nivel_confianza="media", caballo_id=10, caballo_nombre="Juan", caballo_raza="Criollo",
        caballo_propietario="David", yegua_id=8, yegua_nombre="Sara",
        yegua_raza="Cuarto de Milla", yegua_propietario="Ana",
    )
    datos.update(cambios)
    return fila(**datos)


def test_repo_listar_de_usuario(motor_falso):
    conexion = motor_falso(repo_mysql, resultado(filas=[fila_listado()]))

    lista = repo_mysql.CompatibilidadRepositoryMySQL().listar_de_usuario(14)

    assert lista == [{
        "id_solicitud": 1,
        "fecha": datetime(2026, 11, 3, 2, 18, tzinfo=timezone.utc),
        "puntuacion": 81,
        "nivel_confianza": "media",
        "caballo": {"id_caballo": 10, "nombre": "Juan", "raza": "Criollo", "propietario": "David"},
        "yegua": {"id_caballo": 8, "nombre": "Sara", "raza": "Cuarto de Milla", "propietario": "Ana"},
    }]
    assert conexion.execute.call_args.args[1] == {"id_usuario": 14}


def test_repo_obtener_evaluacion(motor_falso):
    motor_falso(
        repo_mysql,
        resultado(first=fila(
            id_solicitud=1, usuario_id_usuario=14, caballo_id_caballo=10, yegua_id_caballo=8,
            creado_en=datetime(2026, 11, 3, 2, 18), resultado=json.dumps(RESPUESTA_IA), modelo=None,
        )),
        resultado(first=None),
    )
    repo = repo_mysql.CompatibilidadRepositoryMySQL()

    evaluacion = repo.obtener_evaluacion(1)

    assert evaluacion == guardada(resultado=resultado_ia(modelo=""))
    assert repo.obtener_evaluacion(2) is None
