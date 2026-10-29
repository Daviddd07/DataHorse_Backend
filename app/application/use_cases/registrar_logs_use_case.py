from dataclasses import replace
from typing import List, Optional

from app.domain.entities.log_frontend import LogFrontend
from app.domain.exceptions import DatosInvalidosError
from app.domain.ports.in_.registrar_logs_port import RegistrarLogsPort
from app.domain.ports.out.log_repository_port import LogRepositoryPort

MAX_LOGS_POR_LOTE = 50


class RegistrarLogsUseCase(RegistrarLogsPort):
    def __init__(self, log_repo: LogRepositoryPort):
        self._log_repo = log_repo

    def ejecutar(self, logs: List[LogFrontend], id_usuario: Optional[int]) -> int:
        if not logs:
            raise DatosInvalidosError("logs", "El lote de logs está vacío")
        if len(logs) > MAX_LOGS_POR_LOTE:
            raise DatosInvalidosError("logs", f"Máximo {MAX_LOGS_POR_LOTE} logs por lote")

        # El usuario lo decide el servidor (viene de la cookie), nunca el body.
        return self._log_repo.guardar_lote(
            [replace(log, id_usuario=id_usuario) for log in logs]
        )
