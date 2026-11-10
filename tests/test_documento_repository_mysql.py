from datetime import datetime

from conftest import fila, resultado

from app.domain.entities.documento_caballo import DocumentoCaballo
from app.infraestructure.adaptadores.outbound.persistence import documento_repository_mysql as modulo

FECHA = datetime(2026, 11, 10, 9, 30)


def fila_documento(**cambios):
    datos = dict(
        id_documento=3, caballo_id_caballo=5, tipo="premio", titulo="Campeón 2024",
        ruta="documentos/a.png", nombre_original="campeon.png", content_type="image/png",
        tamano_bytes=2048, estado_verificacion="sin_revisar", fecha_subida=FECHA,
    )
    datos.update(cambios)
    return fila(**datos)


def repo():
    return modulo.DocumentoRepositoryMySQL()


def test_guardar_devuelve_el_documento_con_id_y_fecha(motor_falso):
    conexion = motor_falso(modulo, resultado(lastrowid=3), resultado(first=fila_documento()))
    nuevo = DocumentoCaballo(
        id_documento=None, id_caballo=5, tipo="premio", titulo="Campeón 2024",
        ruta="documentos/a.png", nombre_original="campeon.png",
        content_type="image/png", tamano_bytes=2048,
    )

    guardado = repo().guardar(nuevo)

    assert guardado.id_documento == 3
    assert guardado.fecha_subida == FECHA
    assert guardado.tipo_etiqueta == "Premio"
    assert guardado.es_pdf is False
    assert conexion.execute.call_args_list[0].args[1]["estado"] == "sin_revisar"


def test_listar_por_caballo(motor_falso):
    motor_falso(modulo, resultado(filas=[fila_documento(), fila_documento(id_documento=4)]))

    assert [d.id_documento for d in repo().listar_por_caballo(5)] == [3, 4]


def test_contar_por_caballo(motor_falso):
    motor_falso(modulo, resultado(scalar=2))

    assert repo().contar_por_caballo(5) == 2


def test_obtener_existente_e_inexistente(motor_falso):
    motor_falso(modulo, resultado(first=fila_documento()), resultado(first=None))

    assert repo().obtener(5, 3).titulo == "Campeón 2024"
    assert repo().obtener(5, 99) is None


def test_eliminar(motor_falso):
    conexion = motor_falso(modulo, resultado())

    repo().eliminar(3)

    assert conexion.execute.call_args.args[1] == {"id": 3}


def test_contexto_caballo(motor_falso):
    motor_falso(
        modulo,
        resultado(first=fila(usuario_id_usuario=10, eliminado=0, publicado=1)),
        resultado(first=None),
    )

    contexto = repo().contexto_caballo(5)

    assert (contexto.id_propietario, contexto.eliminado, contexto.publicado) == (10, False, True)
    assert repo().contexto_caballo(99) is None
