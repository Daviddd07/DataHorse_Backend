
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.infraestructure.adaptadores.outbound.persistence import db_consultas


def crear_db():
    return MagicMock()


def probar_insercion(nombre_funcion, nombre_modelo):
    db = crear_db()
    datos = {"correo": "prueba@test.com"}
    fila = object()

    with patch.object(
        db_consultas, nombre_modelo, return_value=fila
    ) as modelo:
        resultado = getattr(db_consultas, nombre_funcion)(db, datos)

    modelo.assert_called_once_with(**datos)
    db.add.assert_called_once_with(fila)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(fila)
    assert resultado is fila


def test_insertar_usuario():
    probar_insercion("insertar_usuario", "UsuarioModel")


def test_insertar_raza():
    probar_insercion("insertar_raza", "RazaModel")


def test_insertar_caballo():
    probar_insercion("insertar_caballo", "CaballoModel")


def test_insertar_publicacion():
    probar_insercion("insertar_publicacion", "PublicacionModel")


def test_obtener_usuario_por_correo():
    db = crear_db()
    usuario = object()
    db.execute.return_value.scalar_one_or_none.return_value = usuario

    resultado = db_consultas.obtener_usuario_por_correo(
        db, "prueba@test.com"
    )

    assert resultado is usuario
    db.execute.assert_called_once()


def test_obtener_usuario_por_id():
    db = crear_db()
    usuario = object()
    db.execute.return_value.scalar_one_or_none.return_value = usuario

    resultado = db_consultas.obtener_usuario_por_id(db, 1)

    assert resultado is usuario


def test_obtener_razas():
    db = crear_db()
    razas = [object(), object()]
    db.execute.return_value.scalars.return_value.all.return_value = razas

    resultado = db_consultas.obtener_razas(db)

    assert resultado == razas


def test_obtener_raza_por_id():
    db = crear_db()
    raza = object()
    db.execute.return_value.scalar_one_or_none.return_value = raza

    resultado = db_consultas.obtener_raza_por_id(db, 1)

    assert resultado is raza


def test_obtener_caballos():
    db = crear_db()
    caballos = [object(), object()]
    db.execute.return_value.scalars.return_value.all.return_value = caballos

    resultado = db_consultas.obtener_caballos(db)

    assert resultado == caballos


def test_obtener_publicaciones_activas_con_foto():
    db = crear_db()
    fila = SimpleNamespace(
        id_publicacion=1,
        id_caballo=2,
        titulo="Caballo de prueba",
        nombre="Relámpago",
        raza_nombre="Criollo",
        sexo="Macho",
        color="Negro",
        ubicacion="Cundinamarca",
        precio_referencia=1500000,
        estado="Activa",
        fecha_publicacion=None,
        foto_ruta="fotos/caballo.jpg",
    )
    db.execute.return_value.all.return_value = [fila]

    resultado = db_consultas.obtener_publicaciones_activas(db)

    assert len(resultado) == 1
    assert resultado[0]["foto_principal"] == "/fotos/caballo.jpg"
    assert resultado[0]["precio_referencia"] == 1500000.0


def test_obtener_publicaciones_activas_sin_foto():
    db = crear_db()
    fila = SimpleNamespace(
        id_publicacion=1,
        id_caballo=2,
        titulo="Caballo de prueba",
        nombre="Relámpago",
        raza_nombre="Criollo",
        sexo="Macho",
        color="Negro",
        ubicacion="Cundinamarca",
        precio_referencia=1500000,
        estado="Activa",
        fecha_publicacion=None,
        foto_ruta=None,
    )
    db.execute.return_value.all.return_value = [fila]

    resultado = db_consultas.obtener_publicaciones_activas(db)

    assert resultado[0]["foto_principal"] is None


def test_obtener_publicaciones_activas_sin_resultados():
    db = crear_db()
    db.execute.return_value.all.return_value = []

    resultado = db_consultas.obtener_publicaciones_activas(db)

    assert resultado == []
