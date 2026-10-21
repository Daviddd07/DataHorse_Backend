import time

from app.infraestructure.adaptadores.outbound.persistence.db_conexion import engine
from app.domain.services.geocoding_service import GeocodingService
from sqlalchemy import text


def main():
    geocoding = GeocodingService()

    with engine.begin() as connection:
        # Buscamos usuarios que tengan texto en ubicacion pero que aun no tengan ciudad
        usuarios = connection.execute(
            text("""
                SELECT id_usuario, ubicacion
                FROM usuario
                WHERE ubicacion IS NOT NULL
                  AND ubicacion != ''
                  AND ciudad IS NULL
            """)
        ).fetchall()

        print(f"Usuarios por migrar: {len(usuarios)}")

        for usuario in usuarios:
            print(f"  Geocodificando: {usuario.ubicacion}")

            datos = geocoding.geocodificar(usuario.ubicacion)

            if datos:
                connection.execute(
                    text("""
                        UPDATE usuario
                        SET ubicacion_lat = :lat,
                            ubicacion_lng = :lng,
                            ubicacion_texto = :texto,
                            ciudad = :ciudad,
                            departamento = :departamento
                        WHERE id_usuario = :id
                    """),
                    {
                        "lat": datos["lat"],
                        "lng": datos["lng"],
                        "texto": datos["texto"],
                        "ciudad": datos["ciudad"] or usuario.ubicacion,
                        "departamento": datos["departamento"] or "Sin departamento",
                        "id": usuario.id_usuario,
                    },
                )
                print(f"    OK: {datos['ciudad']}, {datos['departamento']}")
            else:
                print("    No encontrado, dejando valor actual")

            # Respetar el limite de 1 peticion por segundo de Nominatim
            time.sleep(1.2)

    print("Migracion de usuarios completa.")


if __name__ == "__main__":
    main()