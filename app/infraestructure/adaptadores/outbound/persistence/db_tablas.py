<<<<<<< HEAD
from datetime import date

from sqlalchemy import Integer, String, Date
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
=======
﻿from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RolModel(Base):
    __tablename__ = "Rol"

    id_rol: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre_rol: Mapped[str] = mapped_column(String(80), nullable=False)


class UsuarioModel(Base):
    __tablename__ = "Usuario"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rol_id_rol: Mapped[int] = mapped_column(ForeignKey("Rol.id_rol"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    correo: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    contrasena: Mapped[str] = mapped_column("contraseña", String(255), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ubicacion: Mapped[str | None] = mapped_column(String(180), nullable=True)
    fecha_registro: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False)

    rol = relationship("RolModel")
>>>>>>> 7c3e33babdff51df967880f35799735231fe1b21
