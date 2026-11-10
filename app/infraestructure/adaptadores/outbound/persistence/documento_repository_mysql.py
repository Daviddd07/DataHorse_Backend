from typing import List, Optional

from sqlalchemy import text

from app.domain.entities.documento_caballo import ContextoCaballo, DocumentoCaballo
from app.domain.ports.out.documento_repository_port import DocumentoRepositoryPort
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import engine

COLUMNAS = """
    id_documento, caballo_id_caballo, tipo, titulo, ruta, nombre_original,
    content_type, tamano_bytes, estado_verificacion, fecha_subida
"""


def _a_dominio(fila) -> DocumentoCaballo:
    return DocumentoCaballo(
        id_documento=int(fila.id_documento),
        id_caballo=int(fila.caballo_id_caballo),
        tipo=fila.tipo,
        titulo=fila.titulo,
        ruta=fila.ruta,
        nombre_original=fila.nombre_original,
        content_type=fila.content_type,
        tamano_bytes=int(fila.tamano_bytes),
        estado_verificacion=fila.estado_verificacion,
        fecha_subida=fila.fecha_subida,
    )


class DocumentoRepositoryMySQL(DocumentoRepositoryPort):

    def guardar(self, documento: DocumentoCaballo) -> DocumentoCaballo:
        with engine.begin() as connection:
            resultado = connection.execute(
                text("""
                    INSERT INTO documento_caballo
                        (caballo_id_caballo, tipo, titulo, ruta, nombre_original,
                         content_type, tamano_bytes, estado_verificacion)
                    VALUES (:id_caballo, :tipo, :titulo, :ruta, :nombre_original,
                            :content_type, :tamano_bytes, :estado)
                """),
                {
                    "id_caballo": documento.id_caballo,
                    "tipo": documento.tipo,
                    "titulo": documento.titulo,
                    "ruta": documento.ruta,
                    "nombre_original": documento.nombre_original,
                    "content_type": documento.content_type,
                    "tamano_bytes": documento.tamano_bytes,
                    "estado": documento.estado_verificacion,
                },
            )
            fila = connection.execute(
                text(f"SELECT {COLUMNAS} FROM documento_caballo WHERE id_documento = :id"),
                {"id": resultado.lastrowid},
            ).first()
        return _a_dominio(fila)

    def listar_por_caballo(self, id_caballo: int) -> List[DocumentoCaballo]:
        with engine.connect() as connection:
            filas = connection.execute(
                text(f"""
                    SELECT {COLUMNAS} FROM documento_caballo
                    WHERE caballo_id_caballo = :id_caballo
                    ORDER BY fecha_subida, id_documento
                """),
                {"id_caballo": id_caballo},
            )
            return [_a_dominio(f) for f in filas]

    def contar_por_caballo(self, id_caballo: int) -> int:
        with engine.connect() as connection:
            return int(connection.execute(
                text("SELECT COUNT(*) FROM documento_caballo WHERE caballo_id_caballo = :id_caballo"),
                {"id_caballo": id_caballo},
            ).scalar() or 0)

    def obtener(self, id_caballo: int, id_documento: int) -> Optional[DocumentoCaballo]:
        with engine.connect() as connection:
            fila = connection.execute(
                text(f"""
                    SELECT {COLUMNAS} FROM documento_caballo
                    WHERE id_documento = :id_documento AND caballo_id_caballo = :id_caballo
                """),
                {"id_documento": id_documento, "id_caballo": id_caballo},
            ).first()
        return _a_dominio(fila) if fila else None

    def eliminar(self, id_documento: int) -> None:
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM documento_caballo WHERE id_documento = :id"),
                {"id": id_documento},
            )

    def contexto_caballo(self, id_caballo: int) -> Optional[ContextoCaballo]:
        with engine.connect() as connection:
            fila = connection.execute(
                text("""
                    SELECT
                        c.usuario_id_usuario,
                        c.disponibilidad = 'Eliminado' AS eliminado,
                        EXISTS (
                            SELECT 1 FROM publicacion p
                            WHERE p.caballo_id_caballo = c.id_caballo
                              AND p.estado = 'Activa'
                        ) AS publicado
                    FROM caballo c
                    WHERE c.id_caballo = :id_caballo
                """),
                {"id_caballo": id_caballo},
            ).first()
        if fila is None:
            return None
        return ContextoCaballo(
            id_propietario=int(fila.usuario_id_usuario),
            eliminado=bool(fila.eliminado),
            publicado=bool(fila.publicado),
        )
