
import logging
from unittest.mock import patch

import pytest

from app.config.logging_config import configurar_logging


@pytest.mark.parametrize(
    ("nivel_entrada", "nivel_esperado"),
    [
        ("DEBUG", logging.DEBUG),
        ("INFO", logging.INFO),
        ("WARNING", logging.WARNING),
        ("ERROR", logging.ERROR),
        ("CRITICAL", logging.CRITICAL),
        ("nivel_invalido", logging.INFO),
    ],
)
def test_configurar_logging_nivel(nivel_entrada, nivel_esperado):
    with patch.dict("os.environ", {"LOG_LEVEL": nivel_entrada}):
        with patch("app.config.logging_config.logging.basicConfig") as configurar:
            configurar_logging()

    configurar.assert_called_once()

    argumentos = configurar.call_args.kwargs
    assert argumentos["level"] == nivel_esperado
    assert argumentos["force"] is True
    assert "%(levelname)s" in argumentos["format"]


def test_configurar_logging_por_defecto():
    with patch.dict("os.environ", {}, clear=True):
        with patch("app.config.logging_config.logging.basicConfig") as configurar:
            configurar_logging()

    assert configurar.call_args.kwargs["level"] == logging.INFO
