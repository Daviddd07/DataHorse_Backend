from dataclasses import replace
from datetime import date
from unittest.mock import Mock

import pytest

from app.application.use_cases.documento_use_cases import (
    EliminarDocumentoUseCase,
    ListarDocumentosUseCase,
    ObtenerArchivoDocumentoUseCase,
    SubirDocumentosUseCase,
)
from app.domain.entities.Caballo import Caballo
from app.domain.entities.documento_caballo import ContextoCaballo, DocumentoCaballo
from app.domain.exceptions import (
    AccesoDenegadoError,
    ErrorInternoError,
    RecursoNoEncontradoError,
    SolicitudInvalidaError,
)
from app.domain.ports.in_.documento_ports import DocumentoNuevo
from app.domain.ports.in_.foto_ports import ArchivoSubido
from app.domain.services.validador_documento import (
    DOCUMENTO_MAX_BYTES,
    detectar_formato,
    validar_archivo,
    validar_tipo,
    validar_titulo,
)

PDF = b"%PDF-1.7\n..."
JPG = b"\xff\xd8\xff\xe0" + b"0" * 20
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 "

DUENO, OTRO = 10, 99

MACHO = Caballo(
    id_caballo=5, id_raza=1, id_propietario=DUENO, nombre="Lucero", sexo="Macho",
    fecha_nacimiento=date(2020, 1, 1), altura=1.6, color="Castaño",
    ubicacion="Bogotá", descripcion="desc", disponibilidad="Disponible",
)

DOC = DocumentoCaballo(
    id_documento=3, id_caballo=5, tipo="pedigri", titulo="Registro ASDE",
    ruta="documentos/a.pdf", nombre_original="registro.pdf",
    content_type="application/pdf", tamano_bytes=len(PDF),
)


def nuevo(nombre="registro.pdf", contenido=PDF, tipo="pedigri", titulo="Registro ASDE"):
    return DocumentoNuevo(tipo=tipo, titulo=titulo, archivo=ArchivoSubido(nombre, "application/pdf", contenido))


# ======================================================
# VALIDACIÓN (dominio)
# ======================================================

@pytest.mark.parametrize(
    ("contenido", "esperado"),
    [(PDF, "application/pdf"), (JPG, "image/jpeg"), (PNG, "image/png"),
     (WEBP, "image/webp"), (b"GIF89a....", None), (b"", None)],
)
def test_detectar_formato_por_contenido(contenido, esperado):
    assert detectar_formato(contenido) == esperado


@pytest.mark.parametrize(
    ("nombre", "contenido"),
    [("a.pdf", PDF), ("a.JPG", JPG), ("a.jpeg", JPG), ("a.png", PNG), ("a.webp", WEBP)],
)
def test_validar_archivo_acepta_formatos(nombre, contenido):
    extension, real = validar_archivo(nombre, contenido)
    assert extension == nombre[nombre.rfind("."):].lower()
    assert real == detectar_formato(contenido)


@pytest.mark.parametrize(
    ("nombre", "contenido", "mensaje"),
    [
        ("a.docx", PDF, "formato no permitido"),
        ("a.pdf", b"", "está vacío"),
        ("a.pdf", b"%PDF-" + b"x" * DOCUMENTO_MAX_BYTES, "supera los 10 MB"),
        # Disfrazado: un ejecutable o una imagen renombrados a .pdf
        ("a.pdf", b"MZ\x90\x00", "no corresponde a un archivo .pdf"),
        ("a.pdf", JPG, "no corresponde a un archivo .pdf"),
    ],
)
def test_validar_archivo_rechaza(nombre, contenido, mensaje):
    with pytest.raises(SolicitudInvalidaError, match=mensaje):
        validar_archivo(nombre, contenido)


def test_validar_tipo_y_titulo():
    assert validar_tipo(" premio ") == "premio"
    assert validar_titulo("  Campeón   nacional  ") == "Campeón nacional"
    with pytest.raises(SolicitudInvalidaError, match="Tipo de documento no válido"):
        validar_tipo("diploma")
    with pytest.raises(SolicitudInvalidaError, match="entre 2 y 120"):
        validar_titulo("x")


# ======================================================
# SUBIR
# ======================================================

@pytest.fixture
def subir():
    caballo_repo, doc_repo, almacenamiento, auditoria = Mock(), Mock(), Mock(), Mock()
    caballo_repo.obtener_de_propietario.return_value = MACHO
    doc_repo.contar_por_caballo.return_value = 0
    contador = iter(range(1, 100))
    doc_repo.guardar.side_effect = lambda d: replace(d, id_documento=next(contador))
    almacenamiento.guardar.side_effect = lambda ext, _: f"documentos/x{ext}"
    caso = SubirDocumentosUseCase(caballo_repo, doc_repo, almacenamiento, auditoria)
    return caso, caballo_repo, doc_repo, almacenamiento, auditoria


def test_subir_documentos_exitoso(subir):
    caso, _, doc_repo, almacenamiento, auditoria = subir

    guardados = caso.ejecutar(5, DUENO, [nuevo(), nuevo("foto.png", PNG, "premio", "Campeón 2024")])

    assert [d.id_documento for d in guardados] == [1, 2]
    assert guardados[1].content_type == "image/png"
    assert guardados[1].tipo == "premio"
    assert almacenamiento.guardar.call_count == 2
    assert auditoria.registrar.call_args.kwargs["resultado"] == "EXITOSO"


def test_subir_documentos_solo_machos(subir):
    caso, caballo_repo, _, almacenamiento, _ = subir
    caballo_repo.obtener_de_propietario.return_value = replace(MACHO, sexo="Hembra")

    with pytest.raises(SolicitudInvalidaError, match="Solo los caballos machos"):
        caso.ejecutar(5, DUENO, [nuevo()])

    almacenamiento.guardar.assert_not_called()


def test_subir_documentos_caballo_ajeno(subir):
    caso, caballo_repo, _, _, _ = subir
    caballo_repo.obtener_de_propietario.return_value = None

    with pytest.raises(RecursoNoEncontradoError):
        caso.ejecutar(5, OTRO, [nuevo()])


def test_subir_documentos_respeta_el_maximo(subir):
    caso, _, doc_repo, almacenamiento, _ = subir
    doc_repo.contar_por_caballo.return_value = 9

    with pytest.raises(SolicitudInvalidaError, match="Máximo 10 documentos"):
        caso.ejecutar(5, DUENO, [nuevo(), nuevo()])

    almacenamiento.guardar.assert_not_called()


def test_subir_documentos_valida_todo_antes_de_guardar(subir):
    caso, _, _, almacenamiento, auditoria = subir

    with pytest.raises(SolicitudInvalidaError):
        caso.ejecutar(5, DUENO, [nuevo(), nuevo("malo.pdf", b"MZ")])

    almacenamiento.guardar.assert_not_called()
    assert auditoria.registrar.call_args.kwargs["resultado"] == "FALLIDO"


def test_subir_documentos_vacio(subir):
    caso = subir[0]
    with pytest.raises(SolicitudInvalidaError, match="ningún documento"):
        caso.ejecutar(5, DUENO, [])


def test_subir_documentos_deshace_si_falla_a_medias(subir):
    caso, _, doc_repo, almacenamiento, _ = subir
    doc_repo.guardar.side_effect = [replace(DOC, id_documento=1), RuntimeError("BD caída")]

    with pytest.raises(ErrorInternoError):
        caso.ejecutar(5, DUENO, [nuevo(), nuevo()])

    doc_repo.eliminar.assert_called_once_with(1)
    assert almacenamiento.eliminar.call_count == 2


# ======================================================
# LISTAR / VER / DESCARGAR
# ======================================================

def contexto(publicado=True, eliminado=False):
    return ContextoCaballo(id_propietario=DUENO, eliminado=eliminado, publicado=publicado)


@pytest.fixture
def lectura():
    doc_repo, almacenamiento = Mock(), Mock()
    doc_repo.contexto_caballo.return_value = contexto()
    doc_repo.listar_por_caballo.return_value = [DOC]
    doc_repo.obtener.return_value = DOC
    almacenamiento.leer.return_value = PDF
    return doc_repo, almacenamiento


@pytest.mark.parametrize(("id_usuario", "es_propietario"), [(DUENO, True), (OTRO, False)])
def test_listar_documentos(lectura, id_usuario, es_propietario):
    doc_repo, _ = lectura

    resultado = ListarDocumentosUseCase(doc_repo).ejecutar(5, id_usuario)

    assert resultado.documentos == [DOC]
    assert resultado.es_propietario is es_propietario


def test_listar_documentos_de_caballo_no_publicado(lectura):
    doc_repo, _ = lectura
    doc_repo.contexto_caballo.return_value = contexto(publicado=False)

    # El dueño sí los ve; otro usuario recibe 404, como si no existiera
    assert ListarDocumentosUseCase(doc_repo).ejecutar(5, DUENO).documentos == [DOC]
    with pytest.raises(RecursoNoEncontradoError):
        ListarDocumentosUseCase(doc_repo).ejecutar(5, OTRO)


@pytest.mark.parametrize("ctx", [None, contexto(eliminado=True)])
def test_listar_documentos_caballo_inexistente_o_eliminado(lectura, ctx):
    doc_repo, _ = lectura
    doc_repo.contexto_caballo.return_value = ctx

    with pytest.raises(RecursoNoEncontradoError):
        ListarDocumentosUseCase(doc_repo).ejecutar(5, DUENO)


def test_ver_documento_otro_usuario(lectura):
    caso = ObtenerArchivoDocumentoUseCase(*lectura)

    archivo = caso.ejecutar(5, 3, OTRO, descargar=False)

    assert archivo.contenido == PDF
    assert archivo.documento is DOC


def test_descargar_solo_el_propietario(lectura):
    caso = ObtenerArchivoDocumentoUseCase(*lectura)

    assert caso.ejecutar(5, 3, DUENO, descargar=True).contenido == PDF
    with pytest.raises(AccesoDenegadoError, match="Solo el propietario"):
        caso.ejecutar(5, 3, OTRO, descargar=True)


def test_ver_documento_inexistente_o_sin_archivo(lectura):
    doc_repo, almacenamiento = lectura
    caso = ObtenerArchivoDocumentoUseCase(doc_repo, almacenamiento)

    almacenamiento.leer.side_effect = FileNotFoundError()
    with pytest.raises(RecursoNoEncontradoError, match="ya no existe"):
        caso.ejecutar(5, 3, DUENO, descargar=False)

    doc_repo.obtener.return_value = None
    with pytest.raises(RecursoNoEncontradoError, match="Documento no encontrado"):
        caso.ejecutar(5, 3, DUENO, descargar=False)


# ======================================================
# ELIMINAR
# ======================================================

@pytest.fixture
def eliminar():
    caballo_repo, doc_repo, almacenamiento, auditoria = Mock(), Mock(), Mock(), Mock()
    caballo_repo.obtener_de_propietario.return_value = MACHO
    doc_repo.obtener.return_value = DOC
    caso = EliminarDocumentoUseCase(caballo_repo, doc_repo, almacenamiento, auditoria)
    return caso, caballo_repo, doc_repo, almacenamiento, auditoria


def test_eliminar_documento(eliminar):
    caso, _, doc_repo, almacenamiento, auditoria = eliminar

    caso.ejecutar(5, 3, DUENO)

    doc_repo.eliminar.assert_called_once_with(3)
    almacenamiento.eliminar.assert_called_once_with("documentos/a.pdf")
    assert auditoria.registrar.call_args.kwargs["resultado"] == "EXITOSO"


def test_eliminar_documento_ajeno_o_inexistente(eliminar):
    caso, caballo_repo, doc_repo, _, _ = eliminar

    doc_repo.obtener.return_value = None
    with pytest.raises(RecursoNoEncontradoError, match="Documento no encontrado"):
        caso.ejecutar(5, 3, DUENO)

    caballo_repo.obtener_de_propietario.return_value = None
    with pytest.raises(RecursoNoEncontradoError):
        caso.ejecutar(5, 3, OTRO)

    doc_repo.eliminar.assert_not_called()


def test_eliminar_documento_si_falla_el_archivo_queda_auditado(eliminar):
    caso, _, doc_repo, almacenamiento, auditoria = eliminar
    almacenamiento.eliminar.side_effect = OSError("disco")

    caso.ejecutar(5, 3, DUENO)

    doc_repo.eliminar.assert_called_once_with(3)
    assert auditoria.registrar.call_args.kwargs["resultado"] == "FALLIDO"
