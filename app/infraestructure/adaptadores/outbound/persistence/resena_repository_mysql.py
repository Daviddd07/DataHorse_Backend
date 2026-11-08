from datetime import date
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.domain.entities.resena import Resena, ResumenCalificacion
from app.domain.exceptions import ConflictoError
from app.domain.ports.out.resena_repository_port import ResenaRepositoryPort
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import engine


class ResenaRepositoryMySQL(ResenaRepositoryPort):

    def existe(self, id_conversacion: int, id_evaluador: int) -> bool:
        with engine.connect() as connection:
            fila = connection.execute(
                text("""
                    SELECT id_resena
                    FROM resena
                    WHERE conversacion_id_conversacion = :id_conversacion
                      AND id_usuario_evaluador = :id_evaluador
                """),
                {"id_conversacion": id_conversacion, "id_evaluador": id_evaluador},
            ).first()
        return fila is not None

    def crear(
        self,
        id_conversacion: int,
        id_evaluador: int,
        id_evaluado: int,
        calificacion: int,
        comentario: Optional[str],
        fecha: date,
    ) -> Resena:
        try:
            with engine.begin() as connection:
                resultado = connection.execute(
                    text("""
                        INSERT INTO resena
                            (calificacion, comentario, fecha, id_usuario_evaluado,
                             id_usuario_evaluador, conversacion_id_conversacion)
                        VALUES (:calificacion, :comentario, :fecha, :id_evaluado,
                                :id_evaluador, :id_conversacion)
                    """),
                    {
                        "calificacion": calificacion,
                        "comentario": comentario,
                        "fecha": fecha,
                        "id_evaluado": id_evaluado,
                        "id_evaluador": id_evaluador,
                        "id_conversacion": id_conversacion,
                    },
                )
        except IntegrityError as e:
            # La clave única (conversación, evaluador) frenó una segunda reseña simultánea
            raise ConflictoError("Ya calificaste a esta persona en esta conversación") from e

        return Resena(
            id_resena=int(resultado.lastrowid),
            id_conversacion=id_conversacion,
            id_evaluador=id_evaluador,
            id_evaluado=id_evaluado,
            calificacion=calificacion,
            comentario=comentario,
            fecha=fecha,
        )

    def resumen_de(self, id_usuario: int) -> ResumenCalificacion:
        with engine.connect() as connection:
            fila = connection.execute(
                text("""
                    SELECT AVG(calificacion) AS promedio, COUNT(*) AS total
                    FROM resena
                    WHERE id_usuario_evaluado = :id_usuario
                """),
                {"id_usuario": id_usuario},
            ).first()
        return ResumenCalificacion.desde(fila.promedio, fila.total)
