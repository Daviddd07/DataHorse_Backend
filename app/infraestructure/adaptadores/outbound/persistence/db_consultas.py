from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infraestructure.adaptadores.outbound.persistence.db_tablas import (
    CaballoModel,
    PublicacionModel,
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


def insertar_publicacion(db: Session, datos: dict) -> PublicacionModel:
    fila = PublicacionModel(**datos)
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila


def obtener_publicaciones_activas(db: Session) -> list[dict]:
    stmt = (
        select(
            PublicacionModel.id_publicacion,
            PublicacionModel.titulo,
            PublicacionModel.precio_referencia,
            PublicacionModel.estado,
            PublicacionModel.fecha_publicacion,
            CaballoModel.id_caballo,
            CaballoModel.nombre,
            CaballoModel.sexo,
            CaballoModel.color,
            CaballoModel.ubicacion,
            RazaModel.nombre.label("raza_nombre"),
        )
        .join(CaballoModel, PublicacionModel.caballo_id_caballo == CaballoModel.id_caballo)
        .join(RazaModel, CaballoModel.id_raza == RazaModel.id_raza)
        .where(PublicacionModel.estado == "Activa")
        .where(CaballoModel.sexo == "Macho")
    )

    filas = db.execute(stmt).all()

    return [
        {
            "id_publicacion": f.id_publicacion,
            "id_caballo": f.id_caballo,
            "titulo": f.titulo,
            "nombre": f.nombre,
            "raza": f.raza_nombre,
            "sexo": f.sexo,
            "color": f.color,
            "ubicacion": f.ubicacion,
            "precio_referencia": float(f.precio_referencia),
            "estado": f.estado,
            "fecha_publicacion": f.fecha_publicacion,
        }
        for f in filas
    ]