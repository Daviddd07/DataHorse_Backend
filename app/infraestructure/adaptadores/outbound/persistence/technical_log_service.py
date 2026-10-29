
import logging

from sqlalchemy import text

from app.infraestructure.adaptadores.outbound.persistence.db_conexion import (
    engine,
)

logger = logging.getLogger("datahorse.database_logs")


def guardar_log_tecnico(
    nivel: str,
    modulo: str,
    mensaje: str,
    request_id: str | None = None,
    metodo_http: str | None = None,
    ruta: str | None = None,
    estado_http: int | None = None,
    duracion_ms: float | None = None,
    excepcion: str | None = None,
) -> None:
    """
    Guarda un evento técnico en MySQL.
    Si falla el almacenamiento, registra el problema en consola
    sin interrumpir la operación principal.
    """
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO logs_tecnicos (
                        nivel,
                        modulo,
                        mensaje,
                        request_id,
                        metodo_http,
                        ruta,
                        estado_http,
                        duracion_ms,
                        excepcion
                    )
                    VALUES (
                        :nivel,
                        :modulo,
                        :mensaje,
                        :request_id,
                        :metodo_http,
                        :ruta,
                        :estado_http,
                        :duracion_ms,
                        :excepcion
                    )
                    """
                ),
                {
                    "nivel": nivel.upper(),
                    "modulo": modulo,
                    "mensaje": mensaje,
                    "request_id": request_id,
                    "metodo_http": metodo_http,
                    "ruta": ruta,
                    "estado_http": estado_http,
                    "duracion_ms": duracion_ms,
                    "excepcion": excepcion,
                },
            )

    except Exception:
        logger.exception(
            "No fue posible guardar el log técnico en MySQL."
        )
