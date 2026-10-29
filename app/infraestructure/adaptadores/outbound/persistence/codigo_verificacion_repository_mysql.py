from datetime import datetime
from typing import Optional

from sqlalchemy import text

from app.domain.entities.codigo_verificacion import CodigoVerificacion
from app.domain.ports.out.codigo_verificacion_repository_port import (
    CodigoVerificacionRepositoryPort,
)
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import engine


class CodigoVerificacionRepositoryMySQL(CodigoVerificacionRepositoryPort):

    def reemplazar(
        self,
        id_usuario: int,
        tipo: str,
        codigo_hash: str,
        fecha_expiracion: datetime,
    ) -> None:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    UPDATE verificacion_correo
                    SET usado = 1
                    WHERE usuario_id_usuario = :id_usuario
                      AND tipo = :tipo
                      AND usado = 0
                """),
                {"id_usuario": id_usuario, "tipo": tipo},
            )
            connection.execute(
                text("""
                    INSERT INTO verificacion_correo (
                        usuario_id_usuario, codigo_hash, tipo,
                        fecha_expiracion, usado, intentos
                    )
                    VALUES (:id_usuario, :codigo_hash, :tipo, :fecha_expiracion, 0, 0)
                """),
                {
                    "id_usuario": id_usuario,
                    "codigo_hash": codigo_hash,
                    "tipo": tipo,
                    "fecha_expiracion": fecha_expiracion,
                },
            )

    def obtener_vigente(self, id_usuario: int, tipo: str) -> Optional[CodigoVerificacion]:
        with engine.connect() as connection:
            fila = connection.execute(
                text("""
                    SELECT id_verificacion, codigo_hash, fecha_expiracion, intentos
                    FROM verificacion_correo
                    WHERE usuario_id_usuario = :id_usuario
                      AND tipo = :tipo
                      AND usado = 0
                    ORDER BY id_verificacion DESC
                    LIMIT 1
                """),
                {"id_usuario": id_usuario, "tipo": tipo},
            ).first()

        if fila is None:
            return None

        return CodigoVerificacion(
            id_verificacion=fila.id_verificacion,
            codigo_hash=fila.codigo_hash,
            fecha_expiracion=fila.fecha_expiracion,
            intentos=fila.intentos,
        )

    def marcar_usado(self, id_verificacion: int) -> None:
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE verificacion_correo SET usado = 1 WHERE id_verificacion = :id"),
                {"id": id_verificacion},
            )

    def registrar_intento_fallido(self, id_verificacion: int, max_intentos: int) -> None:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    UPDATE verificacion_correo
                    SET
                        intentos = intentos + 1,
                        usado = CASE
                            WHEN intentos + 1 >= :max_intentos THEN 1
                            ELSE usado
                        END
                    WHERE id_verificacion = :id
                """),
                {"id": id_verificacion, "max_intentos": max_intentos},
            )
