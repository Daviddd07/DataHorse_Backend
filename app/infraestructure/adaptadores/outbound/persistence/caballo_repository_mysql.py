from typing import List

from app.domain.entities.Caballo import Caballo
from app.domain.ports.out.caballo_repository_port import CaballoRepositoryPort
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import SessionLocal
from app.infraestructure.adaptadores.outbound.persistence.db_consultas import (
    insertar_caballo,
    obtener_caballos,
)


def _a_entidad(fila) -> Caballo:
    return Caballo(
        id_caballo=fila.id_caballo,
        id_raza=fila.id_raza,
        id_propietario=fila.id_propietario,
        nombre=fila.nombre,
        sexo=fila.sexo,
        fecha_nacimiento=fila.fecha_nacimiento,
        altura=float(fila.altura),
        color=fila.color,
        ubicacion=fila.ubicacion,
        descripcion=fila.descripcion,
        disponibilidad=fila.disponibilidad,
    )


class CaballoRepositoryMySQL(CaballoRepositoryPort):
    def create(self, caballo: Caballo) -> Caballo:
        db = SessionLocal()
        try:
            datos = {
                "id_raza": caballo.id_raza,
                "id_propietario": caballo.id_propietario,
                "nombre": caballo.nombre,
                "sexo": caballo.sexo,
                "fecha_nacimiento": caballo.fecha_nacimiento,
                "altura": caballo.altura,
                "color": caballo.color,
                "ubicacion": caballo.ubicacion,
                "descripcion": caballo.descripcion,
                "disponibilidad": caballo.disponibilidad,
            }
            fila = insertar_caballo(db, datos)
            return _a_entidad(fila)
        finally:
            db.close()

    def find_all(self) -> List[Caballo]:
        db = SessionLocal()
        try:
            filas = obtener_caballos(db)
            return [_a_entidad(f) for f in filas]
        finally:
            db.close()