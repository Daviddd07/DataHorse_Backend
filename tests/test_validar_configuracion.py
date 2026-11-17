import pytest

from app.config.validar_configuracion import (
    ConfiguracionInvalidaError,
    problemas_de_configuracion,
    validar_configuracion,
)

SECRETO = "x" * 40

ENTORNO_VALIDO = {
    "DB_HOST": "db",
    "DB_PORT": "3306",
    "DB_USER": "u",
    "DB_PASSWORD": "p",
    "DB_NAME": "datahorse2",
    "SECRET_KEY": SECRETO,
    "CODIGO_SECRET": SECRETO,
}


def test_configuracion_valida_no_lanza():
    assert problemas_de_configuracion(ENTORNO_VALIDO) == []
    validar_configuracion(ENTORNO_VALIDO)


@pytest.mark.parametrize("variable", ["SECRET_KEY", "CODIGO_SECRET", "DB_HOST"])
def test_falta_una_variable(variable):
    entorno = {**ENTORNO_VALIDO, variable: "  "}

    with pytest.raises(ConfiguracionInvalidaError, match=f"Falta {variable}"):
        validar_configuracion(entorno)


def test_secreto_demasiado_corto():
    entorno = {**ENTORNO_VALIDO, "SECRET_KEY": "corta"}

    assert problemas_de_configuracion(entorno) == [
        "SECRET_KEY es demasiado corta (5 caracteres; mínimo 32)"
    ]


def test_almacenamiento_s3_exige_bucket():
    entorno = {**ENTORNO_VALIDO, "ALMACENAMIENTO": "s3"}

    assert problemas_de_configuracion(entorno) == [
        "Falta S3_BUCKET_ARCHIVOS (obligatoria con ALMACENAMIENTO=s3)"
    ]
    assert problemas_de_configuracion({**entorno, "S3_BUCKET_ARCHIVOS": "mi-bucket"}) == []


def test_almacenamiento_desconocido():
    entorno = {**ENTORNO_VALIDO, "ALMACENAMIENTO": "ftp"}

    assert problemas_de_configuracion(entorno) == [
        "ALMACENAMIENTO debe ser 'local' o 's3' (es 'ftp')"
    ]
