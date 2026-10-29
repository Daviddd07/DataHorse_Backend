import logging

from sqlalchemy import text

from app.domain.ports.out.auditoria_port import AuditoriaPort
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import (
    engine,
)

logger = logging.getLogger(__name__)


def registrar_auditoria(
    accion: str,
    modulo: str,
    resultado: str,
    usuario_id: int | None = None,
    detalle: str | None = None,
    request_id: str | None = None,
) -> None:
    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO audit_logs (
                        usuario_id,
                        accion,
                        modulo,
                        resultado,
                        detalle,
                        request_id
                    )
                    VALUES (
                        :usuario_id,
                        :accion,
                        :modulo,
                        :resultado,
                        :detalle,
                        :request_id
                    )
                """),
                {
                    "usuario_id": usuario_id,
                    "accion": accion,
                    "modulo": modulo,
                    "resultado": resultado,
                    "detalle": detalle,
                    "request_id": request_id,
                },
            )

    except Exception:
        logger.exception(
            "No fue posible guardar el evento de auditoría."
        )


class AuditoriaMySQL(AuditoriaPort):
    def registrar(
        self,
        accion: str,
        modulo: str,
        resultado: str,
        usuario_id: int | None = None,
        detalle: str | None = None,
    ) -> None:
        registrar_auditoria(
            accion=accion,
            modulo=modulo,
            resultado=resultado,
            usuario_id=usuario_id,
            detalle=detalle,
        )
