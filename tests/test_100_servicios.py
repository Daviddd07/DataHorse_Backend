from unittest.mock import MagicMock

import pytest

from app.domain.services import geocoding_service as geo
from app.domain.services import subir_fotos_service as fotos


# ============================================================
# CONFIGURACION Y DOBLES DE PRUEBA
# ============================================================

class RepoFotosFalso:
    def __init__(self, cantidad=0):
        self.cantidad = cantidad
        self.guardadas = []
        self.promociones = []

    def contar_por_caballo(self, id_caballo):
        return self.cantidad

    def guardar(self, foto):
        self.guardadas.append(foto)
        return foto

    def promover_principal(self, id_caballo):
        self.promociones.append(id_caballo)


def configurar_fotos(monkeypatch, tmp_path):
    monkeypatch.setattr(fotos, "FOTO_CABALLO_DIR", tmp_path)
    monkeypatch.setattr(fotos, "FOTO_CABALLO_URL_PREFIX", "/fotos")
    monkeypatch.setattr(fotos, "FOTO_MAX_SIZE", 5)
    monkeypatch.setattr(fotos, "FOTO_ALLOWED_TYPES", {"image/jpeg", "image/png"})
    monkeypatch.setattr(fotos, "FOTO_EXT_ALLOWED", {".jpg", ".jpeg", ".png"})


def respuesta_geo(status=200, resultados=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = resultados if resultados is not None else []
    return r


# ============================================================
# GEOCODIFICACION: 40 CASOS
# ============================================================

@pytest.mark.parametrize("texto", [
    "", " ", "   ", "\t", "\n", "\t\n", "     ", "\n  \t",
])
def test_geo_entrada_vacia_no_consulta(monkeypatch, texto):
    get = MagicMock()
    monkeypatch.setattr(geo.requests, "get", get)
    assert geo.GeocodingService().geocodificar(texto) is None
    get.assert_not_called()


@pytest.mark.parametrize("status", [
    201, 204, 301, 400, 401, 403, 404, 500,
])
def test_geo_estado_http_no_exitoso(monkeypatch, status):
    monkeypatch.setattr(
        geo.requests, "get", MagicMock(return_value=respuesta_geo(status))
    )
    assert geo.GeocodingService().geocodificar("Bogota") is None


@pytest.mark.parametrize("resultados", [
    [], [], [], [], [], [], [], [],
])
def test_geo_sin_resultados(monkeypatch, resultados):
    monkeypatch.setattr(
        geo.requests, "get",
        MagicMock(return_value=respuesta_geo(200, resultados)),
    )
    assert geo.GeocodingService().geocodificar("Fusagasuga") is None


@pytest.mark.parametrize("campo,valor", [
    ("city", "Ciudad A"),
    ("town", "Pueblo B"),
    ("village", "Vereda C"),
    ("municipality", "Municipio D"),
    ("county", "Condado E"),
])
def test_geo_resuelve_variantes_de_ciudad(monkeypatch, campo, valor):
    resultado = {
        "lat": "4.5",
        "lon": "-74.1",
        "display_name": "Lugar de prueba",
        "address": {campo: valor, "state": "Cundinamarca"},
    }
    monkeypatch.setattr(
        geo.requests, "get",
        MagicMock(return_value=respuesta_geo(200, [resultado])),
    )

    salida = geo.GeocodingService().geocodificar("Lugar")

    assert salida["ciudad"] == valor
    assert salida["departamento"] == "Cundinamarca"
    assert salida["lat"] == 4.5
    assert salida["lng"] == -74.1


@pytest.mark.parametrize("error", [
    RuntimeError("error de red"),
    ValueError("respuesta invalida"),
    TypeError("tipo inesperado"),
    KeyError("campo ausente"),
    Exception("error inesperado"),
])
def test_geo_maneja_excepciones(monkeypatch, error):
    monkeypatch.setattr(
        geo.requests, "get", MagicMock(side_effect=error)
    )
    assert geo.GeocodingService().geocodificar("Bogota") is None


@pytest.mark.parametrize("campo,valor", [
    ("lat", "no-es-numero"),
    ("lon", "no-es-numero"),
    ("lat", None),
])
def test_geo_coordenada_invalida_devuelve_none(monkeypatch, campo, valor):
    resultado = {"lat": "4.5", "lon": "-74.1", "address": {}}
    resultado[campo] = valor
    monkeypatch.setattr(
        geo.requests, "get",
        MagicMock(return_value=respuesta_geo(200, [resultado])),
    )
    assert geo.GeocodingService().geocodificar("Lugar") is None


@pytest.mark.parametrize("texto,timeout", [
    (" Bogota ", 1),
    ("Medellin", 5),
    ("Cali", 20),
])
def test_geo_envia_parametros_correctos(monkeypatch, texto, timeout):
    resultado = {
        "lat": "4.6",
        "lon": "-74.0",
        "display_name": "Resultado",
        "address": {"city": "Ciudad", "state": "Departamento"},
    }
    get = MagicMock(return_value=respuesta_geo(200, [resultado]))
    monkeypatch.setattr(geo.requests, "get", get)

    salida = geo.GeocodingService(timeout=timeout).geocodificar(texto)

    assert salida is not None
    kwargs = get.call_args.kwargs
    assert kwargs["params"]["q"] == texto.strip()
    assert kwargs["params"]["format"] == "json"
    assert kwargs["params"]["limit"] == 1
    assert kwargs["params"]["addressdetails"] == 1
    assert kwargs["timeout"] == timeout
    assert kwargs["headers"]["User-Agent"]
    assert kwargs["headers"]["Accept-Language"] == "es"


# ============================================================
# FOTOGRAFIAS: 60 CASOS
# ============================================================

@pytest.mark.parametrize("tipo", [
    "text/plain", "application/pdf", "image/gif", "image/webp",
    "application/json", "", "IMAGE/JPEG", "image/bmp",
    "audio/mpeg", "video/mp4",
])
def test_fotos_rechaza_tipo_no_permitido(monkeypatch, tmp_path, tipo):
    configurar_fotos(monkeypatch, tmp_path)
    repo = RepoFotosFalso()

    with pytest.raises(ValueError, match="Tipo no permitido"):
        fotos.SubirFotosService(repo).ejecutar(
            1, [("foto.jpg", tipo, b"abc")]
        )

    assert repo.guardadas == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("tamano", [
    6, 7, 8, 9, 10, 20, 50, 100, 1000, 10000,
])
def test_fotos_rechaza_archivo_demasiado_grande(
    monkeypatch, tmp_path, tamano
):
    configurar_fotos(monkeypatch, tmp_path)
    repo = RepoFotosFalso()

    with pytest.raises(ValueError, match="excede 5MB"):
        fotos.SubirFotosService(repo).ejecutar(
            1, [("foto.jpg", "image/jpeg", b"x" * tamano)]
        )

    assert repo.guardadas == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("nombre", [
    "foto.gif", "foto.webp", "foto.bmp", "foto.svg", "foto.pdf",
    "foto", "foto.JPG.exe", "foto.jpeg.txt", "foto.PNG.gif",
    "foto.tiff",
])
def test_fotos_rechaza_extension_no_permitida(
    monkeypatch, tmp_path, nombre
):
    configurar_fotos(monkeypatch, tmp_path)
    repo = RepoFotosFalso()

    with pytest.raises(ValueError, match="Extensi"):
        fotos.SubirFotosService(repo).ejecutar(
            1, [(nombre, "image/jpeg", b"abc")]
        )

    assert repo.guardadas == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("nombre,tipo,contenido", [
    ("a.jpg", "image/jpeg", b"a"),
    ("b.jpeg", "image/jpeg", b"bb"),
    ("c.png", "image/png", b"ccc"),
    ("d.JPG", "image/jpeg", b"dddd"),
    ("e.PNG", "image/png", b"12345"),
    ("f.jpg", "image/jpeg", b"123"),
    ("g.png", "image/png", b"12"),
    ("h.jpeg", "image/jpeg", b"1234"),
    ("i.jpg", "image/jpeg", b""),
    ("j.png", "image/png", b"ok"),
])
def test_fotos_guarda_archivos_validos(
    monkeypatch, tmp_path, nombre, tipo, contenido
):
    configurar_fotos(monkeypatch, tmp_path)
    repo = RepoFotosFalso(cantidad=0)

    resultado = fotos.SubirFotosService(repo).ejecutar(
        7, [(nombre, tipo, contenido)]
    )

    assert len(resultado) == 1
    assert len(repo.guardadas) == 1
    foto = resultado[0]
    assert foto.id_caballo == 7
    assert foto.es_principal is True
    assert foto.orden == 0
    assert (tmp_path / foto.ruta.split("/")[-1]).read_bytes() == contenido


@pytest.mark.parametrize("cantidad", [1, 2, 3, 5, 10])
def test_fotos_no_reemplaza_principal_existente(
    monkeypatch, tmp_path, cantidad
):
    configurar_fotos(monkeypatch, tmp_path)
    repo = RepoFotosFalso(cantidad=cantidad)

    resultado = fotos.SubirFotosService(repo).ejecutar(
        8, [("nueva.jpg", "image/jpeg", b"abc")]
    )

    assert len(resultado) == 1
    assert resultado[0].es_principal is False
    assert repo.cantidad == cantidad


@pytest.mark.parametrize("id_caballo", [1, 2, 3, 50, 999])
def test_fotos_lista_vacia_no_guarda_archivos(
    monkeypatch, tmp_path, id_caballo
):
    configurar_fotos(monkeypatch, tmp_path)
    repo = RepoFotosFalso()

    resultado = fotos.SubirFotosService(repo).ejecutar(id_caballo, [])

    assert resultado == []
    assert repo.guardadas == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("nombre", [
    "foto.jpg", "foto.jpeg", "foto.png", "subcarpeta/foto.jpg",
    "otra/ruta/foto.png",
])
def test_fotos_elimina_archivo_existente(monkeypatch, tmp_path, nombre):
    configurar_fotos(monkeypatch, tmp_path)
    archivo = tmp_path / nombre.split("/")[-1]
    archivo.write_bytes(b"foto")
    servicio = fotos.SubirFotosService(RepoFotosFalso())

    servicio.eliminar_archivo(nombre)

    assert not archivo.exists()


@pytest.mark.parametrize("nombre", [
    "inexistente.jpg", "inexistente.png", "carpeta/no.jpg",
    "otra/foto.jpeg", "sin-archivo.png",
])
def test_fotos_eliminar_archivo_inexistente_no_falla(
    monkeypatch, tmp_path, nombre
):
    configurar_fotos(monkeypatch, tmp_path)
    servicio = fotos.SubirFotosService(RepoFotosFalso())

    assert servicio.eliminar_archivo(nombre) is None


@pytest.mark.parametrize("id_caballo", [1, 2, 10, 25, 100])
def test_fotos_promover_principal_delega_en_repositorio(
    monkeypatch, tmp_path, id_caballo
):
    configurar_fotos(monkeypatch, tmp_path)
    repo = RepoFotosFalso()
    servicio = fotos.SubirFotosService(repo)

    resultado = servicio.promover_principal(id_caballo)

    assert resultado is None
    assert repo.promociones == [id_caballo]
