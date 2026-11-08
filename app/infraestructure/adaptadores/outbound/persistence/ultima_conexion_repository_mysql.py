from datetime import datetime
from typing import Dict, Iterable, Optional

from sqlalchemy import bindparam, text

from app.domain.ports.out.presencia_port import UltimaConexionRepositoryPort
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import engine


class UltimaConexionRepositoryMySQL(UltimaConexionRepositoryPort):

    def registrar(self, id_usuario: int, momento: datetime) -> None:
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE usuario SET ultima_conexion = :momento WHERE id_usuario = :id_usuario"),
                {"momento": momento, "id_usuario": id_usuario},
            )

    def obtener(self, ids_usuario: Iterable[int]) -> Dict[int, Optional[datetime]]:
        ids = list(ids_usuario)
        if not ids:
            return {}
        consulta = text(
            "SELECT id_usuario, ultima_conexion FROM usuario WHERE id_usuario IN :ids"
        ).bindparams(bindparam("ids", expanding=True))
        with engine.connect() as connection:
            filas = connection.execute(consulta, {"ids": ids})
            return {int(fila.id_usuario): fila.ultima_conexion for fila in filas}
