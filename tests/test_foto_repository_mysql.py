from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.domain.entities.foto_caballo import FotoCaballo
from app.infraestructure.adaptadores.outbound.persistence.foto_repository_mysql import (
    FotoRepositoryMySQL,
)


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def repo(db):
    return FotoRepositoryMySQL(db)


@pytest.fixture
def foto():
    return FotoCaballo(
        id_foto=None,
        id_caballo=10,
        ruta="fotos/caballo.jpg",
        es_principal=False,
        orden=1,
    )


def fila(**cambios):
    datos = {
        "id_foto": 5,
        "id_caballo": 10,
        "ruta": "fotos/caballo.jpg",
        "es_principal": 1,
        "orden": 1,
        "fecha_subida": datetime(2026, 1, 1),
    }
    datos.update(cambios)
    return SimpleNamespace(**datos)


def test_guardar(repo, db, foto):
    db.execute.return_value.lastrowid = 25

    resultado = repo.guardar(foto)

    assert resultado is foto
    assert resultado.id_foto == 25
    db.commit.assert_called_once()


def test_listar_por_caballo_con_fotos(repo, db):
    db.execute.return_value.fetchall.return_value = [
        fila(es_principal=1),
        fila(id_foto=6, es_principal=0, orden=2),
    ]

    resultado = repo.listar_por_caballo(10)

    assert len(resultado) == 2
    assert resultado[0].es_principal is True
    assert resultado[1].es_principal is False
    assert resultado[1].id_foto == 6


def test_listar_por_caballo_sin_fotos(repo, db):
    db.execute.return_value.fetchall.return_value = []

    assert repo.listar_por_caballo(10) == []


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(3, 3), (0, 0), (None, 0)],
)
def test_contar_por_caballo(repo, db, valor, esperado):
    db.execute.return_value.scalar.return_value = valor

    assert repo.contar_por_caballo(10) == esperado


def test_obtener_principal_encontrada(repo, db):
    db.execute.return_value.fetchone.return_value = fila(es_principal=1)

    resultado = repo.obtener_principal(10)

    assert resultado.id_foto == 5
    assert resultado.es_principal is True


def test_obtener_principal_no_encontrada(repo, db):
    db.execute.return_value.fetchone.return_value = None

    assert repo.obtener_principal(10) is None


def test_obtener_por_id_encontrada(repo, db):
    db.execute.return_value.fetchone.return_value = fila()

    resultado = repo.obtener_por_id(5)

    assert resultado.id_foto == 5
    assert resultado.id_caballo == 10


def test_obtener_por_id_no_encontrada(repo, db):
    db.execute.return_value.fetchone.return_value = None

    assert repo.obtener_por_id(5) is None


def test_eliminar(repo, db):
    repo.eliminar(5)

    db.execute.assert_called_once()
    db.commit.assert_called_once()


def test_promover_principal_si_ya_existe(repo, db):
    db.execute.return_value.fetchone.return_value = fila()

    repo.promover_principal(10)

    assert db.execute.call_count == 1
    db.commit.assert_not_called()


def test_promover_principal_si_no_hay_fotos(repo, db):
    db.execute.return_value.fetchone.side_effect = [None, None]

    repo.promover_principal(10)

    assert db.execute.call_count == 2
    db.commit.assert_not_called()


def test_promover_principal_primera_foto(repo, db):
    db.execute.return_value.fetchone.side_effect = [
        None,
        SimpleNamespace(id_foto=7),
    ]

    repo.promover_principal(10)

    assert db.execute.call_count == 3
    db.commit.assert_called_once()
