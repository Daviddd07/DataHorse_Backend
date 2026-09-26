from typing import List, Optional

from app.domain.entities.Raza import Raza
from app.domain.ports.out.raza_repository_port import RazaRepositoryPort
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import SessionLocal
from app.infraestructure.adaptadores.outbound.persistence.db_consultas import (
    insertar_raza,
    obtener_raza_por_id,
    obtener_razas,
)


def _a_entidad(fila) -> Raza:
    return Raza(id_raza=fila.id_raza, nombre=fila.nombre, descripcion=fila.descripcion)


class RazaRepositoryMySQL(RazaRepositoryPort):
    def find_all(self) -> List[Raza]:
        db = SessionLocal()
        try:
            filas = obtener_razas(db)
            return [_a_entidad(f) for f in filas]
        finally:
            db.close()

    def find_by_id(self, id_raza: int) -> Optional[Raza]:
        db = SessionLocal()
        try:
            fila = obtener_raza_por_id(db, id_raza)
            return _a_entidad(fila) if fila else None
        finally:
            db.close()

    def create(self, raza: Raza) -> Raza:
        db = SessionLocal()
        try:
            datos = {"nombre": raza.nombre, "descripcion": raza.descripcion}
            fila = insertar_raza(db, datos)
            return _a_entidad(fila)
        finally:
            db.close()