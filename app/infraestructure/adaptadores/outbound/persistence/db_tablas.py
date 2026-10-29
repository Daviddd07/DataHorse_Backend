from datetime import date, datetime
from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infraestructure.adaptadores.outbound.persistence.db_conexion import Base


class RolModel(Base):
    __tablename__ = "rol"

    id_rol: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre_rol: Mapped[str] = mapped_column(String(80), nullable=False)


class UsuarioModel(Base):
    __tablename__ = "usuario"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rol_id_rol: Mapped[int] = mapped_column(ForeignKey("rol.id_rol"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    correo: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    contrasena: Mapped[str] = mapped_column("contraseña", String(255), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ubicacion: Mapped[str | None] = mapped_column(String(180), nullable=True)
    fecha_registro: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False)
    ubicacion_lat: Mapped[float | None] = mapped_column(Numeric(10, 8), nullable=True)
    ubicacion_lng: Mapped[float | None] = mapped_column(Numeric(11, 8), nullable=True)
    ubicacion_texto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ciudad: Mapped[str | None] = mapped_column(String(120), nullable=True)
    departamento: Mapped[str | None] = mapped_column(String(120), nullable=True)

    rol = relationship("RolModel")


class RazaModel(Base):
    __tablename__ = "raza"

    id_raza: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)


class CaballoModel(Base):
    __tablename__ = "caballo"

    id_caballo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_raza: Mapped[int] = mapped_column("raza_id_raza", ForeignKey("raza.id_raza"), nullable=False)
    id_propietario: Mapped[int] = mapped_column("usuario_id_usuario", ForeignKey("usuario.id_usuario"), nullable=False)
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


class PublicacionModel(Base):
    __tablename__ = "publicacion"

    id_publicacion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    caballo_id_caballo: Mapped[int] = mapped_column(ForeignKey("caballo.id_caballo"), nullable=False)
    usuario_id_usuario: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"), nullable=False)
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_publicacion: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False)
    precio_referencia: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    caballo = relationship("CaballoModel")
    usuario = relationship("UsuarioModel")
    
class FotoCaballoModel(Base):
    __tablename__ = "foto_caballo"

    id_foto: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_caballo: Mapped[int] = mapped_column(
        "id_caballo", ForeignKey("caballo.id_caballo", ondelete="CASCADE"), nullable=False
    )
    ruta: Mapped[str] = mapped_column(String(500), nullable=False)
    es_principal: Mapped[bool] = mapped_column(default=False, nullable=False)
    orden: Mapped[int] = mapped_column(default=0, nullable=False)
    fecha_subida: Mapped[date | None] = mapped_column(Date, nullable=True)

class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "usuario.id_usuario",
            ondelete="SET NULL",
            onupdate="CASCADE",
        ),
        nullable=True,
    )

    accion: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    modulo: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    resultado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    detalle: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    request_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    fecha_hora: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

