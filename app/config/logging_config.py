import logging
import os


def configurar_logging() -> None:
    nivel = os.getenv("LOG_LEVEL", "INFO").upper()

    niveles_validos = {
        "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    }

    if nivel not in niveles_validos:
        nivel = "INFO"

    logging.basicConfig(
        level=getattr(logging, nivel),
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )