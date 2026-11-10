from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

import main
from app.config import dependencies as deps
from app.domain.entities.documento_caballo import DocumentoCaballo
from app.domain.exceptions import AccesoDenegadoError
from app.domain.ports.in_.documento_ports import ArchivoDocumento, DocumentosDeCaballo

PDF = b"%PDF-1.7 contenido"

DOC = DocumentoCaballo(
    id_documento=3, id_caballo=5, tipo="pedigri", titulo="Registro ASDE",
    ruta="documentos/a.pdf", nombre_original="registro año.pdf",
    content_type="application/pdf", tamano_bytes=len(PDF),
)


@pytest.fixture
def api():
    tokens = Mock()
    tokens.decodificar.side_effect = lambda t: "7" if t == "valido" else None
    main.app.dependency_overrides[deps.get_token_service] = lambda: tokens

    with patch.object(main, "guardar_log_tecnico"):
        cliente = TestClient(main.app)

        def usar(proveedor):
            caso = Mock()
            main.app.dependency_overrides[proveedor] = lambda: caso
            return caso

        cliente.usar = usar
        cliente.cookies.set("access_token", "valido")
        yield cliente

    main.app.dependency_overrides.clear()


def test_tipos_de_documento(api):
    respuesta = api.get("/api/v1/caballos/documentos/tipos")

    assert respuesta.status_code == 200
    assert {"valor": "premio", "etiqueta": "Premio"} in respuesta.json()


def test_subir_documentos_envia_tipo_y_titulo_de_cada_archivo(api):
    caso = api.usar(deps.get_subir_documentos_use_case)
    caso.ejecutar.return_value = [DOC]

    respuesta = api.post(
        "/api/v1/caballos/5/documentos",
        files=[("files", ("registro.pdf", PDF, "application/pdf"))],
        data={"tipos": ["pedigri"], "titulos": ["Registro ASDE"]},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()[0]["tipo_etiqueta"] == "Pedigrí / registro"
    assert respuesta.json()[0]["es_pdf"] is True
    id_caballo, id_usuario, nuevos = caso.ejecutar.call_args.args
    assert (id_caballo, id_usuario) == (5, 7)
    assert nuevos[0].titulo == "Registro ASDE"
    assert nuevos[0].archivo.contenido == PDF


def test_subir_documentos_exige_tipo_y_titulo_por_archivo(api):
    api.usar(deps.get_subir_documentos_use_case)

    respuesta = api.post(
        "/api/v1/caballos/5/documentos",
        files=[("files", ("a.pdf", PDF, "application/pdf")), ("files", ("b.pdf", PDF, "application/pdf"))],
        data={"tipos": ["pedigri"], "titulos": ["Uno"]},
    )

    assert respuesta.status_code == 400
    assert "tipo y su título" in respuesta.json()["detail"]


def test_listar_documentos(api):
    caso = api.usar(deps.get_listar_documentos_use_case)
    caso.ejecutar.return_value = DocumentosDeCaballo(documentos=[DOC], es_propietario=False)

    respuesta = api.get("/api/v1/caballos/5/documentos")

    assert respuesta.status_code == 200
    assert respuesta.json()["es_propietario"] is False
    assert respuesta.json()["documentos"][0]["titulo"] == "Registro ASDE"
    # La ruta interna del archivo nunca sale en la respuesta
    assert "ruta" not in respuesta.json()["documentos"][0]


def test_ver_documento_se_muestra_sin_ofrecer_descarga(api):
    caso = api.usar(deps.get_obtener_archivo_documento_use_case)
    caso.ejecutar.return_value = ArchivoDocumento(documento=DOC, contenido=PDF)

    respuesta = api.get("/api/v1/caballos/5/documentos/3/contenido")

    assert respuesta.status_code == 200
    assert respuesta.content == PDF
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.headers["content-disposition"].startswith("inline;")
    assert "no-store" in respuesta.headers["cache-control"]
    assert respuesta.headers["x-content-type-options"] == "nosniff"
    assert caso.ejecutar.call_args.kwargs["descargar"] is False


def test_descargar_documento_como_adjunto(api):
    caso = api.usar(deps.get_obtener_archivo_documento_use_case)
    caso.ejecutar.return_value = ArchivoDocumento(documento=DOC, contenido=PDF)

    respuesta = api.get("/api/v1/caballos/5/documentos/3/descarga")

    assert respuesta.status_code == 200
    assert respuesta.headers["content-disposition"] == "attachment; filename*=UTF-8''registro%20a%C3%B1o.pdf"
    assert caso.ejecutar.call_args.kwargs["descargar"] is True


def test_descargar_documento_ajeno_responde_403(api):
    caso = api.usar(deps.get_obtener_archivo_documento_use_case)
    caso.ejecutar.side_effect = AccesoDenegadoError("Solo el propietario puede descargar este documento")

    respuesta = api.get("/api/v1/caballos/5/documentos/3/descarga")

    assert respuesta.status_code == 403


def test_documentos_exigen_sesion(api):
    api.cookies.clear()

    assert api.get("/api/v1/caballos/5/documentos").status_code == 401
    assert api.get("/api/v1/caballos/5/documentos/3/contenido").status_code == 401


def test_eliminar_documento(api):
    caso = api.usar(deps.get_eliminar_documento_use_case)

    respuesta = api.delete("/api/v1/caballos/5/documentos/3")

    assert respuesta.status_code == 200
    caso.ejecutar.assert_called_once_with(5, 3, 7)
