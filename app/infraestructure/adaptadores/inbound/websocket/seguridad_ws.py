"""Validaciones comunes de los WebSockets: origen permitido y sesión (cookie)."""
import os
from typing import Optional

from fastapi import WebSocket

from app.config.settings import ORIGENES_PERMITIDOS
from app.domain.ports.out.token_port import TokenPort
from app.infraestructure.adaptadores.inbound.rest.seguridad import COOKIE_SESION

CIERRE_NO_AUTENTICADO = 4401
CIERRE_ACCESO_DENEGADO = 4403
CIERRE_NO_ENCONTRADO = 4404


def origenes_permitidos() -> set[str]:
    # Misma regla que el CORS de main.py (el middleware CORS no se aplica a WebSockets).
    desde_env = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
    return set(desde_env or ORIGENES_PERMITIDOS)


def origen_permitido(websocket: WebSocket) -> bool:
    origen = websocket.headers.get("origin")
    return origen is None or origen in origenes_permitidos()


def id_usuario_de(websocket: WebSocket, tokens: TokenPort) -> Optional[int]:
    """Mismo criterio que obtener_id_usuario_autenticado, pero sin lanzar HTTPException."""
    token = websocket.cookies.get(COOKIE_SESION)
    if not token:
        return None
    id_texto = tokens.decodificar(token)
    try:
        return int(id_texto) if id_texto is not None else None
    except (ValueError, TypeError):
        return None
