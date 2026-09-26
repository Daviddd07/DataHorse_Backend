from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infraestructure.adaptadores.outbound.persistence.db_tablas import (
    CaballoModel,
    RazaModel,
    UsuarioModel,
)


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


def insertar_raza(db: Session, datos: dict) -> RazaModel:
    fila = RazaModel(**datos)
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


def obtener_razas(db: Session) -> list[RazaModel]:
    stmt = select(RazaModel).order_by(RazaModel.nombre)
    return list(db.execute(stmt).scalars().all())


def obtener_raza_por_id(db: Session, id_raza: int) -> RazaModel | None:
    stmt = select(RazaModel).where(RazaModel.id_raza == id_raza)
    return db.execute(stmt).scalar_one_or_none()


def insertar_caballo(db: Session, datos: dict) -> CaballoModel:
    fila = CaballoModel(**datos)
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


def obtener_caballos(db: Session) -> list[CaballoModel]:
    stmt = select(CaballoModel)
    return list(db.execute(stmt).scalars().all())