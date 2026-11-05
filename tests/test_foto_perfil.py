"""Pruebas de la foto de perfil: casos de uso, adaptador de Pillow, repositorio y API."""
from datetime import date
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

import main
from app.application.use_cases.perfil_use_cases import CambiarFotoPerfilUseCase, QuitarFotoPerfilUseCase
from app.config import dependencies as deps
from app.config.settings import FOTO_MAX_SIZE
from app.domain.entities.Usuario import Usuario
from app.domain.exceptions import NoAutenticadoError, SolicitudInvalidaError
from app.domain.ports.in_.foto_ports import ArchivoSubido
from app.infraestructure.adaptadores.outbound.persistence import usuario_repository_mysql as usuarios


def usuario(**cambios):
    datos = dict(
        id_usuario=7, id_rol=2, nombre="Ana", correo="ana@test.com", contrasena="hash",
        telefono=None, ubicacion=None, fecha_registro=date(2026, 9, 24), estado="activo",
        foto_perfil=None,
    )
    datos.update(cambios)
    return Usuario(**datos)


def archivo(**cambios):
    datos = dict(nombre="yo.png", content_type="image/png", contenido=b"bytes-originales")
    datos.update(cambios)
    return ArchivoSubido(**datos)


@pytest.fixture
def repo():
    r = Mock()
    r.find_by_id.return_value = usuario()
    return r


@pytest.fixture
def almacenamiento():
    a = Mock()
    a.guardar.return_value = "/uploads/perfiles/nueva.jpg"
    return a


@pytest.fixture
def procesador():
    p = Mock()
    p.foto_de_perfil.return_value = b"jpeg-normalizado"
    return p


# ======================================================
# CAMBIAR FOTO
# ======================================================

def test_cambiar_foto_guarda_la_imagen_normalizada(repo, almacenamiento, procesador):
    actualizado = CambiarFotoPerfilUseCase(repo, almacenamiento, procesador).ejecutar(7, archivo())

    procesador.foto_de_perfil.assert_called_once_with(b"bytes-originales")
    almacenamiento.guardar.assert_called_once_with(".jpg", b"jpeg-normalizado")
    repo.actualizar_foto_perfil.assert_called_once_with(7, "/uploads/perfiles/nueva.jpg")
    assert actualizado.foto_perfil == "/uploads/perfiles/nueva.jpg"
    almacenamiento.eliminar.assert_not_called()


def test_cambiar_foto_borra_la_anterior(repo, almacenamiento, procesador):
    repo.find_by_id.return_value = usuario(foto_perfil="/uploads/perfiles/vieja.jpg")

    CambiarFotoPerfilUseCase(repo, almacenamiento, procesador).ejecutar(7, archivo())

    almacenamiento.eliminar.assert_called_once_with("/uploads/perfiles/vieja.jpg")


def test_cambiar_foto_no_falla_si_no_puede_borrar_la_anterior(repo, almacenamiento, procesador):
    repo.find_by_id.return_value = usuario(foto_perfil="/uploads/perfiles/vieja.jpg")
    almacenamiento.eliminar.side_effect = OSError("bloqueado")

    actualizado = CambiarFotoPerfilUseCase(repo, almacenamiento, procesador).ejecutar(7, archivo())

    assert actualizado.foto_perfil == "/uploads/perfiles/nueva.jpg"


def test_cambiar_foto_no_deja_archivos_huerfanos_si_falla_la_base(repo, almacenamiento, procesador):
    repo.actualizar_foto_perfil.side_effect = RuntimeError("BD caída")

    with pytest.raises(RuntimeError):
        CambiarFotoPerfilUseCase(repo, almacenamiento, procesador).ejecutar(7, archivo())

    almacenamiento.eliminar.assert_called_once_with("/uploads/perfiles/nueva.jpg")


@pytest.mark.parametrize(
    "malo",
    [
        {"content_type": "application/pdf"},
        {"nombre": "yo.gif"},
        {"contenido": b"x" * (FOTO_MAX_SIZE + 1)},
    ],
)
def test_cambiar_foto_valida_tipo_extension_y_tamano(repo, almacenamiento, procesador, malo):
    with pytest.raises(SolicitudInvalidaError):
        CambiarFotoPerfilUseCase(repo, almacenamiento, procesador).ejecutar(7, archivo(**malo))

    procesador.foto_de_perfil.assert_not_called()
    almacenamiento.guardar.assert_not_called()


def test_cambiar_foto_rechaza_lo_que_no_es_imagen(repo, almacenamiento, procesador):
    procesador.foto_de_perfil.side_effect = SolicitudInvalidaError("El archivo no es una imagen válida")

    with pytest.raises(SolicitudInvalidaError):
        CambiarFotoPerfilUseCase(repo, almacenamiento, procesador).ejecutar(7, archivo())

    almacenamiento.guardar.assert_not_called()
    repo.actualizar_foto_perfil.assert_not_called()


def test_cambiar_foto_usuario_inexistente(repo, almacenamiento, procesador):
    repo.find_by_id.return_value = None
    with pytest.raises(NoAutenticadoError):
        CambiarFotoPerfilUseCase(repo, almacenamiento, procesador).ejecutar(7, archivo())


# ======================================================
# QUITAR FOTO
# ======================================================

def test_quitar_foto_borra_archivo_y_ruta(repo, almacenamiento):
    repo.find_by_id.return_value = usuario(foto_perfil="/uploads/perfiles/vieja.jpg")

    actualizado = QuitarFotoPerfilUseCase(repo, almacenamiento).ejecutar(7)

    repo.actualizar_foto_perfil.assert_called_once_with(7, None)
    almacenamiento.eliminar.assert_called_once_with("/uploads/perfiles/vieja.jpg")
    assert actualizado.foto_perfil is None


def test_quitar_foto_sin_foto_no_hace_nada(repo, almacenamiento):
    QuitarFotoPerfilUseCase(repo, almacenamiento).ejecutar(7)

    repo.actualizar_foto_perfil.assert_not_called()
    almacenamiento.eliminar.assert_not_called()


# ======================================================
# ADAPTADOR DE PILLOW (se salta si Pillow no está instalado)
# ======================================================

def _imagen(formato="PNG", tamano=(800, 400), modo="RGB", exif_orientacion=None):
    Image = pytest.importorskip("PIL.Image")
    imagen = Image.new(modo, tamano, (200, 30, 30, 0) if modo == "RGBA" else (200, 30, 30))
    salida = BytesIO()
    extra = {}
    if exif_orientacion:
        exif = Image.Exif()
        exif[0x0112] = exif_orientacion
        extra["exif"] = exif
    imagen.save(salida, formato, **extra)
    return salida.getvalue()


@pytest.fixture
def pillow():
    pytest.importorskip("PIL")
    from app.infraestructure.adaptadores.outbound.imagenes.pillow_procesador_imagen import (
        PillowProcesadorImagen,
    )
    return PillowProcesadorImagen(lado=512)


def test_pillow_recorta_en_cuadrado_y_guarda_jpeg(pillow):
    from PIL import Image

    resultado = Image.open(BytesIO(pillow.foto_de_perfil(_imagen(tamano=(800, 400)))))

    assert resultado.format == "JPEG"
    assert resultado.size == (512, 512)


def test_pillow_quita_los_metadatos(pillow):
    from PIL import Image

    entrada = _imagen(formato="JPEG", exif_orientacion=6)
    resultado = Image.open(BytesIO(pillow.foto_de_perfil(entrada)))

    assert not resultado.getexif()


def test_pillow_pone_fondo_blanco_a_las_transparencias(pillow):
    from PIL import Image

    resultado = Image.open(BytesIO(pillow.foto_de_perfil(_imagen(modo="RGBA", tamano=(64, 64)))))

    rojo, verde, azul = resultado.convert("RGB").getpixel((32, 32))
    assert min(rojo, verde, azul) > 240


@pytest.mark.parametrize("contenido", [b"no soy una imagen", b"\x89PNG\r\n\x1a\n roto"])
def test_pillow_rechaza_archivos_que_no_son_imagenes(pillow, contenido):
    with pytest.raises(SolicitudInvalidaError, match="no es una imagen"):
        pillow.foto_de_perfil(contenido)


def test_pillow_rechaza_imagenes_gigantes():
    pytest.importorskip("PIL")
    from app.infraestructure.adaptadores.outbound.imagenes.pillow_procesador_imagen import (
        PillowProcesadorImagen,
    )

    with pytest.raises(SolicitudInvalidaError, match="demasiado grande"):
        PillowProcesadorImagen(lado=512, max_pixeles=100).foto_de_perfil(_imagen(tamano=(20, 20)))


# ======================================================
# REPOSITORIO MYSQL
# ======================================================

def test_repositorio_actualiza_solo_la_foto():
    db = MagicMock()
    sesion = MagicMock()
    sesion.__enter__.return_value = db

    with patch.object(usuarios, "SessionLocal", return_value=sesion):
        usuarios.UsuarioRepositoryMySQL().actualizar_foto_perfil(7, "/uploads/perfiles/x.jpg")

    sentencia = str(db.execute.call_args.args[0])
    assert "foto_perfil" in sentencia
    assert "nombre" not in sentencia
    db.commit.assert_called_once()


# ======================================================
# API
# ======================================================

@pytest.fixture
def api():
    tokens = Mock()
    tokens.decodificar.side_effect = lambda t: {"valido": "7"}.get(t)
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


def test_api_subir_foto(api):
    caso = api.usar(deps.get_cambiar_foto_perfil_use_case)
    # El almacenamiento guarda la ruta sin '/' inicial; la API la entrega lista para la URL
    caso.ejecutar.return_value = usuario(foto_perfil="uploads/perfiles/nueva.jpg")

    respuesta = api.put("/api/v1/cuenta/foto", files={"foto": ("yo.png", b"bytes", "image/png")})

    assert respuesta.status_code == 200
    assert respuesta.json()["foto_perfil"] == "/uploads/perfiles/nueva.jpg"
    id_usuario, recibido = caso.ejecutar.call_args.args
    assert id_usuario == 7
    assert (recibido.nombre, recibido.content_type, recibido.contenido) == ("yo.png", "image/png", b"bytes")


def test_api_subir_foto_lee_como_maximo_un_byte_de_mas(api):
    caso = api.usar(deps.get_cambiar_foto_perfil_use_case)
    caso.ejecutar.return_value = usuario()

    api.put("/api/v1/cuenta/foto", files={"foto": ("yo.png", b"x" * (FOTO_MAX_SIZE + 50), "image/png")})

    assert len(caso.ejecutar.call_args.args[1].contenido) == FOTO_MAX_SIZE + 1


def test_api_subir_foto_invalida(api):
    api.usar(deps.get_cambiar_foto_perfil_use_case).ejecutar.side_effect = SolicitudInvalidaError(
        "El archivo no es una imagen válida"
    )

    respuesta = api.put("/api/v1/cuenta/foto", files={"foto": ("yo.png", b"x", "image/png")})

    assert respuesta.status_code == 400
    assert "no es una imagen" in respuesta.json()["detail"]


def test_api_quitar_foto(api):
    caso = api.usar(deps.get_quitar_foto_perfil_use_case)
    caso.ejecutar.return_value = usuario()

    respuesta = api.delete("/api/v1/cuenta/foto")

    assert respuesta.status_code == 200
    assert respuesta.json()["foto_perfil"] is None
    caso.ejecutar.assert_called_once_with(7)


def test_api_foto_exige_sesion(api):
    api.cookies.clear()
    assert api.delete("/api/v1/cuenta/foto").status_code == 401
    assert api.put("/api/v1/cuenta/foto", files={"foto": ("a.png", b"x", "image/png")}).status_code == 401


def test_api_entrega_la_foto_con_barra_inicial_en_perfil_y_en_me(api):
    guardado = usuario(foto_perfil="uploads/perfiles/a.jpg")
    api.usar(deps.get_obtener_perfil_use_case).ejecutar.return_value = guardado
    api.usar(deps.get_usuario_actual_use_case).ejecutar.return_value = guardado

    assert api.get("/api/v1/cuenta/perfil").json()["foto_perfil"] == "/uploads/perfiles/a.jpg"
    assert api.get("/auth/me").json()["foto_perfil"] == "/uploads/perfiles/a.jpg"


def test_ruta_publica():
    from app.infraestructure.adaptadores.inbound.rest.schemas import ruta_publica

    assert ruta_publica("uploads/perfiles/a.jpg") == "/uploads/perfiles/a.jpg"
    assert ruta_publica("/uploads/perfiles/a.jpg") == "/uploads/perfiles/a.jpg"
    assert ruta_publica(None) is None
