from typing import List, Optional

from sqlalchemy import text

from app.domain.ports.out.ubicacion_consultas_port import UbicacionConsultasPort
from app.infraestructure.adaptadores.outbound.persistence.db_conexion import engine


class UbicacionConsultasMySQL(UbicacionConsultasPort):
    """Departamentos y ciudades donde hay caballos registrados."""

    def listar_departamentos(self) -> List[str]:
        with engine.connect() as connection:
            resultado = connection.execute(
                text("""
                    SELECT DISTINCT departamento
                    FROM caballo
                    WHERE departamento IS NOT NULL
                      AND departamento != 'Sin departamento'
                      AND disponibilidad != 'Eliminado'
                    ORDER BY departamento ASC
                """)
            )
            return [fila.departamento for fila in resultado]

    def listar_ciudades(self, departamento: Optional[str] = None) -> List[str]:
        with engine.connect() as connection:
            resultado = connection.execute(
                text("""
                    SELECT DISTINCT ciudad
                    FROM caballo
                    WHERE ciudad IS NOT NULL
                      AND ciudad != 'Sin ciudad'
                      AND (:departamento IS NULL OR departamento = :departamento)
                      AND disponibilidad != 'Eliminado'
                    ORDER BY ciudad ASC
                """),
                {"departamento": departamento or None},
            )
            return [fila.ciudad for fila in resultado]
