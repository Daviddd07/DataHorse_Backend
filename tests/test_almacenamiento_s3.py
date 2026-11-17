"""Adaptador de S3 y endpoint de fotos públicas, con un S3 falso en memoria (sin red ni AWS)."""
import io

import pytest
from botocore.exceptions import ClientError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.config.dependencies import get_almacenamientos_publicos
from app.infraestructure.adaptadores.inbound.rest import archivos_publicos_controller
from app.domain.exceptions import DominioError
from app.infraestructure.adaptadores.inbound.rest.errores import estado_http
from app.infraestructure.adaptadores.outbound.almacenamiento.almacenamiento_s3 import (
    AlmacenamientoS3,
)


class S3Falso:
    """Imita put_object / get_object / delete_object de boto3."""

    def __init__(self):
        self.objetos = {}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objetos[(Bucket, Key)] = (Body, ContentType)

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.objetos:
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "no existe"}}, "GetObject")
        return {"Body": io.BytesIO(self.objetos[(Bucket, Key)][0])}

    def delete_object(self, Bucket, Key):
        self.objetos.pop((Bucket, Key), None)


@pytest.fixture
def s3():
    return S3Falso()


def test_guarda_lee_y_elimina_con_la_misma_ruta_que_en_local(s3):
    almacenamiento = AlmacenamientoS3(s3, "bucket", "/uploads/caballos")

    ruta = almacenamiento.guardar(".jpg", b"foto")

    assert ruta.startswith("uploads/caballos/") and ruta.endswith(".jpg")
    assert s3.objetos[("bucket", ruta)] == (b"foto", "image/jpeg")
    assert almacenamiento.leer(ruta) == b"foto"

    almacenamiento.eliminar(ruta)
    assert ("bucket", ruta) not in s3.objetos


def test_leer_inexistente_lanza_file_not_found(s3):
    almacenamiento = AlmacenamientoS3(s3, "bucket", "documentos")

    with pytest.raises(FileNotFoundError):
        almacenamiento.leer("documentos/no-existe.pdf")


def test_otros_errores_de_s3_no_se_ocultan():
    class S3SinPermiso(S3Falso):
        def get_object(self, Bucket, Key):
            raise ClientError({"Error": {"Code": "AccessDenied", "Message": "x"}}, "GetObject")

    with pytest.raises(ClientError):
        AlmacenamientoS3(S3SinPermiso(), "bucket", "documentos").leer("documentos/a.pdf")


def test_nunca_sale_del_prefijo(s3):
    s3.objetos[("bucket", "secreto.txt")] = (b"x", "text/plain")
    almacenamiento = AlmacenamientoS3(s3, "bucket", "uploads/caballos")

    almacenamiento.eliminar("../../secreto.txt")
    with pytest.raises(FileNotFoundError):
        almacenamiento.leer("../../secreto.txt")

    assert ("bucket", "secreto.txt") in s3.objetos


# ======================================================
# ENDPOINT /uploads EN MODO S3
# ======================================================

@pytest.fixture
def cliente(s3):
    app = FastAPI()

    @app.exception_handler(DominioError)
    async def _error(request: Request, exc: DominioError):  # igual que main.py
        return JSONResponse({"detail": exc.mensaje}, status_code=estado_http(exc))

    app.include_router(archivos_publicos_controller.router)
    caballos = AlmacenamientoS3(s3, "bucket", "uploads/caballos")
    app.dependency_overrides[get_almacenamientos_publicos] = lambda: {"caballos": caballos}
    return TestClient(app), caballos


def test_sirve_la_foto_con_la_url_de_siempre(cliente):
    http, caballos = cliente
    ruta = caballos.guardar(".png", b"png")

    respuesta = http.get(f"/{ruta}")

    assert respuesta.status_code == 200
    assert respuesta.content == b"png"
    assert respuesta.headers["content-type"] == "image/png"
    assert "immutable" in respuesta.headers["cache-control"]


@pytest.mark.parametrize("url", ["/uploads/caballos/no-existe.jpg", "/uploads/documentos/privado.pdf"])
def test_foto_inexistente_o_carpeta_privada_da_404(cliente, url):
    http, _ = cliente

    assert http.get(url).status_code == 404
