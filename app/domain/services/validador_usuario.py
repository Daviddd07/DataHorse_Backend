"""Reglas de negocio del registro (viven en el dominio)."""
import re
from typing import Optional

from app.domain.exceptions import DatosInvalidosError

RE_CORREO = re.compile(r"^[^\s@]{1,64}@[^\s@]{1,100}(?:\.[^\s@]{2,63})+$")
RE_TELEFONO = re.compile(r"^\+?[0-9 ()-]{7,30}$")


def validar_registro(nombre: str, correo: str, contrasena: str,
                     telefono: Optional[str], ubicacion: Optional[str]) -> None:
    if not 2 <= len(nombre) <= 120:
        raise DatosInvalidosError("nombre", "El nombre debe tener entre 2 y 120 caracteres.")
    if len(correo) > 180 or not RE_CORREO.match(correo):
        raise DatosInvalidosError("correo", "Correo no válido.")
    if not 8 <= len(contrasena) <= 64:
        raise DatosInvalidosError("contrasena", "La contraseña debe tener entre 8 y 64 caracteres.")
    if not (re.search(r"[a-z]", contrasena) and re.search(r"[A-Z]", contrasena) and re.search(r"\d", contrasena)):
        raise DatosInvalidosError("contrasena", "Incluye mayúscula, minúscula y número.")
    if telefono and not RE_TELEFONO.match(telefono):
        raise DatosInvalidosError("telefono", "Teléfono no válido.")
    if ubicacion and len(ubicacion) > 180:
        raise DatosInvalidosError("ubicacion", "Máximo 180 caracteres.")


def validar_nueva_contrasena(contrasena: str) -> None:
    if len(contrasena) < 8:
        raise DatosInvalidosError("contrasena", "La contraseña debe tener mínimo 8 caracteres")
    if not any(c.isupper() for c in contrasena):
        raise DatosInvalidosError("contrasena", "La contraseña debe incluir una mayúscula")
    if not any(c.islower() for c in contrasena):
        raise DatosInvalidosError("contrasena", "La contraseña debe incluir una minúscula")
    if not any(c.isdigit() for c in contrasena):
        raise DatosInvalidosError("contrasena", "La contraseña debe incluir un número")
