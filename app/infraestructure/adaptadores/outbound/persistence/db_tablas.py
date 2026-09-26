from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infraestructure.adaptadores.outbound.persistence.db_conexion import Base


class UsuarioTabla(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    nombre: Mapped[str] = mapped_column(
        String(120),
        nullable=False
    )

    correo: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
        unique=True
    )

    contrasena: Mapped[str] = mapped_column(
        "contraseña",
        String(255),
        nullable=False
    )

    telefono: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    ubicacion: Mapped[str | None] = mapped_column(
        String(180),
        nullable=True
    )

    fecha_registro: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    estado: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    id_rol: Mapped[int] = mapped_column(
        "rol_id_rol",
        Integer,
        nullable=False
    )