import asyncio
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Response
from starlette.requests import Request

from app.application.use_cases.login_use_case import InvalidCredentialsError
from app.application.use_cases.registrar_use_case import EmailAlreadyExistsError
from app.domain.exceptions import DatosInvalidosError
from app.infraestructure.adaptadores.inbound.rest import controller
from app.infraestructure.adaptadores.inbound.rest.schemas import (
    LoginRequest,
    RegistrarRequest,
)


# ======================================================
# HELPERS
# ======================================================

def crear_request():
    return Request({
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/caballos",
        "raw_path": b"/caballos",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    })


def resultado(first=None, scalar=None, filas=None):
    """Simula el objeto que devuelve connection.execute()."""
    res = MagicMock()
    res.first.return_value = first
    res.scalar.return_value = scalar
    res.__iter__.return_value = iter(filas or [])
    return res


def mock_engine(metodo, *resultados, error=None):
    """Parchea engine.connect / engine.begin con una conexión falsa."""
    conexion = MagicMock()
    conexion.execute.side_effect = list(resultados)
    contexto = MagicMock()
    contexto.__enter__.return_value = conexion

    if error is not None:
        return patch.object(controller.engine, metodo, side_effect=error), conexion

    return patch.object(controller.engine, metodo, return_value=contexto), conexion


@pytest.fixture
def autenticado():
    with patch.object(controller, "_obtener_id_usuario_autenticado", return_value=10):
        yield


@pytest.fixture
def auditoria():
    with patch.object(controller, "registrar_auditoria") as mock:
        yield mock


FOTO = SimpleNamespace(id_foto=1, ruta="uploads/a.jpg", es_principal=1, orden=0)


# ======================================================
# LOGIN / REGISTRO / ME
# ======================================================

def test_login_exitoso_setea_cookie():
    use_case = MagicMock()
    use_case.execute.return_value = 7
    response = Response()

    with patch.object(controller, "create_access_token", return_value="tok"):
        resp = controller.login(
            LoginRequest(correo="a@b.com", password="12345678"),
            response,
            use_case,
        )

    assert resp == {"mensaje": "Login exitoso"}
    assert "access_token=tok" in response.headers["set-cookie"]


def test_login_credenciales_invalidas():
    use_case = MagicMock()
    use_case.execute.side_effect = InvalidCredentialsError()

    with pytest.raises(HTTPException) as error:
        controller.login(
            LoginRequest(correo="a@b.com", password="12345678"),
            Response(),
            use_case,
        )

    assert error.value.status_code == 401


def body_registro():
    return RegistrarRequest(correo="a@b.com", password="12345678", nombre="Ana")


def test_register_exitoso():
    use_case = MagicMock()
    use_case.ejecutar.return_value = SimpleNamespace(
        id_usuario=3, correo="a@b.com", nombre="Ana"
    )

    resp = controller.register(body_registro(), use_case)

    assert resp.id == 3
    assert resp.nombre == "Ana"


@pytest.mark.parametrize(
    ("excepcion", "status"),
    [
        (DatosInvalidosError("correo", "Correo invalido"), 422),
        (EmailAlreadyExistsError(), 409),
    ],
)
def test_register_errores(excepcion, status):
    use_case = MagicMock()
    use_case.ejecutar.side_effect = excepcion

    with pytest.raises(HTTPException) as error:
        controller.register(body_registro(), use_case)

    assert error.value.status_code == status


def test_me_devuelve_usuario(autenticado):
    repo = MagicMock()
    repo.find_by_id.return_value = SimpleNamespace(
        id_usuario=10, correo="a@b.com", nombre="Ana"
    )

    resp = controller.me(crear_request(), repo)

    assert resp.id == 10


def test_me_usuario_no_encontrado(autenticado):
    repo = MagicMock()
    repo.find_by_id.return_value = None

    with pytest.raises(HTTPException) as error:
        controller.me(crear_request(), repo)

    assert error.value.status_code == 401


# ======================================================
# SUBIR FOTOS
# ======================================================

def archivo_falso():
    archivo = MagicMock()
    archivo.filename = "a.jpg"
    archivo.content_type = "image/jpeg"
    archivo.read = AsyncMock(return_value=b"data")
    return archivo


def test_subir_fotos_exitoso(autenticado, auditoria):
    service = MagicMock()
    service.ejecutar.return_value = [
        SimpleNamespace(
            id_foto=1,
            ruta="uploads/a.jpg",
            es_principal=True,
            orden=0,
            fecha_subida=date(2026, 1, 1),
        )
    ]
    parche, _ = mock_engine("connect", resultado(first=SimpleNamespace(id_caballo=5)))

    with parche:
        resp = asyncio.run(
            controller.subir_fotos(5, crear_request(), [archivo_falso()], service)
        )

    assert resp[0].ruta == "/uploads/a.jpg"
    service.ejecutar.assert_called_once_with(5, [("a.jpg", "image/jpeg", b"data")])
    assert auditoria.call_args.kwargs["resultado"] == "EXITOSO"


def test_subir_fotos_caballo_no_existe(autenticado):
    parche, _ = mock_engine("connect", resultado(first=None))

    with parche, pytest.raises(HTTPException) as error:
        asyncio.run(
            controller.subir_fotos(5, crear_request(), [archivo_falso()], MagicMock())
        )

    assert error.value.status_code == 404


def test_subir_fotos_error_validacion(autenticado, auditoria):
    service = MagicMock()
    service.ejecutar.side_effect = ValueError("Formato no permitido")
    parche, _ = mock_engine("connect", resultado(first=SimpleNamespace(id_caballo=5)))

    with parche, pytest.raises(HTTPException) as error:
        asyncio.run(
            controller.subir_fotos(5, crear_request(), [archivo_falso()], service)
        )

    assert error.value.status_code == 400
    assert error.value.detail == "Formato no permitido"
    assert auditoria.call_args.kwargs["resultado"] == "FALLIDO"


# ======================================================
# DETALLE DE PUBLICACIÓN
# ======================================================

def fila_publicacion(**cambios):
    datos = dict(
        id_publicacion=1,
        titulo="Lucero - Macho",
        descripcion="desc",
        fecha_publicacion=date(2026, 1, 1),
        estado="Activa",
        precio_referencia=1000,
        usuario_id_usuario=10,
        id_caballo=5,
        nombre="Lucero",
        sexo="Macho",
        fecha_nacimiento=date(2020, 1, 1),
        altura=1.6,
        color="Castaño",
        ubicacion="Bogotá",
        disponibilidad="Disponible",
        id_raza=1,
        raza="Criollo",
        raza_descripcion="desc raza",
        propietario="Ana",
        propietario_ubicacion="Bogotá",
        propietario_telefono="300",
        es_favorita=1,
    )
    datos.update(cambios)
    return SimpleNamespace(**datos)


def test_detalle_publicacion_exitoso(autenticado):
    parche, _ = mock_engine(
        "connect",
        resultado(first=fila_publicacion()),
        resultado(filas=[FOTO]),
    )

    with parche:
        resp = controller.obtener_publicacion_detalle(1, crear_request())

    assert resp["es_mia"] is True
    assert resp["es_favorita"] is True
    assert resp["precio"] == 1000.0
    assert resp["fotos"][0]["ruta"] == "/uploads/a.jpg"


def test_detalle_publicacion_sin_precio(autenticado):
    parche, _ = mock_engine(
        "connect",
        resultado(first=fila_publicacion(precio_referencia=None, usuario_id_usuario=99)),
        resultado(filas=[]),
    )

    with parche:
        resp = controller.obtener_publicacion_detalle(1, crear_request())

    assert resp["precio"] is None
    assert resp["es_mia"] is False


def test_detalle_publicacion_no_encontrada(autenticado):
    parche, _ = mock_engine("connect", resultado(first=None))

    with parche, pytest.raises(HTTPException) as error:
        controller.obtener_publicacion_detalle(1, crear_request())

    assert error.value.status_code == 404


def test_detalle_publicacion_error_bd(autenticado):
    parche, _ = mock_engine("connect", error=Exception("fallo"))

    with parche, pytest.raises(HTTPException) as error:
        controller.obtener_publicacion_detalle(1, crear_request())

    assert error.value.status_code == 500


# ======================================================
# MIS CABALLOS
# ======================================================

def fila_mis_caballos(**cambios):
    datos = dict(
        id_caballo=5,
        nombre="Lucero",
        sexo="Macho",
        fecha_nacimiento=date(2020, 1, 1),
        altura=1.6,
        color="Castaño",
        ubicacion="Bogotá",
        ubicacion_texto="Bogotá, Colombia",
        ciudad="Bogotá",
        departamento="Cundinamarca",
        descripcion="desc",
        disponibilidad="Disponible",
        id_raza=1,
        raza="Criollo",
        foto_ruta="uploads/a.jpg",
        id_publicacion=1,
        precio_referencia=1000,
        estado_publicacion="Activa",
    )
    datos.update(cambios)
    return SimpleNamespace(**datos)


def test_listar_mis_caballos(autenticado):
    filas = [
        fila_mis_caballos(),
        fila_mis_caballos(
            id_caballo=6, foto_ruta=None, id_publicacion=None, precio_referencia=None
        ),
    ]
    parche, _ = mock_engine("connect", resultado(filas=filas))

    with parche:
        resp = controller.listar_mis_caballos(crear_request())

    assert resp[0]["foto_principal"] == "/uploads/a.jpg"
    assert resp[0]["publicado"] is True
    assert resp[1]["foto_principal"] is None
    assert resp[1]["precio"] is None
    assert resp[1]["publicado"] is False


def test_listar_mis_caballos_error_bd(autenticado):
    parche, _ = mock_engine("connect", error=Exception("fallo"))

    with parche, pytest.raises(HTTPException) as error:
        controller.listar_mis_caballos(crear_request())

    assert error.value.status_code == 500


# ======================================================
# OBTENER CABALLO
# ======================================================

def fila_caballo(**cambios):
    datos = dict(
        id_caballo=5,
        nombre="Lucero",
        sexo="Macho",
        fecha_nacimiento=date(2020, 1, 1),
        altura=1.6,
        color="Castaño",
        ubicacion="Bogotá",
        ubicacion_texto="Bogotá, Colombia",
        ciudad="Bogotá",
        departamento="Cundinamarca",
        descripcion="desc",
        disponibilidad="Disponible",
        raza_id_raza=1,
        raza="Criollo",
        id_publicacion=1,
        precio_referencia=1000,
    )
    datos.update(cambios)
    return SimpleNamespace(**datos)


@pytest.mark.parametrize(("precio", "esperado"), [(1000, 1000.0), (None, None)])
def test_obtener_caballo(autenticado, precio, esperado):
    parche, _ = mock_engine(
        "connect",
        resultado(first=fila_caballo(precio_referencia=precio)),
        resultado(filas=[FOTO]),
    )

    with parche:
        resp = controller.obtener_caballo(5, crear_request())

    assert resp["id_raza"] == 1
    assert resp["precio"] == esperado
    assert resp["fotos"][0]["es_principal"] is True


def test_obtener_caballo_no_encontrado(autenticado):
    parche, _ = mock_engine("connect", resultado(first=None))

    with parche, pytest.raises(HTTPException) as error:
        controller.obtener_caballo(5, crear_request())

    assert error.value.status_code == 404


def test_obtener_caballo_error_bd(autenticado):
    parche, _ = mock_engine("connect", error=Exception("fallo"))

    with parche, pytest.raises(HTTPException) as error:
        controller.obtener_caballo(5, crear_request())

    assert error.value.status_code == 500


# ======================================================
# ACTUALIZAR CABALLO
# ======================================================

def body_actualizar(**cambios):
    datos = dict(
        id_raza=1,
        raza_personalizada=None,
        nombre="Lucero",
        fecha_nacimiento=date(2020, 1, 1),
        altura=1.6,
        color="Castaño",
        ubicacion="Bogotá",
        descripcion="desc",
        disponibilidad="Disponible",
        precio=1000,
    )
    datos.update(cambios)
    return controller.CaballoUpdateRequest(**datos)


@pytest.mark.parametrize(
    "cambios",
    [{"nombre": "  "}, {"altura": 0}, {"disponibilidad": "Eliminado"}],
)
def test_actualizar_caballo_validaciones(autenticado, cambios):
    with pytest.raises(HTTPException) as error:
        controller.actualizar_caballo(5, body_actualizar(**cambios), crear_request())

    assert error.value.status_code == 422


def test_actualizar_macho_misma_ubicacion(autenticado):
    parche, conexion = mock_engine(
        "begin",
        resultado(first=SimpleNamespace(id_caballo=5, sexo="Macho", disponibilidad="Disponible")),
        resultado(scalar="Bogotá"),
        resultado(),  # UPDATE caballo
        resultado(),  # UPDATE publicacion
    )

    with parche, patch.object(controller, "GeocodingService") as geo:
        resp = controller.actualizar_caballo(5, body_actualizar(), crear_request())

    assert resp["id_caballo"] == 5
    geo.assert_not_called()
    assert conexion.execute.call_count == 4


def test_actualizar_hembra_con_raza_nueva_y_geocoding(autenticado):
    parche, conexion = mock_engine(
        "begin",
        resultado(first=SimpleNamespace(id_caballo=5, sexo="Hembra", disponibilidad="Disponible")),
        resultado(scalar=8),  # siguiente id de raza
        resultado(),  # INSERT raza
        resultado(scalar="Otra ciudad"),
        resultado(),  # UPDATE caballo
    )
    datos_geo = {
        "lat": 4.6,
        "lng": -74.0,
        "texto": "Bogotá, Colombia",
        "ciudad": "Bogotá",
        "departamento": "Cundinamarca",
    }

    with parche, patch.object(controller, "GeocodingService") as geo:
        geo.return_value.geocodificar.return_value = datos_geo
        resp = controller.actualizar_caballo(
            5,
            body_actualizar(id_raza=None, raza_personalizada="Nueva", precio=None),
            crear_request(),
        )

    assert resp["mensaje"] == "Caballo actualizado correctamente"
    params_update = conexion.execute.call_args_list[4].args[1]
    assert params_update["raza_id_raza"] == 8
    assert params_update["ciudad"] == "Bogotá"
    assert conexion.execute.call_count == 5


@pytest.mark.parametrize(
    "caballo",
    [None, SimpleNamespace(id_caballo=5, sexo="Macho", disponibilidad="Eliminado")],
)
def test_actualizar_caballo_no_encontrado(autenticado, caballo):
    parche, _ = mock_engine("begin", resultado(first=caballo))

    with parche, pytest.raises(HTTPException) as error:
        controller.actualizar_caballo(5, body_actualizar(), crear_request())

    assert error.value.status_code == 404


def test_actualizar_caballo_sin_raza(autenticado):
    parche, _ = mock_engine(
        "begin",
        resultado(first=SimpleNamespace(id_caballo=5, sexo="Hembra", disponibilidad="Disponible")),
    )

    with parche, pytest.raises(HTTPException) as error:
        controller.actualizar_caballo(5, body_actualizar(id_raza=None), crear_request())

    assert error.value.detail == "Debes seleccionar una raza"


def test_actualizar_macho_sin_precio(autenticado):
    parche, _ = mock_engine(
        "begin",
        resultado(first=SimpleNamespace(id_caballo=5, sexo="Macho", disponibilidad="Disponible")),
    )

    with parche, pytest.raises(HTTPException) as error:
        controller.actualizar_caballo(5, body_actualizar(precio=0), crear_request())

    assert error.value.detail == "Debes ingresar un precio valido"


def test_actualizar_caballo_error_bd(autenticado):
    parche, _ = mock_engine("begin", error=Exception("fallo"))

    with parche, pytest.raises(HTTPException) as error:
        controller.actualizar_caballo(5, body_actualizar(), crear_request())

    assert error.value.status_code == 500


# ======================================================
# ELIMINAR CABALLO
# ======================================================

def test_eliminar_caballo_exitoso(autenticado):
    parche, conexion = mock_engine(
        "begin",
        resultado(first=SimpleNamespace(id_caballo=5, disponibilidad="Disponible")),
        resultado(),
        resultado(),
    )

    with parche:
        resp = controller.eliminar_caballo(5, crear_request())

    assert resp["mensaje"] == "Caballo eliminado correctamente"
    assert conexion.execute.call_count == 3


@pytest.mark.parametrize(
    "caballo",
    [None, SimpleNamespace(id_caballo=5, disponibilidad="Eliminado")],
)
def test_eliminar_caballo_no_encontrado(autenticado, caballo):
    parche, _ = mock_engine("begin", resultado(first=caballo))

    with parche, pytest.raises(HTTPException) as error:
        controller.eliminar_caballo(5, crear_request())

    assert error.value.status_code == 404


def test_eliminar_caballo_error_bd(autenticado):
    parche, _ = mock_engine("begin", error=Exception("fallo"))

    with parche, pytest.raises(HTTPException) as error:
        controller.eliminar_caballo(5, crear_request())

    assert error.value.status_code == 500


# ======================================================
# ELIMINAR FOTO
# ======================================================

CABALLO_ACTIVO = SimpleNamespace(id_caballo=5, disponibilidad="Disponible")
FOTO_BD = SimpleNamespace(id_foto=1, ruta="uploads/a.jpg")


def test_eliminar_foto_exitoso(autenticado, auditoria):
    service = MagicMock()
    parche, _ = mock_engine(
        "begin",
        resultado(first=CABALLO_ACTIVO),
        resultado(first=FOTO_BD),
        resultado(),
    )

    with parche:
        resp = controller.eliminar_foto(5, 1, crear_request(), service)

    assert resp["id_foto"] == 1
    service.eliminar_archivo.assert_called_once_with("uploads/a.jpg")
    service.promover_principal.assert_called_once_with(5)
    assert auditoria.call_args.kwargs["resultado"] == "EXITOSO"


def test_eliminar_foto_falla_borrado_archivo(autenticado, auditoria):
    service = MagicMock()
    service.eliminar_archivo.side_effect = OSError("disco")
    parche, _ = mock_engine(
        "begin",
        resultado(first=CABALLO_ACTIVO),
        resultado(first=FOTO_BD),
        resultado(),
    )

    with parche, pytest.raises(HTTPException) as error:
        controller.eliminar_foto(5, 1, crear_request(), service)

    assert error.value.status_code == 500
    assert "archivo físico" in error.value.detail
    assert auditoria.call_args.kwargs["resultado"] == "FALLIDO"
    service.promover_principal.assert_not_called()


@pytest.mark.parametrize(
    ("resultados", "mensaje"),
    [
        ([None], "Caballo no encontrado"),
        ([SimpleNamespace(id_caballo=5, disponibilidad="Eliminado")], "Caballo no encontrado"),
        ([CABALLO_ACTIVO, None], "Foto no encontrada"),
    ],
)
def test_eliminar_foto_no_encontrado(autenticado, resultados, mensaje):
    parche, _ = mock_engine("begin", *[resultado(first=r) for r in resultados])

    with parche, pytest.raises(HTTPException) as error:
        controller.eliminar_foto(5, 1, crear_request(), MagicMock())

    assert error.value.status_code == 404
    assert error.value.detail == mensaje


def test_eliminar_foto_error_bd(autenticado):
    parche, _ = mock_engine("begin", error=Exception("fallo"))

    with parche, pytest.raises(HTTPException) as error:
        controller.eliminar_foto(5, 1, crear_request(), MagicMock())

    assert error.value.status_code == 500
