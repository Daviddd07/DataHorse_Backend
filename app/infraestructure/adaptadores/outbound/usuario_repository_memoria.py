from dataclasses import asdict, fields
from typing import Optional

from sqlalchemy import select, inspect
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

            # Verificar si el correo ya está registrado
            existente = db.scalar(
                select(UsuarioTabla).where(
                    UsuarioTabla.correo == usuario.correo
                )
            )

            if existente is not None:
                raise CorreoYaRegistradoError()

            # Convertir el dataclass Usuario en diccionario
            datos = asdict(usuario)

            # Obtener los atributos válidos del modelo SQLAlchemy
            columnas = {
                atributo.key
                for atributo in inspect(UsuarioTabla).column_attrs
            }

            # Solo mandar a MySQL campos que existan en la tabla
            datos_bd = {
                clave: valor
                for clave, valor in datos.items()
                if clave in columnas
                and not (clave == "id_usuario" and valor is None)
            }

            usuario_db = UsuarioTabla(**datos_bd)

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

        datos = {}

        for campo in fields(Usuario):

            if hasattr(usuario_db, campo.name):
                datos[campo.name] = getattr(
                    usuario_db,
                    campo.name
                )

        return Usuario(**datos)