"""Reglas para aceptar un documento de respaldo. Sin dependencias externas."""
from pathlib import Path
from typing import Optional

from app.domain.entities.documento_caballo import TIPOS_DOCUMENTO
from app.domain.exceptions import SolicitudInvalidaError

DOCUMENTO_MAX_BYTES = 10 * 1024 * 1024    # 10 MB por archivo
DOCUMENTOS_MAX_POR_CABALLO = 10
TITULO_MIN, TITULO_MAX = 2, 120

# Extensión aceptada -> tipo de contenido real que debe tener el archivo
FORMATOS = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def detectar_formato(contenido: bytes) -> Optional[str]:
    """Reconoce el formato por los primeros bytes, no por el nombre ni por lo que diga el navegador."""
    if contenido.startswith(b"%PDF-"):
        return "application/pdf"
    if contenido.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(contenido) >= 12 and contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "image/webp"
    return None


def validar_tipo(tipo: str) -> str:
    tipo = (tipo or "").strip()
    if tipo not in TIPOS_DOCUMENTO:
        raise SolicitudInvalidaError(f"Tipo de documento no válido: {tipo or '(vacío)'}")
    return tipo


def validar_titulo(titulo: str) -> str:
    titulo = " ".join((titulo or "").split())
    if not TITULO_MIN <= len(titulo) <= TITULO_MAX:
        raise SolicitudInvalidaError(
            f"El título debe tener entre {TITULO_MIN} y {TITULO_MAX} caracteres"
        )
    return titulo


def validar_archivo(nombre: str, contenido: bytes) -> tuple[str, str]:
    """Devuelve (extensión, content_type real). Rechaza archivos disfrazados."""
    extension = Path(nombre or "").suffix.lower()
    if extension not in FORMATOS:
        raise SolicitudInvalidaError(
            f"{nombre}: formato no permitido. Usa PDF, JPG, PNG o WEBP"
        )

    if not contenido:
        raise SolicitudInvalidaError(f"{nombre} está vacío")

    if len(contenido) > DOCUMENTO_MAX_BYTES:
        raise SolicitudInvalidaError(f"{nombre} supera los 10 MB")

    real = detectar_formato(contenido)
    if real != FORMATOS[extension]:
        raise SolicitudInvalidaError(
            f"{nombre}: el contenido no corresponde a un archivo {extension}"
        )

    return extension, real
