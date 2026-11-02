"""Pruebas del panel de administración: rol, casos de uso y consultas MySQL."""
from datetime import date
from unittest.mock import Mock

import pytest

from app.application.use_cases.admin_use_cases import (
    ListarUsuariosAdminUseCase,
    ObtenerResumenAdminUseCase,
    VerificarAdministradorUseCase,
)
from app.domain.entities.Usuario import ESTADO_ACTIVO_GOOGLE, ROL_ADMINISTRADOR_ID, Usuario
from app.domain.exceptions import AccesoDenegadoError, NoAutenticadoError
from app.infraestructure.adaptadores.outbound.persistence import admin_consultas_mysql as admin
from conftest import fila, resultado


def usuario(id_rol):
    return Usuario(
        id_usuario=7, id_rol=id_rol, nombre="Ana", correo="ana@test.com",
        contrasena="hash", telefono=None, ubicacion=None, estado="activo",
    )


# ======================================================
# ENTIDAD
# ======================================================

def test_es_administrador_segun_el_rol():
    assert usuario(ROL_ADMINISTRADOR_ID).es_administrador() is True
    assert usuario(2).es_administrador() is False


# ======================================================
# CASOS DE USO
# ======================================================

def test_verificar_administrador_permite_al_admin():
    repo = Mock()
    repo.find_by_id.return_value = usuario(ROL_ADMINISTRADOR_ID)

    VerificarAdministradorUseCase(repo).ejecutar(7)

    repo.find_by_id.assert_called_once_with(7)


def test_verificar_administrador_rechaza_usuario_normal():
    repo = Mock()
    repo.find_by_id.return_value = usuario(2)
    caso = VerificarAdministradorUseCase(repo)

    with pytest.raises(AccesoDenegadoError, match="Solo los administradores"):
        caso.ejecutar(7)


def test_verificar_administrador_usuario_inexistente():
    repo = Mock()
    repo.find_by_id.return_value = None
    caso = VerificarAdministradorUseCase(repo)

    with pytest.raises(NoAutenticadoError):
        caso.ejecutar(7)


def test_resumen_y_usuarios_delegan_en_las_consultas():
    consultas = Mock()
    consultas.resumen.return_value = {"usuarios": {}}
    consultas.listar_usuarios.return_value = [{"id_usuario": 1}]

    resumen = ObtenerResumenAdminUseCase(consultas, "http://grafana/d/logs").ejecutar()

    assert resumen == {"usuarios": {}, "enlaces": {"grafana": "http://grafana/d/logs"}}
    assert ListarUsuariosAdminUseCase(consultas).ejecutar() == [{"id_usuario": 1}]


def test_resumen_sin_grafana_configurado():
    consultas = Mock()
    consultas.resumen.return_value = {"usuarios": {}}

    assert ObtenerResumenAdminUseCase(consultas).ejecutar()["enlaces"] == {"grafana": None}


# ======================================================
# CONSULTAS MYSQL
# ======================================================

def test_resumen_agrupa_los_totales(motor_falso):
    totales = fila(
        usuarios_total=10, usuarios_activos=8, usuarios_pendientes=2, administradores=1,
        usuarios_nuevos=3, caballos_total=6, machos=4, yeguas=2,
        publicaciones_total=5, publicaciones_activas=4,
    )
    conexion = motor_falso(
        admin,
        resultado(first=totales),
        resultado(filas=[fila(raza="Criollo", total=4), fila(raza="Árabe", total=0)]),
    )

    datos = admin.AdminConsultasMySQL().resumen()

    assert datos == {
        "usuarios": {
            "total": 10, "activos": 8, "pendientes": 2,
            "administradores": 1, "nuevos_ultimos_30_dias": 3,
        },
        "caballos": {
            "total": 6, "machos": 4, "yeguas": 2,
            "por_raza": [{"raza": "Criollo", "total": 4}, {"raza": "Árabe", "total": 0}],
        },
        "publicaciones": {"total": 5, "activas": 4},
    }
    assert conexion.execute.call_args_list[0].args[1] == {
        "id_rol_admin": ROL_ADMINISTRADOR_ID,
        "estado_google": ESTADO_ACTIVO_GOOGLE,
    }


def test_listar_usuarios_con_sus_conteos(motor_falso):
    motor_falso(
        admin,
        resultado(filas=[
            fila(
                id_usuario=7, nombre="Ana", correo="ana@test.com", rol="usuario",
                estado="activo", fecha_registro=date(2026, 9, 24), ciudad="Bogotá",
                departamento="Cundinamarca", caballos=3, machos=2, yeguas=1,
                publicaciones_activas=2,
            )
        ]),
    )

    usuarios = admin.AdminConsultasMySQL().listar_usuarios()

    assert usuarios == [{
        "id_usuario": 7, "nombre": "Ana", "correo": "ana@test.com", "rol": "usuario",
        "estado": "activo", "fecha_registro": date(2026, 9, 24), "ciudad": "Bogotá",
        "departamento": "Cundinamarca", "caballos": 3, "machos": 2, "yeguas": 1,
        "publicaciones_activas": 2,
    }]
    assert "contrasena" not in usuarios[0]
