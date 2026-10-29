from datetime import date
from unittest.mock import Mock

import pytest

from app.application.use_cases.favorito_use_cases import (
    AgregarFavoritoUseCase,
    QuitarFavoritoUseCase,
)
from app.application.use_cases.foto_use_cases import (
    EliminarFotoUseCase,
    SubirFotosUseCase,
    validar_archivo,
)
from app.application.use_cases.publicacion_use_cases import (
    ListarPublicacionesUseCase,
    ObtenerPublicacionUseCase,
)
from app.domain.entities.Caballo import Caballo
from app.domain.entities.foto_caballo import FotoCaballo
from app.domain.exceptions import (
    ErrorInternoError,
    RecursoNoEncontradoError,
    SolicitudInvalidaError,
)
from app.domain.ports.in_.foto_ports import ArchivoSubido

CABALLO = Caballo(
    id_caballo=5, id_raza=1, id_propietario=10, nombre="Lucero", sexo="Macho",
    fecha_nacimiento=date(2020, 1, 1), altura=1.6, color="Castaño",
    ubicacion="Bogotá", descripcion="desc", disponibilidad="Disponible",
)


def archivo(nombre="a.jpg", tipo="image/jpeg", contenido=b"data"):
    return ArchivoSubido(nombre=nombre, content_type=tipo, contenido=contenido)


@pytest.fixture
def deps():
    caballo_repo, foto_repo, almacenamiento, auditoria = Mock(), Mock(), Mock(), Mock()
    caballo_repo.obtener_de_propietario.return_value = CABALLO
    foto_repo.contar_por_caballo.return_value = 0
    foto_repo.guardar.side_effect = lambda f: f
    almacenamiento.guardar.side_effect = lambda ext, _: f"uploads/caballos/x{ext}"
    return caballo_repo, foto_repo, almacenamiento, auditoria


# ======================================================
# VALIDACIÓN DE ARCHIVOS
# ======================================================

@pytest.mark.parametrize(
    ("entrada", "mensaje"),
    [
        (archivo(tipo="text/plain"), "Tipo no permitido: text/plain"),
        (archivo(contenido=b"x" * (5 * 1024 * 1024 + 1)), "a.jpg excede 5MB"),
        (archivo(nombre="a.gif"), "Extensión no permitida: .gif"),
    ],
)
def test_validar_archivo_rechaza(entrada, mensaje):
    with pytest.raises(SolicitudInvalidaError, match=mensaje):
        validar_archivo(entrada)


def test_validar_archivo_devuelve_extension_minuscula():
    assert validar_archivo(archivo(nombre="FOTO.PNG", tipo="image/png")) == ".png"


# ======================================================
# SUBIR FOTOS
# ======================================================

def test_subir_fotos_primera_es_principal(deps):
    caballo_repo, foto_repo, almacenamiento, auditoria = deps

    fotos = SubirFotosUseCase(*deps).ejecutar(5, 10, [archivo(), archivo(nombre="b.png", tipo="image/png")])

    assert [f.es_principal for f in fotos] == [True, False]
    assert [f.orden for f in fotos] == [0, 1]
    assert fotos[1].ruta == "uploads/caballos/x.png"
    assert auditoria.registrar.call_args.kwargs["resultado"] == "EXITOSO"


def test_subir_fotos_no_reemplaza_principal_existente(deps):
    _, foto_repo, _, _ = deps
    foto_repo.contar_por_caballo.return_value = 2

    fotos = SubirFotosUseCase(*deps).ejecutar(5, 10, [archivo()])

    assert fotos[0].es_principal is False


def test_subir_fotos_invalida_no_guarda_nada_y_audita(deps):
    _, foto_repo, almacenamiento, auditoria = deps

    with pytest.raises(SolicitudInvalidaError):
        SubirFotosUseCase(*deps).ejecutar(5, 10, [archivo(), archivo(nombre="a.gif")])

    almacenamiento.guardar.assert_not_called()
    foto_repo.guardar.assert_not_called()
    assert auditoria.registrar.call_args.kwargs["resultado"] == "FALLIDO"


def test_subir_fotos_caballo_ajeno(deps):
    caballo_repo = deps[0]
    caballo_repo.obtener_de_propietario.return_value = None

    with pytest.raises(RecursoNoEncontradoError):
        SubirFotosUseCase(*deps).ejecutar(5, 10, [archivo()])


# ======================================================
# ELIMINAR FOTO
# ======================================================

FOTO = FotoCaballo(id_foto=1, id_caballo=5, ruta="uploads/caballos/a.jpg", es_principal=True, orden=0)


def test_eliminar_foto_exitoso(deps):
    _, foto_repo, almacenamiento, auditoria = deps
    foto_repo.obtener_por_id.return_value = FOTO

    EliminarFotoUseCase(*deps).ejecutar(5, 1, 10)

    foto_repo.eliminar.assert_called_once_with(1)
    almacenamiento.eliminar.assert_called_once_with("uploads/caballos/a.jpg")
    foto_repo.promover_principal.assert_called_once_with(5)
    assert auditoria.registrar.call_args.kwargs["resultado"] == "EXITOSO"


@pytest.mark.parametrize("foto", [None, FotoCaballo(1, 99, "r", False, 0)])
def test_eliminar_foto_no_encontrada_o_de_otro_caballo(deps, foto):
    _, foto_repo, _, _ = deps
    foto_repo.obtener_por_id.return_value = foto

    with pytest.raises(RecursoNoEncontradoError, match="Foto no encontrada"):
        EliminarFotoUseCase(*deps).ejecutar(5, 1, 10)

    foto_repo.eliminar.assert_not_called()


def test_eliminar_foto_falla_borrado_de_archivo(deps):
    _, foto_repo, almacenamiento, auditoria = deps
    foto_repo.obtener_por_id.return_value = FOTO
    almacenamiento.eliminar.side_effect = OSError("disco")

    with pytest.raises(ErrorInternoError, match="archivo físico"):
        EliminarFotoUseCase(*deps).ejecutar(5, 1, 10)

    foto_repo.promover_principal.assert_not_called()
    assert auditoria.registrar.call_args.kwargs["resultado"] == "FALLIDO"


# ======================================================
# FAVORITOS
# ======================================================

def test_agregar_favorito_nuevo():
    caballos, favoritos, auditoria = Mock(), Mock(), Mock()
    caballos.existe.return_value = True
    favoritos.existe.return_value = False
    favoritos.agregar.return_value = 3

    assert AgregarFavoritoUseCase(caballos, favoritos, auditoria).ejecutar(10, 5) == 3
    favoritos.agregar.assert_called_once_with(10, 5, date.today())
    auditoria.registrar.assert_called_once()


def test_agregar_favorito_existente():
    caballos, favoritos, auditoria = Mock(), Mock(), Mock()
    caballos.existe.return_value = True
    favoritos.existe.return_value = True

    assert AgregarFavoritoUseCase(caballos, favoritos, auditoria).ejecutar(10, 5) is None
    favoritos.agregar.assert_not_called()


def test_agregar_favorito_caballo_inexistente():
    caballos = Mock()
    caballos.existe.return_value = False

    with pytest.raises(RecursoNoEncontradoError):
        AgregarFavoritoUseCase(caballos, Mock(), Mock()).ejecutar(10, 5)


@pytest.mark.parametrize(("filas", "esperado", "auditado"), [(1, True, True), (0, False, False)])
def test_quitar_favorito(filas, esperado, auditado):
    favoritos, auditoria = Mock(), Mock()
    favoritos.quitar.return_value = filas

    assert QuitarFavoritoUseCase(favoritos, auditoria).ejecutar(10, 5) is esperado
    assert auditoria.registrar.called is auditado


# ======================================================
# PUBLICACIONES
# ======================================================

def test_listar_publicaciones():
    consultas = Mock()
    consultas.listar_activas.return_value = [{"id_publicacion": 1}]

    assert ListarPublicacionesUseCase(consultas).ejecutar(10) == [{"id_publicacion": 1}]


def test_obtener_publicacion():
    consultas = Mock()
    consultas.obtener_detalle.return_value = {"id_publicacion": 1}

    assert ObtenerPublicacionUseCase(consultas).ejecutar(1, 10) == {"id_publicacion": 1}


def test_obtener_publicacion_no_encontrada():
    consultas = Mock()
    consultas.obtener_detalle.return_value = None

    with pytest.raises(RecursoNoEncontradoError, match="Publicación no encontrada"):
        ObtenerPublicacionUseCase(consultas).ejecutar(1, 10)
