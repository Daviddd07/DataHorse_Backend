<<<<<<< HEAD
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infraestructure.adaptadores.outbound.persistence.db_tablas import UsuarioTabla


def buscar_usuario_por_correo(
    db: Session,
    correo: str
) -> UsuarioTabla | None:

    stmt = select(UsuarioTabla).where(
        UsuarioTabla.correo == correo
    )

    return db.scalar(stmt)


def crear_usuario(
    db: Session,
    nombre: str,
    correo: str,
    contrasena: str,
    rol_id: int,
    telefono: str | None = None,
    ubicacion: str | None = None
) -> UsuarioTabla:

    usuario = UsuarioTabla(
        nombre=nombre,
        correo=correo,
        contrasena=contrasena,
        telefono=telefono,
        ubicacion=ubicacion,
        fecha_registro=date.today(),
        estado="ACTIVO",
        rol_id_rol=rol_id
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    return usuario
=======
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
>>>>>>> 7c3e33babdff51df967880f35799735231fe1b21
