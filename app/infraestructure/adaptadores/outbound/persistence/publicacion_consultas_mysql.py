from typing import List, Optional

from sqlalchemy import text

from app.domain.ports.out.publicacion_consultas_port import PublicacionConsultasPort
from app.infraestructure.adaptadores.outbound.persistence.caballo_repository_mysql import (
    listar_fotos,
)
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import engine


def _float_o_none(valor) -> Optional[float]:
    return float(valor) if valor is not None else None


class PublicacionConsultasMySQL(PublicacionConsultasPort):

    def listar_activas(self, id_usuario_actual: int) -> List[dict]:
        with engine.connect() as connection:
            resultado = connection.execute(
                text("""
                    SELECT
                        p.id_publicacion, p.titulo, p.descripcion,
                        p.fecha_publicacion, p.estado, p.precio_referencia,
                        p.usuario_id_usuario,
                        c.id_caballo, c.nombre, c.sexo, c.fecha_nacimiento,
                        c.altura, c.color, c.ubicacion_texto, c.ciudad,
                        c.departamento, c.ubicacion_lat, c.ubicacion_lng,
                        c.ubicacion, c.disponibilidad,
                        r.id_raza,
                        r.nombre AS raza,
                        u.nombre AS propietario,
                        fc.ruta AS foto_ruta,
                        EXISTS (
                            SELECT 1
                            FROM favorito f
                            WHERE f.usuario_id_usuario = :id_usuario
                              AND f.caballo_id_caballo = c.id_caballo
                        ) AS es_favorita
                    FROM publicacion p
                    INNER JOIN caballo c
                        ON p.caballo_id_caballo = c.id_caballo
                    INNER JOIN raza r
                        ON c.raza_id_raza = r.id_raza
                    INNER JOIN usuario u
                        ON p.usuario_id_usuario = u.id_usuario
                    LEFT JOIN foto_caballo fc
                        ON fc.id_caballo = c.id_caballo
                        AND fc.es_principal = TRUE
                    WHERE p.estado = 'Activa'
                      AND c.disponibilidad != 'Eliminado'
                    ORDER BY p.id_publicacion DESC
                """),
                {"id_usuario": id_usuario_actual},
            )

            return [
                {
                    "id_publicacion": fila.id_publicacion,
                    "id_caballo": fila.id_caballo,
                    "id_usuario": fila.usuario_id_usuario,
                    "titulo": fila.titulo,
                    "nombre": fila.nombre,
                    "raza": fila.raza,
                    "sexo": fila.sexo,
                    "fecha_nacimiento": fila.fecha_nacimiento,
                    "altura": float(fila.altura),
                    "ubicacion_texto": fila.ubicacion_texto,
                    "ciudad": fila.ciudad,
                    "departamento": fila.departamento,
                    "ubicacion_lat": float(fila.ubicacion_lat) if fila.ubicacion_lat else None,
                    "ubicacion_lng": float(fila.ubicacion_lng) if fila.ubicacion_lng else None,
                    "ubicacion": fila.ubicacion,
                    "color": fila.color,
                    "descripcion": fila.descripcion,
                    "disponibilidad": fila.disponibilidad,
                    "fecha_publicacion": fila.fecha_publicacion,
                    "precio": _float_o_none(fila.precio_referencia),
                    "propietario": fila.propietario,
                    "es_mia": fila.usuario_id_usuario == id_usuario_actual,
                    "es_favorita": bool(fila.es_favorita),
                    "foto_principal": f"/{fila.foto_ruta}" if fila.foto_ruta else None,
                }
                for fila in resultado
            ]

    def obtener_detalle(self, id_publicacion: int, id_usuario_actual: int) -> Optional[dict]:
        with engine.connect() as connection:
            publicacion = connection.execute(
                text("""
                    SELECT
                        p.id_publicacion, p.titulo, p.descripcion,
                        p.fecha_publicacion, p.estado, p.precio_referencia,
                        p.usuario_id_usuario,
                        c.id_caballo, c.nombre, c.sexo, c.fecha_nacimiento,
                        c.altura, c.color, c.ubicacion, c.disponibilidad,
                        r.id_raza,
                        r.nombre AS raza,
                        r.descripcion AS raza_descripcion,
                        u.nombre AS propietario,
                        u.ubicacion AS propietario_ubicacion,
                        u.telefono AS propietario_telefono,
                        EXISTS (
                            SELECT 1
                            FROM favorito f
                            WHERE f.usuario_id_usuario = :id_usuario
                              AND f.caballo_id_caballo = c.id_caballo
                        ) AS es_favorita
                    FROM publicacion p
                    INNER JOIN caballo c
                        ON p.caballo_id_caballo = c.id_caballo
                    INNER JOIN raza r
                        ON c.raza_id_raza = r.id_raza
                    INNER JOIN usuario u
                        ON p.usuario_id_usuario = u.id_usuario
                    WHERE p.id_publicacion = :id_publicacion
                      AND c.disponibilidad != 'Eliminado'
                """),
                {"id_publicacion": id_publicacion, "id_usuario": id_usuario_actual},
            ).first()

            if publicacion is None:
                return None

            fotos = listar_fotos(connection, publicacion.id_caballo)

        return {
            "id_publicacion": publicacion.id_publicacion,
            "id_caballo": publicacion.id_caballo,
            "id_usuario": publicacion.usuario_id_usuario,
            "titulo": publicacion.titulo,
            "descripcion": publicacion.descripcion,
            "fecha_publicacion": publicacion.fecha_publicacion,
            "estado": publicacion.estado,
            "nombre": publicacion.nombre,
            "sexo": publicacion.sexo,
            "fecha_nacimiento": publicacion.fecha_nacimiento,
            "altura": float(publicacion.altura),
            "color": publicacion.color,
            "ubicacion": publicacion.ubicacion,
            "disponibilidad": publicacion.disponibilidad,
            "id_raza": publicacion.id_raza,
            "raza": publicacion.raza,
            "raza_descripcion": publicacion.raza_descripcion,
            "propietario": publicacion.propietario,
            "propietario_ubicacion": publicacion.propietario_ubicacion,
            "propietario_telefono": publicacion.propietario_telefono,
            "precio": _float_o_none(publicacion.precio_referencia),
            "es_mia": publicacion.usuario_id_usuario == id_usuario_actual,
            "es_favorita": bool(publicacion.es_favorita),
            "fotos": fotos,
        }
