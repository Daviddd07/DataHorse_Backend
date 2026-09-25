from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infraestructure.adaptadores.outbound.persistence.db_tablas import UsuarioModel


def insertar_usuario(db: Session, datos: dict) -> UsuarioModel:
    fila = UsuarioModel(**datos)
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


def obtener_usuario_por_correo(db: Session, correo: str) -> UsuarioModel | None:
    stmt = select(UsuarioModel).where(UsuarioModel.correo == correo)
    return db.execute(stmt).scalar_one_or_none()

def obtener_usuario_por_id(db: Session, id_usuario: int) -> UsuarioModel | None:
    stmt = select(UsuarioModel).where(UsuarioModel.id_usuario == id_usuario)
    return db.execute(stmt).scalar_one_or_none()