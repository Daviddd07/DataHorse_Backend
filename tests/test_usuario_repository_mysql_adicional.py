from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.domain.entities.Usuario import Usuario
from app.domain.exceptions import CorreoYaRegistradoError
from app.infraestructure.adaptadores.outbound import usuario_repository_mysql as modulo


@pytest.fixture
def usuario():
    return Usuario(
        id_usuario=1,
        id_rol=2,
        nombre="Ana",
        correo="ana@example.com",
        contrasena="hash",
        telefono="3001234567",
        ubicacion="Fusagasugá",
        fecha_registro=date.today(),
        estado="ACTIVO",
    )


@pytest.fixture
def fila():
    return MagicMock(
        id_usuario=1,
        rol_id_rol=2,
        nombre="Ana",
        correo="ana@example.com",
        contrasena="hash",
        telefono="3001234567",
        ubicacion="Fusagasugá",
        fecha_registro=date.today(),
        estado="ACTIVO",
    )


def test_create_exitoso(usuario, fila):
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(modulo, "insertar_usuario", return_value=fila) as insertar,
    ):
        resultado = modulo.UsuarioRepositoryMySQL().create(usuario)

    assert resultado.id_usuario == 1
    assert resultado.nombre == "Ana"
    assert resultado.correo == "ana@example.com"
    insertar.assert_called_once()
    db.close.assert_called_once()


def test_create_correo_duplicado(usuario):
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(modulo, "insertar_usuario", side_effect=Exception("duplicado")),
        patch.object(modulo, "obtener_usuario_por_correo", return_value=MagicMock()),
    ):
        with pytest.raises(CorreoYaRegistradoError):
            modulo.UsuarioRepositoryMySQL().create(usuario)

    db.rollback.assert_called_once()
    db.close.assert_called_once()


def test_create_error_no_es_duplicado(usuario):
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(modulo, "insertar_usuario", side_effect=RuntimeError("fallo")),
        patch.object(modulo, "obtener_usuario_por_correo", return_value=None),
    ):
        with pytest.raises(RuntimeError, match="fallo"):
            modulo.UsuarioRepositoryMySQL().create(usuario)

    db.rollback.assert_called_once()
    db.close.assert_called_once()


def test_find_by_email_encontrado(fila):
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(modulo, "obtener_usuario_por_correo", return_value=fila),
    ):
        resultado = modulo.UsuarioRepositoryMySQL().find_by_email("ana@example.com")

    assert resultado is not None
    assert resultado.correo == "ana@example.com"
    db.close.assert_called_once()


def test_find_by_email_no_encontrado():
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(modulo, "obtener_usuario_por_correo", return_value=None),
    ):
        resultado = modulo.UsuarioRepositoryMySQL().find_by_email("noexiste@example.com")

    assert resultado is None
    db.close.assert_called_once()


def test_find_by_id_encontrado(fila):
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(modulo, "obtener_usuario_por_id", return_value=fila),
    ):
        resultado = modulo.UsuarioRepositoryMySQL().find_by_id(1)

    assert resultado is not None
    assert resultado.id_usuario == 1
    db.close.assert_called_once()


def test_find_by_id_no_encontrado():
    db = MagicMock()

    with (
        patch.object(modulo, "SessionLocal", return_value=db),
        patch.object(modulo, "obtener_usuario_por_id", return_value=None),
    ):
        resultado = modulo.UsuarioRepositoryMySQL().find_by_id(999)

    assert resultado is None
    db.close.assert_called_once()
