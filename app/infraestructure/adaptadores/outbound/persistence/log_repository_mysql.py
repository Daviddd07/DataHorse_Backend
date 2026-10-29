from typing import List

from app.domain.entities.log_frontend import LogFrontend
from app.domain.ports.out.log_repository_port import LogRepositoryPort
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import SessionLocal
from app.infraestructure.adaptadores.outbound.persistence.db_consultas import insertar_logs


def _a_fila(log: LogFrontend) -> dict:
    return {
        "id_usuario": log.id_usuario,
        "nivel": log.nivel,
        "mensaje": log.mensaje,
        "contexto": log.contexto,
        "url": log.url,
        "user_agent": log.user_agent,
        "sesion_id": log.sesion_id,
        "fecha": log.fecha,
    }


class LogRepositoryMySQL(LogRepositoryPort):
    def guardar_lote(self, logs: List[LogFrontend]) -> int:
        db = SessionLocal()
        try:
            return insertar_logs(db, [_a_fila(log) for log in logs])
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
