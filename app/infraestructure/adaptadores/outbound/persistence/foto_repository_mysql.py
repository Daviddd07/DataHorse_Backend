from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.domain.entities.foto_caballo import FotoCaballo
from app.domain.ports.out.foto_repository import FotoRepository


class FotoRepositoryMySQL(FotoRepository):

    def __init__(self, db: Session):
        self.db = db

    def guardar(self, foto: FotoCaballo) -> FotoCaballo:
        result = self.db.execute(
            text("""
                INSERT INTO foto_caballo (id_caballo, ruta, es_principal, orden)
                VALUES (:id_caballo, :ruta, :es_principal, :orden)
            """),
            {
                "id_caballo": foto.id_caballo,
                "ruta": foto.ruta,
                "es_principal": foto.es_principal,
                "orden": foto.orden,
            },
        )
        self.db.commit()
        foto.id_foto = result.lastrowid
        return foto

    def listar_por_caballo(self, id_caballo: int) -> List[FotoCaballo]:
        rows = self.db.execute(
            text("""
                SELECT id_foto, id_caballo, ruta, es_principal, orden, fecha_subida
                FROM foto_caballo
                WHERE id_caballo = :id
                ORDER BY orden ASC
            """),
            {"id": id_caballo},
        ).fetchall()

        return [
            FotoCaballo(
                id_foto=r.id_foto,
                id_caballo=r.id_caballo,
                ruta=r.ruta,
                es_principal=bool(r.es_principal),
                orden=r.orden,
                fecha_subida=r.fecha_subida,
            )
            for r in rows
        ]

    def contar_por_caballo(self, id_caballo: int) -> int:
        result = self.db.execute(
            text("SELECT COUNT(*) FROM foto_caballo WHERE id_caballo = :id"),
            {"id": id_caballo},
        ).scalar()
        return int(result or 0)

    def obtener_principal(self, id_caballo: int) -> FotoCaballo | None:
        row = self.db.execute(
            text("""
                SELECT id_foto, id_caballo, ruta, es_principal, orden, fecha_subida
                FROM foto_caballo
                WHERE id_caballo = :id AND es_principal = TRUE
                LIMIT 1
            """),
            {"id": id_caballo},
        ).fetchone()

        if not row:
            return None

        return FotoCaballo(
            id_foto=row.id_foto,
            id_caballo=row.id_caballo,
            ruta=row.ruta,
            es_principal=bool(row.es_principal),
            orden=row.orden,
            fecha_subida=row.fecha_subida,
        )