"""Revisa al arrancar que el .env tenga los secretos que la API necesita.

Sin esto la API arrancaba igual y fallaba después, en el primer login o
en el primer código de verificación, con un 500 difícil de rastrear.
"""
import os
from typing import List

from app.config.settings import LARGO_MINIMO_SECRETO

# Secretos que firman tokens o códigos: deben existir y ser largos.
SECRETOS_OBLIGATORIOS = ("SECRET_KEY", "CODIGO_SECRET")

# Variables sin las que la API no puede funcionar.
VARIABLES_OBLIGATORIAS = ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME")


class ConfiguracionInvalidaError(RuntimeError):
    pass


def problemas_de_configuracion(entorno=os.environ) -> List[str]:
    problemas = []

    for nombre in VARIABLES_OBLIGATORIAS:
        if not entorno.get(nombre, "").strip():
            problemas.append(f"Falta {nombre}")

    for nombre in SECRETOS_OBLIGATORIOS:
        valor = entorno.get(nombre, "")
        if not valor.strip():
            problemas.append(f"Falta {nombre}")
        elif len(valor) < LARGO_MINIMO_SECRETO:
            problemas.append(
                f"{nombre} es demasiado corta ({len(valor)} caracteres; mínimo {LARGO_MINIMO_SECRETO})"
            )

    return problemas


def validar_configuracion(entorno=os.environ) -> None:
    """Lanza ConfiguracionInvalidaError (y la API no arranca) si falta algo."""
    problemas = problemas_de_configuracion(entorno)
    if problemas:
        raise ConfiguracionInvalidaError(
            "Configuración inválida en el .env del backend:\n  - "
            + "\n  - ".join(problemas)
            + "\nGenera un secreto con: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
