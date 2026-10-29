from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.entities.Usuario import Usuario
from app.domain.exceptions import CorreoYaRegistradoError
from app.infraestructure.adaptadores.outbound.persistence import db_tablas

db_tablas.UsuarioTabla = db_tablas.UsuarioModel

from app.infraestructure.adaptadores.outbound import usuario_repository_memoria as modulo


class RepositorioPrueba(modulo.UsuarioRepositoryMySQL):
    def find_by_id(self, id_usuario):
        return None


repo = RepositorioPrueba()


def crear_usuario_db(**cambios):
    datos = {
        "id_usuario": 1,
        "id_rol": 2,
        "nombre": "Usuario Prueba",
        "correo": "prueba@example.com",
        "contrasena": "hash_prueba",
        "telefono": "3001234567",
        "ubicacion": "Fusagasugá",
    }
    datos.update(cambios)
    return SimpleNamespace(**datos)


def crear_usuario():
    return Usuario(
        id_usuario=None,
        id_rol=2,
        nombre="Usuario Prueba",
        correo="prueba@example.com",
        contrasena="hash_prueba",
        telefono="3001234567",
        ubicacion="Fusagasugá",
    )


def configurar_sesion():
    db = MagicMock()
    contexto = MagicMock()
    contexto.__enter__.return_value = db
    contexto.__exit__.return_value = False
    return db, contexto


def preparar_modelo():
    return [
        SimpleNamespace(key=campo)
        for campo in (
            "id_usuario",
            "rol_id_rol",
            "nombre",
            "correo",
            "contrasena",
            "telefono",
            "ubicacion",
            "fecha_registro",
            "estado",
        )
    ]


def test_find_by_email_usuario_encontrado():
    db, contexto = configurar_sesion()
    db.scalar.return_value = crear_usuario_db()

    with patch.object(modulo, "SessionLocal", return_value=contexto):
        resultado = repo.find_by_email("prueba@example.com")

    assert resultado.correo == "prueba@example.com"
    assert resultado.id_usuario == 1


def test_find_by_email_usuario_no_encontrado():
    db, contexto = configurar_sesion()
    db.scalar.return_value = None

    with patch.object(modulo, "SessionLocal", return_value=contexto):
        resultado = repo.find_by_email("inexistente@example.com")

    assert resultado is None


def test_to_domain_copia_campos_existentes():
    resultado = repo._to_domain(crear_usuario_db())

    assert resultado.id_usuario == 1
    assert resultado.id_rol == 2
    assert resultado.nombre == "Usuario Prueba"
    assert resultado.correo == "prueba@example.com"


def test_to_domain_ignora_atributos_inexistentes():
    datos = crear_usuario_db(id_usuario=2, nombre="Otro Usuario")
    resultado = repo._to_domain(datos)

    assert resultado.id_usuario == 2
    assert resultado.nombre == "Otro Usuario"


def test_create_correo_ya_existente():
    db, contexto = configurar_sesion()
    db.scalar.return_value = crear_usuario_db()

    with patch.object(modulo, "SessionLocal", return_value=contexto):
        with pytest.raises(CorreoYaRegistradoError):
            repo.create(crear_usuario())

    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_create_usuario_correctamente():
    usuario = crear_usuario()
    db, contexto = configurar_sesion()
    db.scalar.return_value = None

    def guardar(objeto):
        objeto.id_usuario = 10
        objeto.id_rol = 2

    db.add.side_effect = guardar

    with patch.object(modulo, "SessionLocal", return_value=contexto):
        with patch.object(modulo, "inspect") as inspeccionar:
            inspeccionar.return_value.column_attrs = preparar_modelo()

            with patch.object(repo, "_to_domain") as convertir:
                convertir.return_value = usuario
                resultado = repo.create(usuario)

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()
    assert resultado.correo == "prueba@example.com"


def test_create_integrity_error_hace_rollback():
    db, contexto = configurar_sesion()
    db.scalar.return_value = None
    db.commit.side_effect = IntegrityError(
        "INSERT", {}, Exception("duplicado")
    )

    with patch.object(modulo, "SessionLocal", return_value=contexto):
        with patch.object(modulo, "inspect") as inspeccionar:
            inspeccionar.return_value.column_attrs = preparar_modelo()

            with pytest.raises(CorreoYaRegistradoError):
                repo.create(crear_usuario())

    db.rollback.assert_called_once()
    db.refresh.assert_not_called()
