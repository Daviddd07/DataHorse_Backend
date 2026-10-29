from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infraestructure.adaptadores.outbound.persistence.db_tablas import RazaModel


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
