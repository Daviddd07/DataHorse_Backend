from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends

from app.config.dependencies import get_registrar_logs_use_case
from app.domain.entities.log_frontend import LogFrontend
from app.domain.ports.in_.registrar_logs_port import RegistrarLogsPort
from app.infraestructure.adaptadores.inbound.rest.errores import error_interno
from app.infraestructure.adaptadores.inbound.rest.log_schemas import LoteLogsSchema
from app.infraestructure.adaptadores.inbound.rest.seguridad import obtener_id_usuario_opcional

logs_router = APIRouter(prefix="/logs", tags=["logs"])


def _a_utc_sin_zona(fecha: datetime) -> datetime:
    """La columna es DATETIME (sin zona): se guarda siempre en UTC."""
    if fecha.tzinfo is None:
        return fecha
    return fecha.astimezone(timezone.utc).replace(tzinfo=None)


# ======================================================
# RECIBIR LOGS DEL FRONTEND
# (se aceptan también sin sesión, p. ej. desde la pantalla de login)
# ======================================================

@logs_router.post("", status_code=204)
def registrar_logs(
    body: LoteLogsSchema,
    id_usuario: Optional[int] = Depends(obtener_id_usuario_opcional),
    use_case: RegistrarLogsPort = Depends(get_registrar_logs_use_case),
):
    logs = [
        LogFrontend(
            id_log=None,
            id_usuario=None,
            nivel=log.nivel,
            mensaje=log.mensaje,
            contexto=log.contexto,
            url=log.url,
            user_agent=log.user_agent,
            sesion_id=log.sesion_id,
            fecha=_a_utc_sin_zona(log.fecha),
        )
        for log in body.logs
    ]

    with error_interno("Error al guardar los logs"):
        use_case.ejecutar(logs, id_usuario)
