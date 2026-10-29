from datetime import date

from sqlalchemy import text

from app.domain.ports.out.favorito_repository_port import FavoritoRepositoryPort
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import engine


class FavoritoRepositoryMySQL(FavoritoRepositoryPort):

    def existe(self, id_usuario: int, id_caballo: int) -> bool:
        with engine.connect() as connection:
            fila = connection.execute(
                text("""
                    SELECT id_favorito
                    FROM favorito
                    WHERE usuario_id_usuario = :id_usuario
                      AND caballo_id_caballo = :id_caballo
                """),
                {"id_usuario": id_usuario, "id_caballo": id_caballo},
            ).first()
        return fila is not None

    def agregar(self, id_usuario: int, id_caballo: int, fecha: date) -> int:
        with engine.begin() as connection:
            resultado = connection.execute(
                text("""
                    INSERT INTO favorito (fecha, usuario_id_usuario, caballo_id_caballo)
                    VALUES (:fecha, :id_usuario, :id_caballo)
                """),
                {"fecha": fecha, "id_usuario": id_usuario, "id_caballo": id_caballo},
            )
        return int(resultado.lastrowid)

    def quitar(self, id_usuario: int, id_caballo: int) -> int:
        with engine.begin() as connection:
            resultado = connection.execute(
                text("""
                    DELETE FROM favorito
                    WHERE usuario_id_usuario = :id_usuario
                      AND caballo_id_caballo = :id_caballo
                """),
                {"id_usuario": id_usuario, "id_caballo": id_caballo},
            )
        return resultado.rowcount
