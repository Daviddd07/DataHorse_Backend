from typing import List, Optional

from sqlalchemy import text

from app.domain.entities.Caballo import Caballo
from app.domain.ports.out.caballo_consultas_port import CaballoConsultasPort
from app.domain.ports.out.caballo_repository_port import (
    CaballoRegistrado,
    CaballoRepositoryPort,
    CambiosPublicacion,
    NuevaPublicacion,
)
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import engine


def _insertar_raza(connection, nombre: str, descripcion: str) -> int:
    resultado = connection.execute(
        text("""
            INSERT INTO raza (nombre, descripcion)
            VALUES (:nombre, :descripcion)
        """),
        {"nombre": nombre, "descripcion": descripcion},
    )
    return int(resultado.lastrowid)


def _a_entidad(fila) -> Caballo:
    return Caballo(
        id_caballo=fila.id_caballo,
        id_raza=fila.raza_id_raza,
        id_propietario=fila.usuario_id_usuario,
        nombre=fila.nombre,
        sexo=fila.sexo,
        fecha_nacimiento=fila.fecha_nacimiento,
        altura=float(fila.altura),
        color=fila.color,
        ubicacion=fila.ubicacion,
        descripcion=fila.descripcion,
        disponibilidad=fila.disponibilidad,
        ubicacion_lat=fila.ubicacion_lat,
        ubicacion_lng=fila.ubicacion_lng,
        ubicacion_texto=fila.ubicacion_texto,
        ciudad=fila.ciudad,
        departamento=fila.departamento,
    )


def _ruta_publica(ruta: Optional[str]) -> Optional[str]:
    return f"/{ruta}" if ruta else None


def _precio(valor) -> Optional[float]:
    return float(valor) if valor is not None else None


class CaballoRepositoryMySQL(CaballoRepositoryPort):

    def existe(self, id_caballo: int) -> bool:
        with engine.connect() as connection:
            fila = connection.execute(
                text("SELECT id_caballo FROM caballo WHERE id_caballo = :id_caballo"),
                {"id_caballo": id_caballo},
            ).first()
        return fila is not None

    def obtener_de_propietario(self, id_caballo: int, id_usuario: int) -> Optional[Caballo]:
        with engine.connect() as connection:
            fila = connection.execute(
                text("""
                    SELECT
                        id_caballo, raza_id_raza, usuario_id_usuario,
                        nombre, sexo, fecha_nacimiento, altura, color,
                        ubicacion, descripcion, disponibilidad,
                        ubicacion_lat, ubicacion_lng, ubicacion_texto,
                        ciudad, departamento
                    FROM caballo
                    WHERE id_caballo = :id_caballo
                      AND usuario_id_usuario = :id_usuario
                """),
                {"id_caballo": id_caballo, "id_usuario": id_usuario},
            ).first()
        return _a_entidad(fila) if fila else None

    def registrar(
        self,
        caballo: Caballo,
        raza_nueva: Optional[str],
        publicacion: Optional[NuevaPublicacion],
    ) -> CaballoRegistrado:
        with engine.begin() as connection:
            id_raza = (
                _insertar_raza(connection, raza_nueva, "Raza registrada desde publicación")
                if raza_nueva
                else caballo.id_raza
            )

            resultado = connection.execute(
                text("""
                    INSERT INTO caballo (
                        nombre, sexo, fecha_nacimiento, altura, color,
                        ubicacion, ubicacion_lat, ubicacion_lng, ubicacion_texto,
                        ciudad, departamento, descripcion, disponibilidad,
                        raza_id_raza, usuario_id_usuario
                    )
                    VALUES (
                        :nombre, :sexo, :fecha_nacimiento, :altura, :color,
                        :ubicacion, :ubicacion_lat, :ubicacion_lng, :ubicacion_texto,
                        :ciudad, :departamento, :descripcion, :disponibilidad,
                        :raza_id_raza, :usuario_id_usuario
                    )
                """),
                {
                    "nombre": caballo.nombre,
                    "sexo": caballo.sexo,
                    "fecha_nacimiento": caballo.fecha_nacimiento,
                    "altura": caballo.altura,
                    "color": caballo.color,
                    "ubicacion": caballo.ubicacion,
                    "ubicacion_lat": caballo.ubicacion_lat,
                    "ubicacion_lng": caballo.ubicacion_lng,
                    "ubicacion_texto": caballo.ubicacion_texto,
                    "ciudad": caballo.ciudad,
                    "departamento": caballo.departamento,
                    "descripcion": caballo.descripcion,
                    "disponibilidad": caballo.disponibilidad,
                    "raza_id_raza": id_raza,
                    "usuario_id_usuario": caballo.id_propietario,
                },
            )
            id_caballo = int(resultado.lastrowid)

            id_publicacion = None
            if publicacion is not None:
                resultado = connection.execute(
                    text("""
                        INSERT INTO publicacion (
                            titulo, descripcion, fecha_publicacion, estado,
                            precio_referencia, caballo_id_caballo, usuario_id_usuario
                        )
                        VALUES (
                            :titulo, :descripcion, :fecha_publicacion, :estado,
                            :precio_referencia, :caballo_id_caballo, :usuario_id_usuario
                        )
                    """),
                    {
                        "titulo": publicacion.titulo,
                        "descripcion": publicacion.descripcion,
                        "fecha_publicacion": publicacion.fecha_publicacion,
                        "estado": publicacion.estado,
                        "precio_referencia": publicacion.precio_referencia,
                        "caballo_id_caballo": id_caballo,
                        "usuario_id_usuario": caballo.id_propietario,
                    },
                )
                id_publicacion = int(resultado.lastrowid)

        return CaballoRegistrado(
            id_caballo=id_caballo,
            id_raza=id_raza,
            id_publicacion=id_publicacion,
        )

    def actualizar(
        self,
        caballo: Caballo,
        raza_nueva: Optional[str],
        publicacion: Optional[CambiosPublicacion],
    ) -> None:
        with engine.begin() as connection:
            id_raza = (
                _insertar_raza(connection, raza_nueva, "Raza registrada desde edicion")
                if raza_nueva
                else caballo.id_raza
            )

            connection.execute(
                text("""
                    UPDATE caballo
                    SET
                        nombre = :nombre,
                        fecha_nacimiento = :fecha_nacimiento,
                        altura = :altura,
                        color = :color,
                        ubicacion = :ubicacion,
                        ubicacion_lat = COALESCE(:ubicacion_lat, ubicacion_lat),
                        ubicacion_lng = COALESCE(:ubicacion_lng, ubicacion_lng),
                        ubicacion_texto = :ubicacion_texto,
                        ciudad = COALESCE(:ciudad, ciudad),
                        departamento = COALESCE(:departamento, departamento),
                        descripcion = :descripcion,
                        disponibilidad = :disponibilidad,
                        raza_id_raza = :raza_id_raza
                    WHERE id_caballo = :id_caballo
                """),
                {
                    "nombre": caballo.nombre,
                    "fecha_nacimiento": caballo.fecha_nacimiento,
                    "altura": caballo.altura,
                    "color": caballo.color,
                    "ubicacion": caballo.ubicacion,
                    "ubicacion_lat": caballo.ubicacion_lat,
                    "ubicacion_lng": caballo.ubicacion_lng,
                    "ubicacion_texto": caballo.ubicacion_texto,
                    "ciudad": caballo.ciudad,
                    "departamento": caballo.departamento,
                    "descripcion": caballo.descripcion,
                    "disponibilidad": caballo.disponibilidad,
                    "raza_id_raza": id_raza,
                    "id_caballo": caballo.id_caballo,
                },
            )

            if publicacion is not None:
                connection.execute(
                    text("""
                        UPDATE publicacion
                        SET
                            titulo = :titulo,
                            descripcion = :descripcion,
                            precio_referencia = :precio
                        WHERE caballo_id_caballo = :id_caballo
                          AND estado = 'Activa'
                    """),
                    {
                        "titulo": publicacion.titulo,
                        "descripcion": publicacion.descripcion,
                        "precio": publicacion.precio_referencia,
                        "id_caballo": caballo.id_caballo,
                    },
                )

    def eliminar(self, id_caballo: int) -> None:
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM publicacion WHERE caballo_id_caballo = :id_caballo"),
                {"id_caballo": id_caballo},
            )
            connection.execute(
                text("""
                    UPDATE caballo
                    SET disponibilidad = 'Eliminado'
                    WHERE id_caballo = :id_caballo
                """),
                {"id_caballo": id_caballo},
            )


class CaballoConsultasMySQL(CaballoConsultasPort):

    def listar_de_propietario(self, id_usuario: int) -> List[dict]:
        with engine.connect() as connection:
            resultado = connection.execute(
                text("""
                    SELECT
                        c.id_caballo, c.nombre, c.sexo, c.fecha_nacimiento,
                        c.altura, c.color, c.ubicacion, c.ubicacion_texto,
                        c.ciudad, c.departamento, c.descripcion, c.disponibilidad,
                        r.id_raza,
                        r.nombre AS raza,
                        fc.ruta AS foto_ruta,
                        p.id_publicacion,
                        p.precio_referencia
                    FROM caballo c
                    INNER JOIN raza r
                        ON c.raza_id_raza = r.id_raza
                    LEFT JOIN foto_caballo fc
                        ON fc.id_caballo = c.id_caballo
                        AND fc.es_principal = TRUE
                    LEFT JOIN publicacion p
                        ON p.caballo_id_caballo = c.id_caballo
                        AND p.estado = 'Activa'
                    WHERE c.usuario_id_usuario = :id_usuario
                      AND c.disponibilidad != 'Eliminado'
                    ORDER BY c.id_caballo DESC
                """),
                {"id_usuario": id_usuario},
            )

            return [
                {
                    "id_caballo": fila.id_caballo,
                    "nombre": fila.nombre,
                    "sexo": fila.sexo,
                    "fecha_nacimiento": fila.fecha_nacimiento,
                    "altura": float(fila.altura),
                    "color": fila.color,
                    "ubicacion": fila.ubicacion,
                    "ubicacion_texto": fila.ubicacion_texto,
                    "ciudad": fila.ciudad,
                    "departamento": fila.departamento,
                    "descripcion": fila.descripcion,
                    "disponibilidad": fila.disponibilidad,
                    "id_raza": fila.id_raza,
                    "raza": fila.raza,
                    "foto_principal": _ruta_publica(fila.foto_ruta),
                    "id_publicacion": fila.id_publicacion,
                    "precio": _precio(fila.precio_referencia),
                    "publicado": fila.id_publicacion is not None,
                }
                for fila in resultado
            ]

    def obtener_detalle_de_propietario(self, id_caballo: int, id_usuario: int) -> Optional[dict]:
        with engine.connect() as connection:
            caballo = connection.execute(
                text("""
                    SELECT
                        c.id_caballo, c.nombre, c.sexo, c.fecha_nacimiento,
                        c.altura, c.color, c.ubicacion, c.ubicacion_texto,
                        c.ciudad, c.departamento, c.descripcion, c.disponibilidad,
                        c.raza_id_raza,
                        r.nombre AS raza,
                        p.id_publicacion,
                        p.precio_referencia
                    FROM caballo c
                    INNER JOIN raza r
                        ON c.raza_id_raza = r.id_raza
                    LEFT JOIN publicacion p
                        ON p.caballo_id_caballo = c.id_caballo
                        AND p.estado = 'Activa'
                    WHERE c.id_caballo = :id_caballo
                      AND c.usuario_id_usuario = :id_usuario
                      AND c.disponibilidad != 'Eliminado'
                """),
                {"id_caballo": id_caballo, "id_usuario": id_usuario},
            ).first()

            if caballo is None:
                return None

            fotos = listar_fotos(connection, id_caballo)

        return {
            "id_caballo": caballo.id_caballo,
            "nombre": caballo.nombre,
            "sexo": caballo.sexo,
            "fecha_nacimiento": caballo.fecha_nacimiento,
            "altura": float(caballo.altura),
            "color": caballo.color,
            "ubicacion": caballo.ubicacion,
            "ubicacion_texto": caballo.ubicacion_texto,
            "ciudad": caballo.ciudad,
            "departamento": caballo.departamento,
            "descripcion": caballo.descripcion,
            "disponibilidad": caballo.disponibilidad,
            "id_raza": caballo.raza_id_raza,
            "raza": caballo.raza,
            "id_publicacion": caballo.id_publicacion,
            "precio": _precio(caballo.precio_referencia),
            "fotos": fotos,
        }


def listar_fotos(connection, id_caballo: int) -> List[dict]:
    """Fotos de un caballo, la principal primero. Se comparte con las publicaciones."""
    resultado = connection.execute(
        text("""
            SELECT id_foto, ruta, es_principal, orden
            FROM foto_caballo
            WHERE id_caballo = :id_caballo
            ORDER BY es_principal DESC, orden ASC
        """),
        {"id_caballo": id_caballo},
    )

    return [
        {
            "id_foto": f.id_foto,
            "ruta": f"/{f.ruta}",
            "es_principal": bool(f.es_principal),
            "orden": f.orden,
        }
        for f in resultado
    ]
