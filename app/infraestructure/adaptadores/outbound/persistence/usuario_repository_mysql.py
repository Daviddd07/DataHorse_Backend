from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domain.entities.Usuario import Usuario
from app.domain.exceptions import CorreoYaRegistradoError
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort

from app.infraestructure.adaptadores.outbound.persistence.db_conexion import (
    SessionLocal,
)

from app.infraestructure.adaptadores.outbound.persistence.db_tablas import (
    UsuarioTabla,
)


class UsuarioRepositoryMySQL(UsuarioRepositoryPort):

    def find_by_email(self, correo: str) -> Optional[Usuario]:
        with SessionLocal() as db:

            stmt = select(UsuarioTabla).where(
                UsuarioTabla.correo == correo
            )

            usuario_db = db.scalar(stmt)

            if usuario_db is None:
                return None

            return self._to_domain(usuario_db)

    def create(self, usuario: Usuario) -> Usuario:
        with SessionLocal() as db:

            # Verificar si el correo ya existe
            existente = db.scalar(
                select(UsuarioTabla).where(
                    UsuarioTabla.correo == usuario.correo
                )
            )

            if existente is not None:
                raise CorreoYaRegistradoError()

            # Convertir la entidad Usuario al modelo de MySQL
            usuario_db = UsuarioTabla(
                id_rol=usuario.id_rol,
                nombre=usuario.nombre,
                correo=usuario.correo,
                contrasena=usuario.contrasena,
                telefono=usuario.telefono,
                ubicacion=usuario.ubicacion,
                fecha_registro=usuario.fecha_registro,
                estado=usuario.estado
            )

            db.add(usuario_db)

            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                raise CorreoYaRegistradoError()

            db.refresh(usuario_db)

            return self._to_domain(usuario_db)

    @staticmethod
    def _to_domain(usuario_db: UsuarioTabla) -> Usuario:
        return Usuario(
            id_usuario=usuario_db.id_usuario,
            id_rol=usuario_db.id_rol,
            nombre=usuario_db.nombre,
            correo=usuario_db.correo,
            contrasena=usuario_db.contrasena,
            telefono=usuario_db.telefono,
            ubicacion=usuario_db.ubicacion,
            fecha_registro=usuario_db.fecha_registro,
            estado=usuario_db.estado
        )