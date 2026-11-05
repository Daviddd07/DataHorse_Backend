"""Pruebas de "Mi cuenta": consultar y editar el perfil (casos de uso, repositorio y API)."""
from datetime import date
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

import main
from app.application.use_cases.perfil_use_cases import ActualizarPerfilUseCase, ObtenerPerfilUseCase
from app.config import dependencies as deps
from app.domain.entities.Usuario import ESTADO_ACTIVO_GOOGLE, Usuario
from app.domain.entities.ubicacion import UbicacionGeocodificada
from app.domain.exceptions import DatosInvalidosError, NoAutenticadoError
from app.domain.ports.in_.perfil_ports import ActualizarPerfilComando
from app.infraestructure.adaptadores.outbound.persistence import usuario_repository_mysql as usuarios


def usuario(**cambios):
    datos = dict(
        id_usuario=7, id_rol=2, nombre="Ana", correo="ana@test.com", contrasena="hash",
        telefono=None, ubicacion="Chía, Cundinamarca", ciudad="Chía", departamento="Cundinamarca",
        ubicacion_lat=4.86, ubicacion_lng=-74.03, fecha_registro=date(2026, 9, 24), estado="activo",
    )
    datos.update(cambios)
    return Usuario(**datos)


def comando(**cambios):
    datos = dict(nombre="Ana María", telefono="300 123 4567", ciudad="Chía", departamento="Cundinamarca")
    datos.update(cambios)
    return ActualizarPerfilComando(**datos)


@pytest.fixture
def repo():
    r = Mock()
    r.find_by_id.return_value = usuario()
    return r


@pytest.fixture
def geocoding():
    g = Mock()
    g.geocodificar.return_value = UbicacionGeocodificada(
        lat=6.24, lng=-75.58, texto="Medellín, Antioquia, Colombia", ciudad="Medellín", departamento="Antioquia"
    )
    return g


# ======================================================
# CASOS DE USO
# ======================================================

def test_obtener_perfil_devuelve_el_usuario(repo):
    assert ObtenerPerfilUseCase(repo).ejecutar(7).nombre == "Ana"
    repo.find_by_id.assert_called_once_with(7)


def test_obtener_perfil_usuario_inexistente(repo):
    repo.find_by_id.return_value = None
    with pytest.raises(NoAutenticadoError):
        ObtenerPerfilUseCase(repo).ejecutar(7)


def test_actualizar_guarda_nombre_y_telefono_sin_geocodificar_si_no_cambia_la_ciudad(repo, geocoding):
    actualizado = ActualizarPerfilUseCase(repo, geocoding).ejecutar(7, comando(nombre="  Ana   María "))

    assert actualizado.nombre == "Ana María"
    assert actualizado.telefono == "300 123 4567"
    assert actualizado.ubicacion_lat == 4.86  # se conserva
    geocoding.geocodificar.assert_not_called()
    repo.actualizar_perfil.assert_called_once_with(actualizado)


def test_actualizar_geocodifica_la_nueva_ciudad(repo, geocoding):
    actualizado = ActualizarPerfilUseCase(repo, geocoding).ejecutar(
        7, comando(ciudad="Medellín", departamento="Antioquia")
    )

    geocoding.geocodificar.assert_called_once_with("Medellín, Antioquia")
    assert (actualizado.ciudad, actualizado.departamento) == ("Medellín", "Antioquia")
    assert (actualizado.ubicacion_lat, actualizado.ubicacion_lng) == (6.24, -75.58)
    assert actualizado.ubicacion_texto == "Medellín, Antioquia, Colombia"


def test_actualizar_sin_resultado_de_geocodificacion_guarda_la_ciudad(repo, geocoding):
    geocoding.geocodificar.return_value = None
    actualizado = ActualizarPerfilUseCase(repo, geocoding).ejecutar(
        7, comando(ciudad="Medellín", departamento="Antioquia")
    )

    assert actualizado.ciudad == "Medellín"
    assert actualizado.ubicacion_texto == "Medellín, Antioquia"
    assert actualizado.ubicacion_lat is None


def test_actualizar_puede_quitar_telefono_y_ubicacion(repo, geocoding):
    actualizado = ActualizarPerfilUseCase(repo, geocoding).ejecutar(
        7, comando(telefono="  ", ciudad=None, departamento=None)
    )

    assert actualizado.telefono is None
    assert actualizado.ubicacion is None and actualizado.ciudad is None
    geocoding.geocodificar.assert_not_called()


def test_actualizar_nunca_cambia_correo_rol_ni_estado(repo, geocoding):
    actualizado = ActualizarPerfilUseCase(repo, geocoding).ejecutar(7, comando())

    assert (actualizado.correo, actualizado.id_rol, actualizado.estado) == ("ana@test.com", 2, "activo")


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"nombre": "A"}, "nombre"),
        ({"nombre": "x" * 121}, "nombre"),
        ({"telefono": "abc"}, "telefono"),
        ({"ciudad": "Chía", "departamento": None}, "ubicacion"),
        ({"ciudad": None, "departamento": "Cundinamarca"}, "ubicacion"),
    ],
)
def test_actualizar_valida_los_datos(repo, geocoding, cambios, campo):
    with pytest.raises(DatosInvalidosError) as error:
        ActualizarPerfilUseCase(repo, geocoding).ejecutar(7, comando(**cambios))

    assert error.value.campo == campo
    repo.actualizar_perfil.assert_not_called()


def test_actualizar_usuario_inexistente(repo, geocoding):
    repo.find_by_id.return_value = None
    with pytest.raises(NoAutenticadoError):
        ActualizarPerfilUseCase(repo, geocoding).ejecutar(7, comando())


# ======================================================
# REPOSITORIO MYSQL
# ======================================================

def test_repositorio_actualiza_solo_los_campos_del_perfil():
    db = MagicMock()
    sesion = MagicMock()
    sesion.__enter__.return_value = db

    with patch.object(usuarios, "SessionLocal", return_value=sesion):
        usuarios.UsuarioRepositoryMySQL().actualizar_perfil(usuario(nombre="Ana María"))

    sentencia = str(db.execute.call_args.args[0])
    for columna in ("nombre", "telefono", "ciudad", "departamento", "ubicacion_lat"):
        assert columna in sentencia
    for protegida in ("correo", "rol_id_rol", "estado", "contraseña"):
        assert protegida not in sentencia
    db.commit.assert_called_once()


# ======================================================
# API
# ======================================================

@pytest.fixture
def api():
    tokens = Mock()
    tokens.decodificar.side_effect = lambda t: {"valido": "7"}.get(t)
    main.app.dependency_overrides[deps.get_token_service] = lambda: tokens

    with patch.object(main, "guardar_log_tecnico"):
        cliente = TestClient(main.app)

        def usar(proveedor):
            caso = Mock()
            main.app.dependency_overrides[proveedor] = lambda: caso
            return caso

        cliente.usar = usar
        cliente.cookies.set("access_token", "valido")
        yield cliente

    main.app.dependency_overrides.clear()


def test_api_obtener_perfil(api):
    api.usar(deps.get_obtener_perfil_use_case).ejecutar.return_value = usuario(estado=ESTADO_ACTIVO_GOOGLE)

    respuesta = api.get("/api/v1/cuenta/perfil")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": 7, "nombre": "Ana", "correo": "ana@test.com", "telefono": None,
        "ciudad": "Chía", "departamento": "Cundinamarca", "fecha_registro": "2026-09-24",
        "es_admin": False, "solo_google": True, "foto_perfil": None,
    }


def test_api_actualizar_perfil_pasa_solo_los_campos_editables(api):
    caso = api.usar(deps.get_actualizar_perfil_use_case)
    caso.ejecutar.return_value = usuario(nombre="Ana María")

    respuesta = api.patch(
        "/api/v1/cuenta/perfil",
        json={"nombre": "Ana María", "telefono": "3001234567", "ciudad": "Chía",
              "departamento": "Cundinamarca", "correo": "otro@test.com", "rol": 1},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Ana María"
    id_usuario, cmd = caso.ejecutar.call_args.args
    assert id_usuario == 7
    assert cmd == ActualizarPerfilComando("Ana María", "3001234567", "Chía", "Cundinamarca")


def test_api_actualizar_perfil_datos_invalidos(api):
    api.usar(deps.get_actualizar_perfil_use_case).ejecutar.side_effect = DatosInvalidosError(
        "telefono", "Teléfono no válido."
    )

    respuesta = api.patch("/api/v1/cuenta/perfil", json={"nombre": "Ana", "telefono": "abc"})

    assert respuesta.status_code == 422


def test_api_perfil_exige_sesion(api):
    api.cookies.clear()
    assert api.get("/api/v1/cuenta/perfil").status_code == 401
    assert api.patch("/api/v1/cuenta/perfil", json={"nombre": "Ana"}).status_code == 401
