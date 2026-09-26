from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domain.entities.Usuario import Usuario
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort
from app.application.use_cases.registrar_use_case import EmailAlreadyExistsError

from app.infraestructure.adaptadores.outbound.persistence.db_conexion import (
    SessionLocal,
)

from app.infraestructure.adaptadores.outbound.persistence.db_tablas import (
    UsuarioModel,
)


class UsuarioRepositoryMySQL(UsuarioRepositoryPort):

    def find_by_email(self, correo: str) -> Optional[Usuario]:
        with SessionLocal() as db:
            stmt = select(UsuarioModel).where(
                UsuarioModel.correo == correo
            )

            usuario_db = db.scalar(stmt)

            if usuario_db is None:
                return None

            return self._to_domain(usuario_db)

    def find_by_id(self, id_usuario: int) -> Optional[Usuario]:
        with SessionLocal() as db:
            stmt = select(UsuarioModel).where(
                UsuarioModel.id_usuario == id_usuario
            )

            usuario_db = db.scalar(stmt)

            if usuario_db is None:
                return None

            return self._to_domain(usuario_db)

    def create(self, usuario: Usuario) -> Usuario:
        with SessionLocal() as db:

            existente = db.scalar(
                select(UsuarioModel).where(
                    UsuarioModel.correo == usuario.correo
                )
            )

            if existente is not None:
                raise EmailAlreadyExistsError()

            usuario_db = UsuarioModel(
                rol_id_rol=usuario.id_rol,
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
                raise EmailAlreadyExistsError()

            db.refresh(usuario_db)

            return self._to_domain(usuario_db)

    @staticmethod
    def _to_domain(usuario_db: UsuarioModel) -> Usuario:
        return Usuario(
            id_usuario=usuario_db.id_usuario,
            id_rol=usuario_db.rol_id_rol,
            nombre=usuario_db.nombre,
            correo=usuario_db.correo,
            contrasena=usuario_db.contrasena,
            telefono=usuario_db.telefono,
            ubicacion=usuario_db.ubicacion,
            fecha_registro=usuario_db.fecha_registro,
            estado=usuario_db.estado
        )