import json
from dataclasses import asdict
from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import text

from app.domain.entities.compatibilidad import (
    EjemplarEvaluado,
    EvaluacionGuardada,
    ResultadoCompatibilidad,
)
from app.domain.entities.descendencia import Descendencia
from app.domain.ports.out.compatibilidad_repository_port import CompatibilidadRepositoryPort
from app.infraestructure.adaptadores.outbound.persistence.caballo_repository_mysql import (
    obtener_descendencia,
)
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import engine


def _float_o_none(valor) -> Optional[float]:
    return float(valor) if valor is not None else None


def _como_utc(fecha: datetime) -> datetime:
    """La BD guarda creado_en en UTC sin zona; se marca para que el navegador la convierta bien."""
    return fecha.replace(tzinfo=timezone.utc)


class CompatibilidadRepositoryMySQL(CompatibilidadRepositoryPort):

    def obtener_ejemplar(self, id_caballo: int) -> Optional[EjemplarEvaluado]:
        with engine.connect() as connection:
            fila = connection.execute(
                text("""
                    SELECT
                        c.id_caballo, c.raza_id_raza, c.usuario_id_usuario,
                        c.nombre, c.sexo, c.fecha_nacimiento, c.altura, c.color,
                        c.descripcion, c.disponibilidad, c.ciudad, c.departamento,
                        c.ubicacion_lat, c.ubicacion_lng,
                        r.nombre AS raza,
                        u.nombre AS propietario,
                        EXISTS (
                            SELECT 1 FROM publicacion p
                            WHERE p.caballo_id_caballo = c.id_caballo
                              AND p.estado = 'Activa'
                        ) AS publicado
                    FROM caballo c
                    INNER JOIN raza r ON c.raza_id_raza = r.id_raza
                    INNER JOIN usuario u ON c.usuario_id_usuario = u.id_usuario
                    WHERE c.id_caballo = :id_caballo
                """),
                {"id_caballo": id_caballo},
            ).first()

            if fila is None:
                return None

            descendencia = obtener_descendencia(connection, id_caballo)

        return EjemplarEvaluado(
            id_caballo=fila.id_caballo,
            id_raza=fila.raza_id_raza,
            id_propietario=fila.usuario_id_usuario,
            nombre=fila.nombre,
            sexo=fila.sexo,
            raza=fila.raza,
            fecha_nacimiento=fila.fecha_nacimiento,
            altura=float(fila.altura),
            color=fila.color,
            descripcion=fila.descripcion,
            disponibilidad=fila.disponibilidad,
            propietario=fila.propietario,
            publicado=bool(fila.publicado),
            ciudad=fila.ciudad,
            departamento=fila.departamento,
            ubicacion_lat=_float_o_none(fila.ubicacion_lat),
            ubicacion_lng=_float_o_none(fila.ubicacion_lng),
            descendencia=Descendencia(**descendencia) if descendencia else None,
        )

    def porcentaje_razas(self, id_raza_yegua: int, id_raza_caballo: int) -> Optional[float]:
        with engine.connect() as connection:
            porcentaje = connection.execute(
                text("""
                    SELECT porcentaje_compatibilidad
                    FROM compatibilidad_razas
                    WHERE raza_yegua_id = :yegua AND raza_caballo_id = :caballo
                """),
                {"yegua": id_raza_yegua, "caballo": id_raza_caballo},
            ).scalar()

        return _float_o_none(porcentaje)

    def buscar_resultado(
        self, id_caballo: int, id_yegua: int, huella: str
    ) -> Optional[ResultadoCompatibilidad]:
        with engine.connect() as connection:
            fila = connection.execute(
                text("""
                    SELECT resultado, modelo
                    FROM solicitudcompatibilidad
                    WHERE caballo_id_caballo = :caballo
                      AND yegua_id_caballo = :yegua
                      AND huella_datos = :huella
                    ORDER BY id_solicitud DESC
                    LIMIT 1
                """),
                {"caballo": id_caballo, "yegua": id_yegua, "huella": huella},
            ).first()

        if fila is None:
            return None

        return ResultadoCompatibilidad(**json.loads(fila.resultado), modelo=fila.modelo or "")

    def contar_evaluaciones_desde(self, id_usuario: int, desde: datetime) -> int:
        with engine.connect() as connection:
            total = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM solicitudcompatibilidad
                    WHERE usuario_id_usuario = :id_usuario
                      AND creado_en >= :desde
                """),
                {"id_usuario": id_usuario, "desde": desde},
            ).scalar()

        return int(total or 0)

    def guardar(
        self,
        id_usuario: int,
        id_caballo: int,
        id_yegua: int,
        huella: str,
        fecha: date,
        resultado: ResultadoCompatibilidad,
    ) -> int:
        datos_ia = {k: v for k, v in asdict(resultado).items() if k != "modelo"}

        with engine.begin() as connection:
            id_solicitud = int(
                connection.execute(
                    text("""
                        INSERT INTO solicitudcompatibilidad (
                            fecha, resultado, usuario_id_usuario, caballo_id_caballo,
                            yegua_id_caballo, huella_datos, modelo
                        )
                        VALUES (:fecha, :resultado, :usuario, :caballo, :yegua, :huella, :modelo)
                    """),
                    {
                        "fecha": fecha,
                        "resultado": json.dumps(datos_ia, ensure_ascii=False),
                        "usuario": id_usuario,
                        "caballo": id_caballo,
                        "yegua": id_yegua,
                        "huella": huella,
                        "modelo": resultado.modelo,
                    },
                ).lastrowid
            )

            connection.execute(
                text("""
                    INSERT INTO resultadocompatibilidad (
                        puntuacion, raza_puntos, madurez_puntos, altura_puntos,
                        ubicacion_puntos, otros_puntos, nivel_confianza, resumen_cria,
                        solicitudcompatibilidad_id_solicitud, caballo_id_caballo
                    )
                    VALUES (
                        :puntuacion, :raza, :madurez, :altura,
                        :ubicacion, :otros, :confianza, :resumen,
                        :id_solicitud, :caballo
                    )
                """),
                {
                    "puntuacion": resultado.puntuacion,
                    "raza": resultado.raza_puntos,
                    "madurez": resultado.madurez_puntos,
                    "altura": resultado.altura_puntos,
                    "ubicacion": resultado.ubicacion_puntos,
                    "otros": resultado.otros_puntos,
                    "confianza": resultado.nivel_confianza,
                    "resumen": resultado.resumen_cria,
                    "id_solicitud": id_solicitud,
                    "caballo": id_caballo,
                },
            )

        return id_solicitud

    def listar_de_usuario(self, id_usuario: int) -> List[dict]:
        with engine.connect() as connection:
            filas = connection.execute(
                text("""
                    SELECT
                        s.id_solicitud, s.creado_en,
                        r.puntuacion, r.nivel_confianza,
                        c.id_caballo AS caballo_id, c.nombre AS caballo_nombre,
                        rc.nombre AS caballo_raza, uc.nombre AS caballo_propietario,
                        y.id_caballo AS yegua_id, y.nombre AS yegua_nombre,
                        ry.nombre AS yegua_raza, uy.nombre AS yegua_propietario
                    FROM solicitudcompatibilidad s
                    INNER JOIN resultadocompatibilidad r
                        ON r.solicitudcompatibilidad_id_solicitud = s.id_solicitud
                    INNER JOIN caballo c ON c.id_caballo = s.caballo_id_caballo
                    INNER JOIN raza rc ON rc.id_raza = c.raza_id_raza
                    INNER JOIN usuario uc ON uc.id_usuario = c.usuario_id_usuario
                    INNER JOIN caballo y ON y.id_caballo = s.yegua_id_caballo
                    INNER JOIN raza ry ON ry.id_raza = y.raza_id_raza
                    INNER JOIN usuario uy ON uy.id_usuario = y.usuario_id_usuario
                    WHERE s.usuario_id_usuario = :id_usuario
                    ORDER BY s.creado_en DESC, s.id_solicitud DESC
                """),
                {"id_usuario": id_usuario},
            )

            return [
                {
                    "id_solicitud": f.id_solicitud,
                    "fecha": _como_utc(f.creado_en),
                    "puntuacion": round(float(f.puntuacion)),  # DECIMAL(5,2) en la BD
                    "nivel_confianza": f.nivel_confianza,
                    "caballo": {
                        "id_caballo": f.caballo_id,
                        "nombre": f.caballo_nombre,
                        "raza": f.caballo_raza,
                        "propietario": f.caballo_propietario,
                    },
                    "yegua": {
                        "id_caballo": f.yegua_id,
                        "nombre": f.yegua_nombre,
                        "raza": f.yegua_raza,
                        "propietario": f.yegua_propietario,
                    },
                }
                for f in filas
            ]

    def obtener_evaluacion(self, id_solicitud: int) -> Optional[EvaluacionGuardada]:
        with engine.connect() as connection:
            fila = connection.execute(
                text("""
                    SELECT
                        id_solicitud, usuario_id_usuario, caballo_id_caballo,
                        yegua_id_caballo, creado_en, resultado, modelo
                    FROM solicitudcompatibilidad
                    WHERE id_solicitud = :id_solicitud
                      AND yegua_id_caballo IS NOT NULL
                """),
                {"id_solicitud": id_solicitud},
            ).first()

        if fila is None:
            return None

        return EvaluacionGuardada(
            id_solicitud=fila.id_solicitud,
            id_usuario=fila.usuario_id_usuario,
            id_caballo=fila.caballo_id_caballo,
            id_yegua=fila.yegua_id_caballo,
            creado_en=_como_utc(fila.creado_en),
            resultado=ResultadoCompatibilidad(**json.loads(fila.resultado), modelo=fila.modelo or ""),
        )
