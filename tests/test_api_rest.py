"""Pruebas de los controllers a través de HTTP, con los casos de uso simulados."""
from datetime import date
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import main
from app.config import dependencies as deps
from app.domain.entities.Usuario import Usuario
from app.domain.entities.foto_caballo import FotoCaballo
from app.domain.entities.Raza import Raza
from app.domain.exceptions import (
    AccesoDenegadoError,
    ConflictoError,
    DatosInvalidosError,
    DemasiadosIntentosError,
    DominioError,
    ErrorInternoError,
    InvalidCredentialsError,
    RecursoNoEncontradoError,
    ServicioExternoError,
    SolicitudInvalidaError,
)
from app.domain.ports.in_.cuenta_ports import CuentaRegistrada
from app.domain.ports.out.caballo_repository_port import CaballoRegistrado
from app.infraestructure.adaptadores.inbound.rest.errores import error_interno, estado_http

USUARIO = Usuario(
    id_usuario=7, id_rol=2, nombre="Ana", correo="ana@test.com",
    contrasena="hash", telefono=None, ubicacion=None, estado="activo",
)

CABALLO_BODY = {
    "id_raza": 1,
    "nombre": "Lucero",
    "sexo": "Macho",
    "fecha_nacimiento": "2020-01-01",
    "altura": 1.6,
    "color": "Castaño",
    "ubicacion": "Bogotá",
    "descripcion": "desc",
    "disponibilidad": "Disponible",
    "precio": 1000,
}


@pytest.fixture
def tokens():
    servicio = Mock()
    servicio.crear.return_value = "token-prueba"
    servicio.decodificar.side_effect = lambda t: {"valido": "7", "raro": "abc"}.get(t)
    return servicio


@pytest.fixture
def api(tokens):
    """Cliente HTTP; `api.usar(proveedor, caso)` reemplaza un caso de uso por un Mock."""
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


# ======================================================
# SEGURIDAD Y SESIÓN
# ======================================================

@pytest.mark.parametrize(
    ("cookie", "detalle"),
    [(None, "No autenticado"), ("vencido", "Sesión inválida o expirada"), ("raro", "Sesión inválida")],
)
def test_rutas_protegidas_exigen_sesion_valida(api, cookie, detalle):
    api.cookies.clear()
    if cookie:
        api.cookies.set("access_token", cookie)

    respuesta = api.get("/api/v1/caballos/mios")

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == detalle


def test_login_abre_sesion(api, tokens):
    caso = api.usar(deps.get_iniciar_sesion_use_case)
    caso.ejecutar.return_value = 7

    respuesta = api.post("/auth/login", json={"correo": "ana@test.com", "password": "Clave1234"})

    assert respuesta.status_code == 200
    assert "access_token=token-prueba" in respuesta.headers["set-cookie"]
    assert "HttpOnly" in respuesta.headers["set-cookie"]
    tokens.crear.assert_called_once_with(7)


def test_logout_borra_cookie(api):
    respuesta = api.post("/auth/logout")

    assert respuesta.json() == {"mensaje": "Sesión cerrada correctamente"}
    assert 'access_token=""' in respuesta.headers["set-cookie"]


def test_cookie_segura_en_produccion(api, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    api.usar(deps.get_iniciar_sesion_use_case).ejecutar.return_value = 7

    cookie = api.post("/auth/login", json={"correo": "ana@test.com", "password": "Clave1234"}).headers["set-cookie"]

    assert "Secure" in cookie
    assert "SameSite=none" in cookie


# ======================================================
# ERRORES DE NEGOCIO -> HTTP
# ======================================================

@pytest.mark.parametrize(
    ("error", "estado"),
    [
        (InvalidCredentialsError(), 401),
        (AccesoDenegadoError("Debes verificar tu correo"), 403),
        (DatosInvalidosError("correo", "Correo no válido."), 422),
        (ConflictoError("dup"), 409),
        (SolicitudInvalidaError("x"), 400),
        (DemasiadosIntentosError("x"), 429),
        (ServicioExternoError("x"), 502),
        (ErrorInternoError("x"), 500),
    ],
)
def test_errores_de_dominio_se_traducen(api, error, estado):
    api.usar(deps.get_iniciar_sesion_use_case).ejecutar.side_effect = error

    respuesta = api.post("/auth/login", json={"correo": "ana@test.com", "password": "Clave1234"})

    assert respuesta.status_code == estado
    assert respuesta.headers["content-type"] == "application/problem+json"
    assert respuesta.json()["detail"] == error.mensaje


def test_estado_http_por_defecto_es_500():
    assert estado_http(DominioError()) == 500


def test_error_interno_oculta_detalles_tecnicos():
    with pytest.raises(HTTPException) as error:
        with error_interno("Error al consultar razas"):
            raise RuntimeError("password=secreto")

    assert error.value.status_code == 500
    assert error.value.detail == "Error al consultar razas"


def test_error_interno_deja_pasar_errores_de_negocio():
    with pytest.raises(RecursoNoEncontradoError):
        with error_interno("x"):
            raise RecursoNoEncontradoError()


def test_fallo_de_bd_devuelve_500_legible(api):
    api.usar(deps.get_listar_razas_use_case).ejecutar.side_effect = RuntimeError("BD caída")

    respuesta = api.get("/api/v1/razas")

    assert respuesta.status_code == 500
    assert respuesta.json()["detail"] == "Error al consultar razas"


# ======================================================
# AUTENTICACIÓN
# ======================================================

@pytest.mark.parametrize(("enviado", "mensaje"), [(True, "Revisa tu correo"), (False, "reenviar código")])
def test_register(api, enviado, mensaje):
    caso = api.usar(deps.get_registrar_cuenta_use_case)
    caso.ejecutar.return_value = CuentaRegistrada(usuario=USUARIO, correo_enviado=enviado)

    respuesta = api.post(
        "/auth/register",
        json={"correo": "ana@test.com", "password": "Clave1234", "nombre": "Ana", "telefono": "300"},
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "pendiente"
    assert cuerpo["correo_enviado"] is enviado
    assert mensaje in cuerpo["mensaje"]
    assert caso.ejecutar.call_args.args[0].telefono == "300"


@pytest.mark.parametrize(
    ("ruta", "proveedor", "cuerpo", "exito"),
    [
        ("/auth/verify-email", deps.get_verificar_correo_use_case,
         {"correo": "ana@test.com", "codigo": "123456"}, "Correo verificado correctamente"),
        ("/auth/resend-code", deps.get_reenviar_codigo_use_case,
         {"correo": "ana@test.com"}, "Código reenviado correctamente"),
    ],
)
@pytest.mark.parametrize("hizo_algo", [True, False])
def test_verificacion_y_reenvio(api, ruta, proveedor, cuerpo, exito, hizo_algo):
    api.usar(proveedor).ejecutar.return_value = hizo_algo

    respuesta = api.post(ruta, json=cuerpo)

    esperado = exito if hizo_algo else "La cuenta ya está verificada"
    assert respuesta.json() == {"mensaje": esperado}


def test_google(api):
    api.usar(deps.get_autenticar_google_use_case).ejecutar.return_value = USUARIO

    respuesta = api.post("/auth/google", json={"credential": "cred"})

    assert respuesta.json()["usuario"] == {"id": 7, "nombre": "Ana", "correo": "ana@test.com"}
    assert "access_token=token-prueba" in respuesta.headers["set-cookie"]


def test_forgot_y_reset_password(api):
    solicitar = api.usar(deps.get_solicitar_recuperacion_use_case)
    restablecer = api.usar(deps.get_restablecer_contrasena_use_case)

    olvido = api.post("/auth/forgot-password", json={"correo": "ana@test.com"})
    reset = api.post(
        "/auth/reset-password",
        json={"correo": "ana@test.com", "codigo": "123456", "nueva_password": "NuevaClave1"},
    )

    assert "recibirás un código" in olvido.json()["mensaje"]
    assert reset.json() == {"mensaje": "Contraseña actualizada correctamente"}
    solicitar.ejecutar.assert_called_once_with("ana@test.com")
    restablecer.ejecutar.assert_called_once_with("ana@test.com", "123456", "NuevaClave1")


def test_me(api):
    caso = api.usar(deps.get_usuario_actual_use_case)
    caso.ejecutar.return_value = USUARIO

    assert api.get("/auth/me").json() == {"id": 7, "correo": "ana@test.com", "nombre": "Ana"}
    caso.ejecutar.assert_called_once_with(7)


# ======================================================
# RAZAS, UBICACIONES Y CABALLOS
# ======================================================

def test_listar_razas(api):
    api.usar(deps.get_listar_razas_use_case).ejecutar.return_value = [Raza(1, "Criollo", None)]

    assert api.get("/api/v1/razas").json() == [{"id_raza": 1, "nombre": "Criollo", "descripcion": None}]


def test_ubicaciones(api):
    caso = api.usar(deps.get_listar_ubicaciones_use_case)
    caso.departamentos.return_value = ["Cundinamarca"]
    caso.ciudades.return_value = ["Bogotá"]

    departamentos = api.get("/api/v1/caballos/ubicaciones/departamentos").json()
    ciudades = api.get("/api/v1/caballos/ubicaciones/ciudades", params={"departamento": "Cundinamarca"}).json()

    assert departamentos == [{"departamento": "Cundinamarca"}]
    assert ciudades == [{"ciudad": "Bogotá"}]
    caso.ciudades.assert_called_once_with("Cundinamarca")


@pytest.mark.parametrize(
    ("sexo", "mensaje", "precio"),
    [("Macho", "Publicación registrada correctamente", 1000), ("Hembra", "Yegua registrada correctamente", None)],
)
def test_registrar_caballo(api, sexo, mensaje, precio):
    caso = api.usar(deps.get_registrar_caballo_use_case)
    caso.ejecutar.return_value = CaballoRegistrado(5, 1, 9 if precio else None)

    respuesta = api.post("/api/v1/caballos", json={**CABALLO_BODY, "sexo": sexo})

    assert respuesta.status_code == 201
    assert respuesta.json()["mensaje"] == mensaje
    assert respuesta.json()["precio"] == precio
    comando = caso.ejecutar.call_args.args[0]
    assert comando.id_propietario == 7
    assert comando.fecha_nacimiento == date(2020, 1, 1)


def test_registrar_caballo_datos_invalidos(api):
    api.usar(deps.get_registrar_caballo_use_case).ejecutar.side_effect = DatosInvalidosError(
        "sexo", "El sexo debe ser Macho o Hembra"
    )

    respuesta = api.post("/api/v1/caballos", json={**CABALLO_BODY, "sexo": "Otro"})

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == "El sexo debe ser Macho o Hembra"


def test_mis_caballos_no_se_confunde_con_id(api):
    mios = api.usar(deps.get_listar_mis_caballos_use_case)
    mios.ejecutar.return_value = [{"id_caballo": 5}]
    detalle = api.usar(deps.get_obtener_caballo_use_case)

    assert api.get("/api/v1/caballos/mios").json() == [{"id_caballo": 5}]
    detalle.ejecutar.assert_not_called()


def test_obtener_caballo(api):
    caso = api.usar(deps.get_obtener_caballo_use_case)
    caso.ejecutar.return_value = {"id_caballo": 5}

    assert api.get("/api/v1/caballos/5").json() == {"id_caballo": 5}
    caso.ejecutar.assert_called_once_with(5, 7)


def test_obtener_caballo_no_encontrado(api):
    api.usar(deps.get_obtener_caballo_use_case).ejecutar.side_effect = RecursoNoEncontradoError(
        "Caballo no encontrado"
    )

    respuesta = api.get("/api/v1/caballos/5")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "Caballo no encontrado"


def test_actualizar_y_eliminar_caballo(api):
    actualizar = api.usar(deps.get_actualizar_caballo_use_case)
    eliminar = api.usar(deps.get_eliminar_caballo_use_case)
    body = {k: v for k, v in CABALLO_BODY.items() if k != "sexo"}

    actualizado = api.put("/api/v1/caballos/5", json=body)
    eliminado = api.delete("/api/v1/caballos/5")

    assert actualizado.json() == {"mensaje": "Caballo actualizado correctamente", "id_caballo": 5}
    assert eliminado.json() == {"mensaje": "Caballo eliminado correctamente", "id_caballo": 5}
    comando = actualizar.ejecutar.call_args.args[0]
    assert (comando.id_caballo, comando.id_usuario, comando.precio) == (5, 7, 1000)
    eliminar.ejecutar.assert_called_once_with(5, 7)


# ======================================================
# FOTOS Y FAVORITOS
# ======================================================

def test_subir_fotos(api):
    caso = api.usar(deps.get_subir_fotos_use_case)
    caso.ejecutar.return_value = [FotoCaballo(1, 5, "uploads/caballos/a.jpg", True, 0)]

    respuesta = api.post(
        "/api/v1/caballos/5/fotos",
        files=[("files", ("a.jpg", b"data", "image/jpeg"))],
    )

    assert respuesta.status_code == 200
    assert respuesta.json()[0]["ruta"] == "/uploads/caballos/a.jpg"
    _, id_usuario, archivos = caso.ejecutar.call_args.args
    assert id_usuario == 7
    assert archivos[0].contenido == b"data"
    assert archivos[0].content_type == "image/jpeg"


def test_subir_fotos_invalidas(api):
    api.usar(deps.get_subir_fotos_use_case).ejecutar.side_effect = SolicitudInvalidaError(
        "Tipo no permitido: text/plain"
    )

    respuesta = api.post("/api/v1/caballos/5/fotos", files=[("files", ("a.txt", b"x", "text/plain"))])

    assert respuesta.status_code == 400


def test_eliminar_foto(api):
    caso = api.usar(deps.get_eliminar_foto_use_case)

    respuesta = api.delete("/api/v1/caballos/5/fotos/1")

    assert respuesta.json() == {"mensaje": "Foto eliminada correctamente", "id_foto": 1}
    caso.ejecutar.assert_called_once_with(5, 1, 7)


@pytest.mark.parametrize(
    ("id_favorito", "esperado"),
    [(3, {"mensaje": "Agregado a favoritos", "id_favorito": 3}),
     (None, {"mensaje": "El caballo ya está en favoritos"})],
)
def test_agregar_favorito(api, id_favorito, esperado):
    api.usar(deps.get_agregar_favorito_use_case).ejecutar.return_value = id_favorito

    assert api.post("/api/v1/caballos/5/favorito").json() == esperado


@pytest.mark.parametrize(
    ("quitado", "mensaje"),
    [(True, "Eliminado de favoritos"), (False, "El caballo no estaba en favoritos")],
)
def test_quitar_favorito(api, quitado, mensaje):
    api.usar(deps.get_quitar_favorito_use_case).ejecutar.return_value = quitado

    assert api.delete("/api/v1/caballos/5/favorito").json() == {"mensaje": mensaje}


# ======================================================
# PUBLICACIONES
# ======================================================

def test_publicaciones(api):
    listar = api.usar(deps.get_listar_publicaciones_use_case)
    listar.ejecutar.return_value = [{"id_publicacion": 1}]
    detalle = api.usar(deps.get_obtener_publicacion_use_case)
    detalle.ejecutar.return_value = {"id_publicacion": 1}

    assert api.get("/publicaciones").json() == [{"id_publicacion": 1}]
    assert api.get("/publicaciones/1").json() == {"id_publicacion": 1}
    detalle.ejecutar.assert_called_once_with(1, 7)


# ======================================================
# RAÍZ DE COMPOSICIÓN
# ======================================================

def test_dependencias_construyen_todos_los_casos_de_uso():
    proveedores = [
        getattr(deps, nombre)
        for nombre in dir(deps)
        if nombre.startswith("get_") and nombre.endswith("_use_case")
        and nombre not in ("get_subir_fotos_use_case", "get_eliminar_foto_use_case")
    ]

    for proveedor in proveedores:
        assert proveedor() is not None

    foto_repo = deps.get_foto_repository(db=Mock())
    assert deps.get_subir_fotos_use_case(foto_repo) is not None
    assert deps.get_eliminar_foto_use_case(foto_repo) is not None
    assert deps.get_usuario_repo() is not None
