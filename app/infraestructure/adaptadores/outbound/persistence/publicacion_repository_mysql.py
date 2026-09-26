from typing import List

from app.domain.entities.Publicaciones import Publicacion
from app.domain.ports.out.publicacion_repository_port import PublicacionRepositoryPort
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import SessionLocal
from app.infraestructure.adaptadores.outbound.persistence.db_consultas import (
    insertar_publicacion,
    obtener_publicaciones_activas,
)


def _a_entidad(fila) -> Publicacion:
    return Publicacion(
        id_publicacion=fila.id_publicacion,
        id_caballo=fila.caballo_id_caballo,
        id_usuario=fila.usuario_id_usuario,
        titulo=fila.titulo,
        descripcion=fila.descripcion,
        precio_referencia=float(fila.precio_referencia),
        estado=fila.estado,
        fecha_publicacion=fila.fecha_publicacion,
    )


class PublicacionRepositoryMySQL(PublicacionRepositoryPort):
    def create(self, publicacion: Publicacion) -> Publicacion:
        db = SessionLocal()
        try:
            datos = {
                "caballo_id_caballo": publicacion.id_caballo,
                "usuario_id_usuario": publicacion.id_usuario,
                "titulo": publicacion.titulo,
                "descripcion": publicacion.descripcion,
                "precio_referencia": publicacion.precio_referencia,
                "estado": publicacion.estado,
                "fecha_publicacion": publicacion.fecha_publicacion,
            }
            fila = insertar_publicacion(db, datos)
            return _a_entidad(fila)
        finally:
            db.close()

    def find_all_activas(self) -> List[dict]:
        db = SessionLocal()
        try:
            return obtener_publicaciones_activas(db)
        finally:
            db.close()