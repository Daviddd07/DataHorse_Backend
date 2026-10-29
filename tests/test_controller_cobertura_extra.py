from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.infraestructure.adaptadores.inbound.rest import controller


def crear_request():
    return Request({
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/caballos",
        "raw_path": b"/caballos",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    })


def crear_caballo(**cambios):
    datos = {
        "id_raza": 1,
        "raza_personalizada": None,
        "nombre": "Lucero",
        "sexo": "Macho",
        "fecha_nacimiento": date(2020, 1, 1),
        "altura": 1.60,
        "color": "Castaño",
        "ubicacion": "Fusagasugá, Cundinamarca",
        "descripcion": "Caballo de prueba",
        "disponibilidad": "Disponible",
        "precio": 1500000,
    }
    datos.update(cambios)
    return controller.CaballoCreateRequest(**datos)


def test_listar_razas_correctamente():
    filas = [
        SimpleNamespace(id_raza=1, nombre="Árabe", descripcion="Raza de prueba"),
        SimpleNamespace(id_raza=2, nombre="Criollo", descripcion="Otra raza"),
    ]
    conexion = MagicMock()
    conexion.execute.return_value = filas
    contexto = MagicMock()
    contexto.__enter__.return_value = conexion

    with patch.object(controller.engine, "connect", return_value=contexto):
        resultado = controller.listar_razas()

    assert len(resultado) == 2
    assert resultado[0]["nombre"] == "Árabe"
    assert resultado[1]["id_raza"] == 2


def test_listar_razas_error_base_datos():
    with (
        patch.object(
            controller.engine,
            "connect",
            side_effect=Exception("fallo de BD"),
        ),
        pytest.raises(HTTPException) as error,
    ):
        controller.listar_razas()

    assert error.value.status_code == 500
    assert "fallo de BD" in error.value.detail


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"sexo": "Otro"}, "El sexo debe ser Macho o Hembra"),
        ({"nombre": "   "}, "El nombre es obligatorio"),
        ({"altura": 0}, "La altura debe ser mayor que cero"),
        ({"altura": -1}, "La altura debe ser mayor que cero"),
        ({"sexo": "Macho", "precio": None}, "Debes ingresar un precio para el caballo"),
        ({"sexo": "Macho", "precio": 0}, "Debes ingresar un precio para el caballo"),
        ({"sexo": "Macho", "precio": -10}, "Debes ingresar un precio para el caballo"),
    ],
)
def test_registrar_caballo_rechaza_datos_invalidos(cambios, mensaje):
    with (
        patch.object(controller, "_obtener_id_usuario_autenticado", return_value=10),
        pytest.raises(HTTPException) as error,
    ):
        controller.registrar_caballo(crear_caballo(**cambios), crear_request())

    assert error.value.status_code == 422
    assert error.value.detail == mensaje
