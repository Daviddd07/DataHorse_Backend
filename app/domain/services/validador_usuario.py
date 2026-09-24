"""Reglas de negocio del registro (viven en el dominio)."""
import re
from typing import Optional

from app.domain.exceptions import EmailAlreadyExistsError

RE_CORREO = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
RE_TELEFONO = re.compile(r"^\+?[0-9 ()-]{7,30}$")


def validar_registro(nombre: str, correo: str, contrasena: str,
                     telefono: Optional[str], ubicacion: Optional[str]) -> None:
    if not 2 <= len(nombre) <= 120:
        raise EmailAlreadyExistsError("nombre", "El nombre debe tener entre 2 y 120 caracteres.")
    if len(correo) > 180 or not RE_CORREO.match(correo):
        raise EmailAlreadyExistsError("correo", "Correo no válido.")
    if not 8 <= len(contrasena) <= 64:
        raise EmailAlreadyExistsError("contrasena", "La contraseña debe tener entre 8 y 64 caracteres.")
    if not (re.search(r"[a-z]", contrasena) and re.search(r"[A-Z]", contrasena) and re.search(r"\d", contrasena)):
        raise EmailAlreadyExistsError("contrasena", "Incluye mayúscula, minúscula y número.")
    if telefono and not RE_TELEFONO.match(telefono):
        raise EmailAlreadyExistsError("telefono", "Teléfono no válido.")
    if ubicacion and len(ubicacion) > 180:
        raise EmailAlreadyExistsError("ubicacion", "Máximo 180 caracteres.")
