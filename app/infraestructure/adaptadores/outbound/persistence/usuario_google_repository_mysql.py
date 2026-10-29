from typing import Optional

from sqlalchemy import text

from app.domain.ports.out.usuario_google_repository_port import UsuarioGoogleRepositoryPort
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import engine


class UsuarioGoogleRepositoryMySQL(UsuarioGoogleRepositoryPort):

    def obtener_id_usuario(self, google_sub: str) -> Optional[int]:
        with engine.connect() as connection:
            fila = connection.execute(
                text("""
                    SELECT usuario_id_usuario
                    FROM usuario_google
                    WHERE google_sub = :google_sub
                """),
                {"google_sub": google_sub},
            ).first()
        return int(fila.usuario_id_usuario) if fila else None

    def obtener_sub(self, id_usuario: int) -> Optional[str]:
        with engine.connect() as connection:
            fila = connection.execute(
                text("""
                    SELECT google_sub
                    FROM usuario_google
                    WHERE usuario_id_usuario = :id_usuario
                """),
                {"id_usuario": id_usuario},
            ).first()
        return fila.google_sub if fila else None

    def vincular(self, id_usuario: int, google_sub: str) -> None:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO usuario_google (usuario_id_usuario, google_sub)
                    VALUES (:id_usuario, :google_sub)
                """),
                {"id_usuario": id_usuario, "google_sub": google_sub},
            )
