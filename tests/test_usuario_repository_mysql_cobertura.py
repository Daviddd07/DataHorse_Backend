from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.application.use_cases.registrar_use_case import EmailAlreadyExistsError
from app.domain.entities.Usuario import Usuario
from app.infraestructure.adaptadores.outbound.persistence import usuario_repository_mysql as modulo


@pytest.fixture
def repo():
    return modulo.UsuarioRepositoryMySQL()


@pytest.fixture
def usuario():
    return Usuario(
        id_usuario=None,
        id_rol=2,
        nombre="Usuario Prueba",
        correo="prueba@example.com",
        contrasena="HashSeguro123",
        telefono="3001234567",
        ubicacion="Fusagasugá",
        ubicacion_lat=4.3365,
        ubicacion_lng=-74.3638,
        ubicacion_texto="Fusagasugá, Cundinamarca",
        ciudad="Fusagasugá",
        departamento="Cundinamarca",
        fecha_registro=datetime(2026, 1, 1),
        estado="activo",
    )


@pytest.fixture
def usuario_db():
    return MagicMock(
        id_usuario=10,
        rol_id_rol=2,
        nombre="Usuario Prueba",
        correo="prueba@example.com",
        contrasena="HashSeguro123",
        telefono="3001234567",
        ubicacion="Fusagasugá",
        ubicacion_lat=4.3365,
        ubicacion_lng=-74.3638,
        ubicacion_texto="Fusagasugá, Cundinamarca",
        ciudad="Fusagasugá",
        departamento="Cundinamarca",
        fecha_registro=datetime(2026, 1, 1),
        estado="activo",
    )


def test_find_by_email_no_encontrado(repo):
    db = MagicMock()
    db.scalar.return_value = None

    with patch.object(modulo, "SessionLocal") as session:
        session.return_value.__enter__.return_value = db

        assert repo.find_by_email("noexiste@example.com") is None

    db.scalar.assert_called_once()


def test_find_by_email_encontrado(repo, usuario_db):
    db = MagicMock()
    db.scalar.return_value = usuario_db

    with patch.object(modulo, "SessionLocal") as session:
        session.return_value.__enter__.return_value = db

        resultado = repo.find_by_email("prueba@example.com")

    assert resultado.id_usuario == 10
    assert resultado.id_rol == 2
    assert resultado.correo == "prueba@example.com"


def test_find_by_id_no_encontrado(repo):
    db = MagicMock()
    db.scalar.return_value = None

    with patch.object(modulo, "SessionLocal") as session:
        session.return_value.__enter__.return_value = db

        assert repo.find_by_id(999) is None


def test_find_by_id_encontrado(repo, usuario_db):
    db = MagicMock()
    db.scalar.return_value = usuario_db

    with patch.object(modulo, "SessionLocal") as session:
        session.return_value.__enter__.return_value = db

        resultado = repo.find_by_id(10)

    assert resultado.id_usuario == 10
    assert resultado.nombre == "Usuario Prueba"


def test_create_correo_ya_existente(repo, usuario):
    db = MagicMock()
    db.scalar.return_value = MagicMock()

    with patch.object(modulo, "SessionLocal") as session:
        session.return_value.__enter__.return_value = db

        with pytest.raises(EmailAlreadyExistsError):
            repo.create(usuario)

    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_create_integrity_error(repo, usuario):
    db = MagicMock()
    db.scalar.return_value = None
    db.commit.side_effect = IntegrityError("INSERT", {}, Exception("duplicado"))

    with patch.object(modulo, "SessionLocal") as session:
        session.return_value.__enter__.return_value = db

        with pytest.raises(EmailAlreadyExistsError):
            repo.create(usuario)

    db.rollback.assert_called_once()


def test_create_exitoso(repo, usuario, usuario_db):
    db = MagicMock()
    db.scalar.return_value = None
    db.refresh.side_effect = lambda objeto: (
        setattr(objeto, "id_usuario", 10),
        setattr(objeto, "rol_id_rol", 2),
    )

    with patch.object(modulo, "SessionLocal") as session:
        session.return_value.__enter__.return_value = db

        resultado = repo.create(usuario)

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()
    assert resultado.id_usuario == 10
    assert resultado.correo == usuario.correo


def test_to_domain_mapea_campos(repo, usuario_db):
    resultado = repo._to_domain(usuario_db)

    assert resultado.id_usuario == 10
    assert resultado.id_rol == 2
    assert resultado.nombre == "Usuario Prueba"
    assert resultado.correo == "prueba@example.com"
    assert resultado.ubicacion_lat == 4.3365
    assert resultado.ubicacion_lng == -74.3638
    assert resultado.ciudad == "Fusagasugá"
    assert resultado.departamento == "Cundinamarca"
