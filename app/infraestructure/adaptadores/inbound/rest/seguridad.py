import os
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response

from app.config.dependencies import get_token_service
from app.domain.ports.out.token_port import TokenPort

COOKIE_SESION = "access_token"
DURACION_SESION_SEGUNDOS = 1800


def obtener_id_usuario_autenticado(
    request: Request,
    tokens: TokenPort = Depends(get_token_service),
) -> int:
    """Lee y valida la cookie de sesión, devolviendo el id del usuario logueado."""
    token = request.cookies.get(COOKIE_SESION)

    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")

    id_texto = tokens.decodificar(token)

    if id_texto is None:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")

    try:
        return int(id_texto)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Sesión inválida")


def obtener_id_usuario_opcional(
    request: Request,
    tokens: TokenPort = Depends(get_token_service),
) -> Optional[int]:
    """Como obtener_id_usuario_autenticado, pero devuelve None en lugar de lanzar 401."""
    token = request.cookies.get(COOKIE_SESION)

    if not token:
        return None

    id_texto = tokens.decodificar(token)

    try:
        return int(id_texto) if id_texto is not None else None
    except (ValueError, TypeError):
        return None


def _opciones_cookie() -> dict:
    es_produccion = os.getenv("ENVIRONMENT") == "production"
    return {
        "httponly": True,
        "secure": es_produccion,
        "samesite": "none" if es_produccion else "lax",
    }


def abrir_sesion(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_SESION,
        value=token,
        max_age=DURACION_SESION_SEGUNDOS,
        **_opciones_cookie(),
    )


def cerrar_sesion(response: Response) -> None:
    response.delete_cookie(key=COOKIE_SESION, **_opciones_cookie())
