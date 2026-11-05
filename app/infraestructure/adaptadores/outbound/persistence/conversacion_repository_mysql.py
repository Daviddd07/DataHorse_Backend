from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.domain.entities.conversacion import (
    ESTADO_CONVERSACION_ACTIVA,
    ESTADO_MENSAJE_LEIDO,
    ESTADO_MENSAJE_NO_LEIDO,
    Conversacion,
    Mensaje,
)
from app.domain.ports.out.conversacion_repository_port import ConversacionRepositoryPort
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import engine


def _a_mensaje(fila) -> Mensaje:
    return Mensaje(
        id_mensaje=fila.id_mensaje,
        id_conversacion=fila.conversacion_id_conversacion,
        id_usuario=fila.usuario_id_usuario,
        contenido=fila.contenido,
        fecha_envio=fila.fecha_envio,
        estado_lectura=fila.estado_lectura,
    )


def _iso(valor) -> Optional[str]:
    return valor.isoformat() if valor is not None else None


def _foto_publica(ruta: Optional[str]) -> Optional[str]:
    # En la BD la ruta va sin '/' inicial; el frontend la pega a la URL del backend
    return f"/{ruta.lstrip('/')}" if ruta else None


class ConversacionRepositoryMySQL(ConversacionRepositoryPort):

    def obtener_dueno_publicacion_activa(self, id_publicacion: int) -> Optional[int]:
        with engine.connect() as connection:
            fila = connection.execute(
                text("""
                    SELECT usuario_id_usuario
                    FROM publicacion
                    WHERE id_publicacion = :id_publicacion
                      AND estado = 'Activa'
                """),
                {"id_publicacion": id_publicacion},
            ).first()
        return fila.usuario_id_usuario if fila is not None else None

    def buscar_id(self, id_publicacion: int, id_interesado: int) -> Optional[int]:
        with engine.connect() as connection:
            fila = connection.execute(
                text("""
                    SELECT id_conversacion
                    FROM conversacion
                    WHERE publicacion_id_publicacion = :id_publicacion
                      AND usuario_id_interesado = :id_interesado
                """),
                {"id_publicacion": id_publicacion, "id_interesado": id_interesado},
            ).first()
        return fila.id_conversacion if fila is not None else None

    def crear(self, id_publicacion: int, id_interesado: int, fecha: date) -> int:
        try:
            with engine.begin() as connection:
                resultado = connection.execute(
                    text("""
                        INSERT INTO conversacion
                            (fecha_creacion, estado, publicacion_id_publicacion, usuario_id_interesado)
                        VALUES (:fecha, :estado, :id_publicacion, :id_interesado)
                    """),
                    {
                        "fecha": fecha,
                        "estado": ESTADO_CONVERSACION_ACTIVA,
                        "id_publicacion": id_publicacion,
                        "id_interesado": id_interesado,
                    },
                )
            return int(resultado.lastrowid)
        except IntegrityError:
            # Dos solicitudes simultáneas: la clave única dejó pasar solo una.
            existente = self.buscar_id(id_publicacion, id_interesado)
            if existente is None:
                raise
            return existente

    def obtener(self, id_conversacion: int) -> Optional[Conversacion]:
        with engine.connect() as connection:
            fila = connection.execute(
                text("""
                    SELECT c.id_conversacion, c.publicacion_id_publicacion,
                           c.usuario_id_interesado, p.usuario_id_usuario AS id_vendedor,
                           p.titulo, ui.nombre AS nombre_interesado, uv.nombre AS nombre_vendedor
                    FROM conversacion c
                    INNER JOIN publicacion p
                        ON p.id_publicacion = c.publicacion_id_publicacion
                    INNER JOIN usuario ui ON ui.id_usuario = c.usuario_id_interesado
                    INNER JOIN usuario uv ON uv.id_usuario = p.usuario_id_usuario
                    WHERE c.id_conversacion = :id_conversacion
                """),
                {"id_conversacion": id_conversacion},
            ).first()
        if fila is None:
            return None
        return Conversacion(
            id_conversacion=fila.id_conversacion,
            id_publicacion=fila.publicacion_id_publicacion,
            id_interesado=fila.usuario_id_interesado,
            id_vendedor=fila.id_vendedor,
            nombre_interesado=fila.nombre_interesado,
            nombre_vendedor=fila.nombre_vendedor,
            titulo_publicacion=fila.titulo,
        )

    _SELECT_RESUMEN = """
        SELECT c.id_conversacion, c.publicacion_id_publicacion, c.fecha_creacion,
               p.titulo, p.usuario_id_usuario AS id_vendedor, uv.nombre AS nombre_vendedor,
               uv.foto_perfil AS foto_vendedor,
               c.usuario_id_interesado AS id_interesado, ui.nombre AS nombre_interesado,
               ui.foto_perfil AS foto_interesado,
               m.contenido AS ultimo_mensaje, m.fecha_envio AS fecha_ultimo_mensaje,
               m.usuario_id_usuario AS id_autor_ultimo,
               (SELECT COUNT(*)
                FROM mensaje nl
                WHERE nl.conversacion_id_conversacion = c.id_conversacion
                  AND nl.usuario_id_usuario <> :id_usuario
                  AND nl.estado_lectura = 'no_leido') AS no_leidos
        FROM conversacion c
        INNER JOIN publicacion p ON p.id_publicacion = c.publicacion_id_publicacion
        INNER JOIN usuario uv ON uv.id_usuario = p.usuario_id_usuario
        INNER JOIN usuario ui ON ui.id_usuario = c.usuario_id_interesado
        LEFT JOIN mensaje m ON m.id_mensaje = (
            SELECT MAX(m2.id_mensaje)
            FROM mensaje m2
            WHERE m2.conversacion_id_conversacion = c.id_conversacion
        )
    """

    @staticmethod
    def _a_resumen(fila, id_usuario: int) -> dict:
        soy_vendedor = fila.id_vendedor == id_usuario
        return {
            "id_conversacion": fila.id_conversacion,
            "id_publicacion": fila.publicacion_id_publicacion,
            "titulo_publicacion": fila.titulo,
            "soy_vendedor": soy_vendedor,
            "otro_usuario": {
                "id": fila.id_interesado if soy_vendedor else fila.id_vendedor,
                "nombre": fila.nombre_interesado if soy_vendedor else fila.nombre_vendedor,
                # Ruta pública de su foto de perfil (o None para mostrar su inicial)
                "foto_perfil": _foto_publica(fila.foto_interesado if soy_vendedor else fila.foto_vendedor),
            },
            "ultimo_mensaje": fila.ultimo_mensaje,
            "fecha_ultimo_mensaje": _iso(fila.fecha_ultimo_mensaje),
            "ultimo_mensaje_es_mio": fila.id_autor_ultimo == id_usuario,
            "no_leidos": int(fila.no_leidos or 0),
            "fecha_creacion": _iso(fila.fecha_creacion),
        }

    def obtener_resumen(self, id_conversacion: int, id_usuario: int) -> Optional[dict]:
        with engine.connect() as connection:
            fila = connection.execute(
                text(self._SELECT_RESUMEN + " WHERE c.id_conversacion = :id_conversacion"),
                {"id_conversacion": id_conversacion, "id_usuario": id_usuario},
            ).first()
        return self._a_resumen(fila, id_usuario) if fila is not None else None

    def listar_de_usuario(self, id_usuario: int) -> List[dict]:
        with engine.connect() as connection:
            filas = connection.execute(
                text(
                    self._SELECT_RESUMEN
                    + """
                    WHERE c.usuario_id_interesado = :id_usuario
                       OR p.usuario_id_usuario = :id_usuario
                    ORDER BY COALESCE(m.fecha_envio, c.fecha_creacion) DESC,
                             c.id_conversacion DESC
                    """
                ),
                {"id_usuario": id_usuario},
            )
            return [self._a_resumen(fila, id_usuario) for fila in filas]

    def listar_mensajes(self, id_conversacion: int, limite: int) -> List[Mensaje]:
        with engine.connect() as connection:
            filas = connection.execute(
                text("""
                    SELECT id_mensaje, conversacion_id_conversacion, usuario_id_usuario,
                           contenido, fecha_envio, estado_lectura
                    FROM mensaje
                    WHERE conversacion_id_conversacion = :id_conversacion
                    ORDER BY id_mensaje DESC
                    LIMIT :limite
                """),
                {"id_conversacion": id_conversacion, "limite": limite},
            )
            mensajes = [_a_mensaje(fila) for fila in filas]
        mensajes.reverse()
        return mensajes

    def contar_no_leidos(self, id_usuario: int) -> int:
        with engine.connect() as connection:
            total = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM mensaje m
                    INNER JOIN conversacion c
                        ON c.id_conversacion = m.conversacion_id_conversacion
                    INNER JOIN publicacion p
                        ON p.id_publicacion = c.publicacion_id_publicacion
                    WHERE (c.usuario_id_interesado = :id_usuario OR p.usuario_id_usuario = :id_usuario)
                      AND m.usuario_id_usuario <> :id_usuario
                      AND m.estado_lectura = :no_leido
                """),
                {"id_usuario": id_usuario, "no_leido": ESTADO_MENSAJE_NO_LEIDO},
            ).scalar()
        return int(total or 0)

    def marcar_leidos(self, id_conversacion: int, id_usuario: int) -> int:
        with engine.begin() as connection:
            resultado = connection.execute(
                text("""
                    UPDATE mensaje
                    SET estado_lectura = :leido
                    WHERE conversacion_id_conversacion = :id_conversacion
                      AND usuario_id_usuario <> :id_usuario
                      AND estado_lectura = :no_leido
                """),
                {
                    "leido": ESTADO_MENSAJE_LEIDO,
                    "no_leido": ESTADO_MENSAJE_NO_LEIDO,
                    "id_conversacion": id_conversacion,
                    "id_usuario": id_usuario,
                },
            )
        return resultado.rowcount

    def guardar_mensaje(
        self, id_conversacion: int, id_usuario: int, contenido: str, fecha_envio: datetime
    ) -> Mensaje:
        with engine.begin() as connection:
            resultado = connection.execute(
                text("""
                    INSERT INTO mensaje
                        (contenido, fecha_envio, estado_lectura,
                         conversacion_id_conversacion, usuario_id_usuario)
                    VALUES (:contenido, :fecha_envio, :estado, :id_conversacion, :id_usuario)
                """),
                {
                    "contenido": contenido,
                    "fecha_envio": fecha_envio,
                    "estado": ESTADO_MENSAJE_NO_LEIDO,
                    "id_conversacion": id_conversacion,
                    "id_usuario": id_usuario,
                },
            )
        return Mensaje(
            id_mensaje=int(resultado.lastrowid),
            id_conversacion=id_conversacion,
            id_usuario=id_usuario,
            contenido=contenido,
            fecha_envio=fecha_envio,
            estado_lectura=ESTADO_MENSAJE_NO_LEIDO,
        )
