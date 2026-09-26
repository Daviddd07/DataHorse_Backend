from typing import Optional

from app.domain.entities.Usuario import Usuario
from app.domain.exceptions import CorreoYaRegistradoError
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import SessionLocal
from app.infraestructure.adaptadores.outbound.persistence.db_consultas import (
    insertar_usuario,
    obtener_usuario_por_correo,
    obtener_usuario_por_id,
)


def _a_entidad(fila) -> Usuario:
    return Usuario(
        id_usuario=fila.id_usuario,
        id_rol=fila.rol_id_rol,
        nombre=fila.nombre,
        correo=fila.correo,
        contrasena=fila.contrasena,
        telefono=fila.telefono,
        ubicacion=fila.ubicacion,
        fecha_registro=fila.fecha_registro,
        estado=fila.estado,
    )


class UsuarioRepositoryMySQL(UsuarioRepositoryPort):
    def create(self, usuario: Usuario) -> Usuario:
        db = SessionLocal()
        try:
            datos = {
                "rol_id_rol": usuario.id_rol,
                "nombre": usuario.nombre,
                "correo": usuario.correo,
                "contrasena": usuario.contrasena,
                "telefono": usuario.telefono,
                "ubicacion": usuario.ubicacion,
                "fecha_registro": usuario.fecha_registro,
                "estado": usuario.estado,
            }
            try:
                fila = insertar_usuario(db, datos)
            except Exception:
                db.rollback()
                if obtener_usuario_por_correo(db, usuario.correo):
                    raise CorreoYaRegistradoError()
                raise
            return _a_entidad(fila)
        finally:
            db.close()

    def find_by_email(self, correo: str) -> Optional[Usuario]:
        db = SessionLocal()
        try:
            fila = obtener_usuario_por_correo(db, correo)
            return _a_entidad(fila) if fila else None
        finally:
            db.close()

    def find_by_id(self, id_usuario: int) -> Optional[Usuario]:
        db = SessionLocal()
        try:
            fila = obtener_usuario_por_id(db, id_usuario)
            return _a_entidad(fila) if fila else None
        finally:
            db.close()