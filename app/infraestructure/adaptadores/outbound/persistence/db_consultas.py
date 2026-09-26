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