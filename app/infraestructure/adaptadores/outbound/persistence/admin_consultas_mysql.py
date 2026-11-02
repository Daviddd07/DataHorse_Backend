from typing import List

from sqlalchemy import text

from app.domain.entities.Usuario import ESTADO_ACTIVO_GOOGLE, ROL_ADMINISTRADOR_ID
from app.domain.ports.out.admin_consultas_port import AdminConsultasPort
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import engine


class AdminConsultasMySQL(AdminConsultasPort):
    """Consultas de solo lectura para el panel de administración.

    Los caballos con disponibilidad 'Eliminado' no se cuentan, igual que en el marketplace.
    """

    def resumen(self) -> dict:
        with engine.connect() as connection:
            totales = connection.execute(
                text("""
                    SELECT
                        (SELECT COUNT(*) FROM usuario) AS usuarios_total,
                        (SELECT COUNT(*) FROM usuario
                          WHERE LOWER(estado) IN ('activo', :estado_google)) AS usuarios_activos,
                        (SELECT COUNT(*) FROM usuario
                          WHERE LOWER(estado) = 'pendiente') AS usuarios_pendientes,
                        (SELECT COUNT(*) FROM usuario
                          WHERE rol_id_rol = :id_rol_admin) AS administradores,
                        (SELECT COUNT(*) FROM usuario
                          WHERE fecha_registro >= CURDATE() - INTERVAL 30 DAY) AS usuarios_nuevos,
                        (SELECT COUNT(*) FROM caballo
                          WHERE disponibilidad != 'Eliminado') AS caballos_total,
                        (SELECT COUNT(*) FROM caballo
                          WHERE disponibilidad != 'Eliminado' AND sexo = 'Macho') AS machos,
                        (SELECT COUNT(*) FROM caballo
                          WHERE disponibilidad != 'Eliminado' AND sexo = 'Hembra') AS yeguas,
                        (SELECT COUNT(*) FROM publicacion) AS publicaciones_total,
                        (SELECT COUNT(*) FROM publicacion p
                          INNER JOIN caballo c ON p.caballo_id_caballo = c.id_caballo
                          WHERE p.estado = 'Activa'
                            AND c.disponibilidad != 'Eliminado') AS publicaciones_activas
                """),
                {"id_rol_admin": ROL_ADMINISTRADOR_ID, "estado_google": ESTADO_ACTIVO_GOOGLE},
            ).first()

            por_raza = connection.execute(
                text("""
                    SELECT r.nombre AS raza, COUNT(c.id_caballo) AS total
                    FROM raza r
                    LEFT JOIN caballo c
                        ON c.raza_id_raza = r.id_raza
                        AND c.disponibilidad != 'Eliminado'
                    GROUP BY r.id_raza, r.nombre
                    ORDER BY total DESC, r.nombre
                """)
            )

            caballos_por_raza = [{"raza": fila.raza, "total": fila.total} for fila in por_raza]

        return {
            "usuarios": {
                "total": totales.usuarios_total,
                "activos": totales.usuarios_activos,
                "pendientes": totales.usuarios_pendientes,
                "administradores": totales.administradores,
                "nuevos_ultimos_30_dias": totales.usuarios_nuevos,
            },
            "caballos": {
                "total": totales.caballos_total,
                "machos": totales.machos,
                "yeguas": totales.yeguas,
                "por_raza": caballos_por_raza,
            },
            "publicaciones": {
                "total": totales.publicaciones_total,
                "activas": totales.publicaciones_activas,
            },
        }

    def listar_usuarios(self) -> List[dict]:
        with engine.connect() as connection:
            resultado = connection.execute(
                text("""
                    SELECT
                        u.id_usuario, u.nombre, u.correo, u.estado,
                        u.fecha_registro, u.ciudad, u.departamento,
                        r.nombre_rol AS rol,
                        COUNT(DISTINCT c.id_caballo) AS caballos,
                        COUNT(DISTINCT CASE WHEN c.sexo = 'Macho'
                                            THEN c.id_caballo END) AS machos,
                        COUNT(DISTINCT CASE WHEN c.sexo = 'Hembra'
                                            THEN c.id_caballo END) AS yeguas,
                        COUNT(DISTINCT p.id_publicacion) AS publicaciones_activas
                    FROM usuario u
                    INNER JOIN rol r
                        ON u.rol_id_rol = r.id_rol
                    LEFT JOIN caballo c
                        ON c.usuario_id_usuario = u.id_usuario
                        AND c.disponibilidad != 'Eliminado'
                    LEFT JOIN publicacion p
                        ON p.caballo_id_caballo = c.id_caballo
                        AND p.estado = 'Activa'
                    GROUP BY
                        u.id_usuario, u.nombre, u.correo, u.estado,
                        u.fecha_registro, u.ciudad, u.departamento, r.nombre_rol
                    ORDER BY u.fecha_registro DESC, u.id_usuario DESC
                """)
            )

            return [
                {
                    "id_usuario": fila.id_usuario,
                    "nombre": fila.nombre,
                    "correo": fila.correo,
                    "rol": fila.rol,
                    "estado": fila.estado,
                    "fecha_registro": fila.fecha_registro,
                    "ciudad": fila.ciudad,
                    "departamento": fila.departamento,
                    "caballos": fila.caballos,
                    "machos": fila.machos,
                    "yeguas": fila.yeguas,
                    "publicaciones_activas": fila.publicaciones_activas,
                }
                for fila in resultado
            ]
