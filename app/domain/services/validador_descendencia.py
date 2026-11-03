"""Reglas de negocio de la descendencia (viven en el dominio)."""
from dataclasses import replace
from typing import Optional

from app.domain.entities.descendencia import MODALIDADES, TEMPERAMENTOS, Descendencia
from app.domain.exceptions import DatosInvalidosError

MAX_CRIAS = 200


def normalizar_descendencia(descendencia: Optional[Descendencia]) -> Optional[Descendencia]:
    """Quita espacios, convierte los textos vacíos en "sin dato" y valida las opciones."""
    if descendencia is None:
        return None

    limpios = {}
    for campo in Descendencia.campos():
        valor = getattr(descendencia, campo)
        limpios[campo] = (valor.strip() or None) if isinstance(valor, str) else valor

    resultado = replace(descendencia, **limpios)

    if resultado.modalidad is not None and resultado.modalidad not in MODALIDADES:
        raise DatosInvalidosError("modalidad", "Modalidad no válida.")
    if resultado.temperamento is not None and resultado.temperamento not in TEMPERAMENTOS:
        raise DatosInvalidosError("temperamento", "Temperamento no válido.")
    if resultado.crias_anteriores is not None and not 0 <= resultado.crias_anteriores <= MAX_CRIAS:
        raise DatosInvalidosError(
            "crias_anteriores", f"Las crías anteriores deben estar entre 0 y {MAX_CRIAS}."
        )

    return resultado
