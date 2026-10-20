import time

from app.infraestructure.adaptadores.outbound.persistence.db_conexion import engine
from app.domain.services.geocoding_service import GeocodingService
from sqlalchemy import text


def main():
    geocoding = GeocodingService()

    with engine.begin() as connection:
        caballos = connection.execute(
            text("""
                SELECT id_caballo, ubicacion
                FROM caballo
                WHERE departamento = 'Pendiente'
                  AND disponibilidad != 'Eliminado'
            """)
        ).fetchall()

        print(f"Caballos por migrar: {len(caballos)}")

        for caballo in caballos:
            print(f"  Geocodificando: {caballo.ubicacion}")

            datos = geocoding.geocodificar(caballo.ubicacion)

            if datos:
                connection.execute(
                    text("""
                        UPDATE caballo
                        SET ubicacion_lat = :lat,
                            ubicacion_lng = :lng,
                            ubicacion_texto = :texto,
                            ciudad = :ciudad,
                            departamento = :departamento
                        WHERE id_caballo = :id
                    """),
                    {
                        "lat": datos["lat"],
                        "lng": datos["lng"],
                        "texto": datos["texto"],
                        "ciudad": datos["ciudad"] or caballo.ubicacion,
                        "departamento": datos["departamento"] or "Sin departamento",
                        "id": caballo.id_caballo,
                    },
                )
                print(f"    OK: {datos['ciudad']}, {datos['departamento']}")
            else:
                print("    No encontrado, dejando valor actual")

            time.sleep(1.2)

    print("Migracion completa.")


if __name__ == "__main__":
    main()