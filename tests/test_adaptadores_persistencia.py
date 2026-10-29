from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from conftest import fila, resultado

from app.domain.entities.Caballo import Caballo
from app.domain.ports.out.caballo_repository_port import (
    CaballoRegistrado,
    CambiosPublicacion,
    NuevaPublicacion,
)
from app.infraestructure.adaptadores.outbound.persistence import (
    audit_log_service,
    caballo_repository_mysql as caballos,
    codigo_verificacion_repository_mysql as codigos,
    favorito_repository_mysql as favoritos,
    publicacion_consultas_mysql as publicaciones,
    ubicacion_consultas_mysql as ubicaciones,
    usuario_google_repository_mysql as google,
    usuario_repository_mysql as usuarios,
)

FOTO = fila(id_foto=1, ruta="uploads/a.jpg", es_principal=1, orden=0)


def caballo(**cambios):
    datos = dict(
        id_caballo=5, id_raza=1, id_propietario=10, nombre="Lucero", sexo="Macho",
        fecha_nacimiento=date(2020, 1, 1), altura=1.6, color="Castaño",
        ubicacion="Bogotá", descripcion="desc", disponibilidad="Disponible",
    )
    datos.update(cambios)
    return Caballo(**datos)


def params(conexion, llamada):
    return conexion.execute.call_args_list[llamada].args[1]


# ======================================================
# CABALLOS (escritura)
# ======================================================

@pytest.mark.parametrize(("encontrado", "esperado"), [(fila(id_caballo=5), True), (None, False)])
def test_caballo_existe(motor_falso, encontrado, esperado):
    motor_falso(caballos, resultado(first=encontrado))

    assert caballos.CaballoRepositoryMySQL().existe(5) is esperado


def test_obtener_de_propietario_mapea_entidad(motor_falso):
    motor_falso(caballos, resultado(first=fila(
        id_caballo=5, raza_id_raza=1, usuario_id_usuario=10, nombre="Lucero",
        sexo="Macho", fecha_nacimiento=date(2020, 1, 1), altura="1.60",
        color="Castaño", ubicacion="Bogotá", descripcion="d", disponibilidad="Eliminado",
        ubicacion_lat=4.6, ubicacion_lng=-74.0, ubicacion_texto="Bogotá",
        ciudad="Bogotá", departamento="Cundinamarca",
    )))

    entidad = caballos.CaballoRepositoryMySQL().obtener_de_propietario(5, 10)

    assert entidad.altura == 1.6
    assert entidad.eliminado is True
    assert entidad.es_macho is True
    assert entidad.departamento == "Cundinamarca"


def test_obtener_de_propietario_inexistente(motor_falso):
    motor_falso(caballos, resultado(first=None))

    assert caballos.CaballoRepositoryMySQL().obtener_de_propietario(5, 10) is None


def test_registrar_macho_con_raza_nueva(motor_falso):
    conexion = motor_falso(
        caballos,
        resultado(lastrowid=8),   # INSERT raza
        resultado(lastrowid=5),   # INSERT caballo
        resultado(lastrowid=9),   # INSERT publicacion
    )
    publicacion = NuevaPublicacion("Lucero - Macho", "desc", 1000, date(2026, 1, 1))

    registrado = caballos.CaballoRepositoryMySQL().registrar(caballo(id_raza=None), "Criollo", publicacion)

    assert registrado == CaballoRegistrado(id_caballo=5, id_raza=8, id_publicacion=9)
    assert params(conexion, 0)["nombre"] == "Criollo"
    assert params(conexion, 1)["raza_id_raza"] == 8
    assert params(conexion, 2)["caballo_id_caballo"] == 5


def test_registrar_hembra_con_raza_existente(motor_falso):
    conexion = motor_falso(caballos, resultado(lastrowid=5))

    registrado = caballos.CaballoRepositoryMySQL().registrar(caballo(sexo="Hembra"), None, None)

    assert registrado == CaballoRegistrado(id_caballo=5, id_raza=1, id_publicacion=None)
    assert conexion.execute.call_count == 1


def test_actualizar_con_raza_nueva_y_publicacion(motor_falso):
    conexion = motor_falso(caballos, resultado(lastrowid=8), resultado(), resultado())
    cambios = CambiosPublicacion("Lucero - Macho", "desc", 1000)

    caballos.CaballoRepositoryMySQL().actualizar(caballo(id_raza=None), "Nueva", cambios)

    assert params(conexion, 0)["descripcion"] == "Raza registrada desde edicion"
    assert params(conexion, 1)["raza_id_raza"] == 8
    assert params(conexion, 2)["precio"] == 1000


def test_actualizar_sin_publicacion(motor_falso):
    conexion = motor_falso(caballos, resultado())

    caballos.CaballoRepositoryMySQL().actualizar(caballo(), None, None)

    assert conexion.execute.call_count == 1
    assert params(conexion, 0)["raza_id_raza"] == 1


def test_eliminar_borra_publicacion_y_marca_caballo(motor_falso):
    conexion = motor_falso(caballos, resultado(), resultado())

    caballos.CaballoRepositoryMySQL().eliminar(5)

    sentencias = [str(c.args[0]) for c in conexion.execute.call_args_list]
    assert "DELETE FROM publicacion" in sentencias[0]
    assert "'Eliminado'" in sentencias[1]


# ======================================================
# CABALLOS (consultas)
# ======================================================

def fila_mis_caballos(**cambios):
    datos = dict(
        id_caballo=5, nombre="Lucero", sexo="Macho", fecha_nacimiento=date(2020, 1, 1),
        altura=1.6, color="Castaño", ubicacion="Bogotá", ubicacion_texto="Bogotá",
        ciudad="Bogotá", departamento="Cundinamarca", descripcion="d",
        disponibilidad="Disponible", id_raza=1, raza="Criollo",
        foto_ruta="uploads/a.jpg", id_publicacion=1, precio_referencia=1000,
    )
    datos.update(cambios)
    return fila(**datos)


def test_listar_de_propietario(motor_falso):
    motor_falso(caballos, resultado(filas=[
        fila_mis_caballos(),
        fila_mis_caballos(foto_ruta=None, id_publicacion=None, precio_referencia=None),
    ]))

    lista = caballos.CaballoConsultasMySQL().listar_de_propietario(10)

    assert lista[0]["foto_principal"] == "/uploads/a.jpg"
    assert lista[0]["publicado"] is True
    assert lista[1]["foto_principal"] is None
    assert lista[1]["precio"] is None
    assert lista[1]["publicado"] is False


def test_obtener_detalle_de_propietario(motor_falso):
    detalle = fila_mis_caballos(raza_id_raza=1)
    motor_falso(caballos, resultado(first=detalle), resultado(filas=[FOTO]))

    respuesta = caballos.CaballoConsultasMySQL().obtener_detalle_de_propietario(5, 10)

    assert respuesta["id_raza"] == 1
    assert respuesta["precio"] == 1000.0
    assert respuesta["fotos"] == [{"id_foto": 1, "ruta": "/uploads/a.jpg", "es_principal": True, "orden": 0}]


def test_obtener_detalle_de_propietario_inexistente(motor_falso):
    motor_falso(caballos, resultado(first=None))

    assert caballos.CaballoConsultasMySQL().obtener_detalle_de_propietario(5, 10) is None


# ======================================================
# PUBLICACIONES
# ======================================================

def fila_publicacion(**cambios):
    datos = dict(
        id_publicacion=1, titulo="Lucero - Macho", descripcion="d",
        fecha_publicacion=date(2026, 1, 1), estado="Activa", precio_referencia=1000,
        usuario_id_usuario=10, id_caballo=5, nombre="Lucero", sexo="Macho",
        fecha_nacimiento=date(2020, 1, 1), altura=1.6, color="Castaño",
        ubicacion_texto="Bogotá", ciudad="Bogotá", departamento="Cundinamarca",
        ubicacion_lat=4.6, ubicacion_lng=-74.0, ubicacion="Bogotá",
        disponibilidad="Disponible", id_raza=1, raza="Criollo",
        raza_descripcion="r", propietario="Ana", propietario_ubicacion="Bogotá",
        propietario_telefono="300", foto_ruta="uploads/a.jpg", es_favorita=1,
    )
    datos.update(cambios)
    return fila(**datos)


def test_listar_publicaciones_activas(motor_falso):
    motor_falso(publicaciones, resultado(filas=[
        fila_publicacion(),
        fila_publicacion(usuario_id_usuario=99, ubicacion_lat=None, ubicacion_lng=None,
                         precio_referencia=None, foto_ruta=None, es_favorita=0),
    ]))

    lista = publicaciones.PublicacionConsultasMySQL().listar_activas(10)

    assert lista[0]["es_mia"] is True
    assert lista[0]["es_favorita"] is True
    assert lista[0]["foto_principal"] == "/uploads/a.jpg"
    assert lista[1]["es_mia"] is False
    assert lista[1]["ubicacion_lat"] is None
    assert lista[1]["precio"] is None


def test_detalle_publicacion(motor_falso):
    motor_falso(publicaciones, resultado(first=fila_publicacion()), resultado(filas=[FOTO]))

    detalle = publicaciones.PublicacionConsultasMySQL().obtener_detalle(1, 10)

    assert detalle["propietario_telefono"] == "300"
    assert detalle["fotos"][0]["ruta"] == "/uploads/a.jpg"


def test_detalle_publicacion_inexistente(motor_falso):
    motor_falso(publicaciones, resultado(first=None))

    assert publicaciones.PublicacionConsultasMySQL().obtener_detalle(1, 10) is None


# ======================================================
# UBICACIONES / FAVORITOS / GOOGLE
# ======================================================

def test_ubicaciones(motor_falso):
    conexion = motor_falso(
        ubicaciones,
        resultado(filas=[fila(departamento="Cundinamarca")]),
        resultado(filas=[fila(ciudad="Bogotá")]),
        resultado(filas=[]),
    )
    repo = ubicaciones.UbicacionConsultasMySQL()

    assert repo.listar_departamentos() == ["Cundinamarca"]
    assert repo.listar_ciudades("Cundinamarca") == ["Bogotá"]
    assert repo.listar_ciudades() == []
    assert params(conexion, 1) == {"departamento": "Cundinamarca"}
    assert params(conexion, 2) == {"departamento": None}


def test_favoritos(motor_falso):
    motor_falso(
        favoritos,
        resultado(first=fila(id_favorito=1)),
        resultado(lastrowid=4),
        resultado(rowcount=1),
    )
    repo = favoritos.FavoritoRepositoryMySQL()

    assert repo.existe(10, 5) is True
    assert repo.agregar(10, 5, date(2026, 1, 1)) == 4
    assert repo.quitar(10, 5) == 1


def test_usuario_google(motor_falso):
    conexion = motor_falso(
        google,
        resultado(first=fila(usuario_id_usuario="7")),
        resultado(first=None),
        resultado(first=fila(google_sub="g-1")),
        resultado(),
    )
    repo = google.UsuarioGoogleRepositoryMySQL()

    assert repo.obtener_id_usuario("g-1") == 7
    assert repo.obtener_id_usuario("otro") is None
    assert repo.obtener_sub(7) == "g-1"
    repo.vincular(7, "g-1")
    assert params(conexion, 3) == {"id_usuario": 7, "google_sub": "g-1"}


# ======================================================
# CÓDIGOS DE VERIFICACIÓN
# ======================================================

def test_codigos_de_verificacion(motor_falso):
    expira = datetime(2026, 1, 1, 12, 0)
    conexion = motor_falso(
        codigos,
        resultado(), resultado(),  # reemplazar: invalida + inserta
        resultado(first=fila(id_verificacion=3, codigo_hash="h", fecha_expiracion=expira, intentos=1)),
        resultado(first=None),
        resultado(),
        resultado(),
    )
    repo = codigos.CodigoVerificacionRepositoryMySQL()

    repo.reemplazar(7, "REGISTRO", "h", expira)
    vigente = repo.obtener_vigente(7, "REGISTRO")

    assert vigente.id_verificacion == 3 and vigente.intentos == 1
    assert repo.obtener_vigente(7, "REGISTRO") is None
    repo.marcar_usado(3)
    repo.registrar_intento_fallido(3, 5)
    assert params(conexion, 1)["codigo_hash"] == "h"
    assert params(conexion, 5) == {"id": 3, "max_intentos": 5}


# ======================================================
# USUARIOS / AUDITORÍA
# ======================================================

@pytest.mark.parametrize(
    ("metodo", "valor", "columna"),
    [("actualizar_estado", "activo", "estado"), ("actualizar_contrasena", "hash", "contraseña")],
)
def test_usuario_actualizaciones(metodo, valor, columna):
    db = MagicMock()
    sesion = MagicMock()
    sesion.__enter__.return_value = db

    with patch.object(usuarios, "SessionLocal", return_value=sesion):
        getattr(usuarios.UsuarioRepositoryMySQL(), metodo)(7, valor)

    sentencia = db.execute.call_args.args[0]
    assert columna in str(sentencia)
    db.commit.assert_called_once()


def test_auditoria_mysql_delega_en_funcion():
    with patch.object(audit_log_service, "registrar_auditoria") as registrar:
        audit_log_service.AuditoriaMySQL().registrar("LOGIN", "AUTH", "EXITOSO", 7, "ok")

    registrar.assert_called_once_with(
        accion="LOGIN", modulo="AUTH", resultado="EXITOSO", usuario_id=7, detalle="ok"
    )
