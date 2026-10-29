from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def resultado(first=None, scalar=None, filas=None, lastrowid=None, rowcount=None):
    """Simula el objeto que devuelve connection.execute()."""
    res = MagicMock()
    res.first.return_value = first
    res.scalar.return_value = scalar
    res.__iter__.side_effect = lambda: iter(filas or [])
    res.lastrowid = lastrowid
    res.rowcount = rowcount
    return res


def fila(**campos):
    return SimpleNamespace(**campos)


@pytest.fixture
def motor_falso():
    """Parchea `engine` en el módulo indicado; devuelve la conexión falsa.

    Uso: conexion = motor_falso(modulo, resultado(...), resultado(...))
    """
    parches = []

    def crear(modulo, *resultados):
        conexion = MagicMock()
        conexion.execute.side_effect = list(resultados)
        contexto = MagicMock()
        contexto.__enter__.return_value = conexion
        engine = MagicMock()
        engine.connect.return_value = contexto
        engine.begin.return_value = contexto
        parche = patch.object(modulo, "engine", engine)
        parche.start()
        parches.append(parche)
        return conexion

    yield crear

    for parche in parches:
        parche.stop()


@pytest.fixture
def anyio_backend():
    return "asyncio"
