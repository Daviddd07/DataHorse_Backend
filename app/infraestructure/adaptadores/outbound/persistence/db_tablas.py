from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infraestructure.adaptadores.outbound.persistence.db_conexion import Base


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


class RazaModel(Base):
    __tablename__ = "Raza"

    id_raza: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)


class CaballoModel(Base):
    __tablename__ = "Caballo"

    id_caballo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_raza: Mapped[int] = mapped_column("raza_id_raza", ForeignKey("Raza.id_raza"), nullable=False)
    id_propietario: Mapped[int] = mapped_column("usuario_id_usuario", ForeignKey("Usuario.id_usuario"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    sexo: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha_nacimiento: Mapped[date] = mapped_column(Date, nullable=False)
    altura: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    color: Mapped[str] = mapped_column(String(60), nullable=False)
    ubicacion: Mapped[str] = mapped_column(String(180), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    disponibilidad: Mapped[str] = mapped_column(String(30), nullable=False)

    raza = relationship("RazaModel")
    propietario = relationship("UsuarioModel")