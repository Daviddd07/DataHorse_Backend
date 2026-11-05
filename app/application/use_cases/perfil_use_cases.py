import logging
from dataclasses import replace

from app.domain.entities.Usuario import Usuario
from app.domain.exceptions import DatosInvalidosError, NoAutenticadoError
from app.application.use_cases.foto_use_cases import validar_archivo
from app.domain.ports.in_.foto_ports import ArchivoSubido
from app.domain.ports.in_.perfil_ports import (
    ActualizarPerfilComando,
    ActualizarPerfilPort,
    CambiarFotoPerfilPort,
    ObtenerPerfilPort,
    QuitarFotoPerfilPort,
)
from app.domain.ports.out.almacenamiento_archivos_port import AlmacenamientoArchivosPort
from app.domain.ports.out.geocoding_port import GeocodingPort
from app.domain.ports.out.procesador_imagen_port import ProcesadorImagenPort
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort
from app.domain.services.validador_usuario import RE_TELEFONO

logger = logging.getLogger("datahorse")


def _buscar_usuario(repo: UsuarioRepositoryPort, id_usuario: int) -> Usuario:
    usuario = repo.find_by_id(id_usuario)
    if usuario is None:
        raise NoAutenticadoError("Usuario no encontrado")
    return usuario


class ObtenerPerfilUseCase(ObtenerPerfilPort):
    def __init__(self, usuario_repo: UsuarioRepositoryPort):
        self._usuario_repo = usuario_repo

    def ejecutar(self, id_usuario: int) -> Usuario:
        return _buscar_usuario(self._usuario_repo, id_usuario)


class ActualizarPerfilUseCase(ActualizarPerfilPort):
    """Cambia nombre, teléfono y ubicación. La ubicación se geocodifica como en el registro
    para que la proximidad del marketplace siga funcionando."""

    def __init__(self, usuario_repo: UsuarioRepositoryPort, geocoding: GeocodingPort):
        self._usuario_repo = usuario_repo
        self._geocoding = geocoding

    def ejecutar(self, id_usuario: int, comando: ActualizarPerfilComando) -> Usuario:
        usuario = _buscar_usuario(self._usuario_repo, id_usuario)

        nombre = " ".join(comando.nombre.split())
        telefono = (comando.telefono or "").strip() or None
        ciudad = (comando.ciudad or "").strip() or None
        departamento = (comando.departamento or "").strip() or None

        if not 2 <= len(nombre) <= 120:
            raise DatosInvalidosError("nombre", "El nombre debe tener entre 2 y 120 caracteres.")
        if telefono and not RE_TELEFONO.match(telefono):
            raise DatosInvalidosError("telefono", "Teléfono no válido.")
        if bool(ciudad) != bool(departamento):
            raise DatosInvalidosError("ubicacion", "Elige el departamento y la ciudad.")

        cambios = {"nombre": nombre, "telefono": telefono}

        # Solo se vuelve a geocodificar si la ubicación cambió
        if (ciudad, departamento) != (usuario.ciudad, usuario.departamento):
            ubicacion = f"{ciudad}, {departamento}" if ciudad else None
            geo = self._geocoding.geocodificar(ubicacion) if ubicacion else None
            cambios.update(
                ubicacion=ubicacion,
                ciudad=ciudad,
                departamento=departamento,
                ubicacion_texto=geo.texto if geo else ubicacion,
                ubicacion_lat=geo.lat if geo else None,
                ubicacion_lng=geo.lng if geo else None,
            )

        actualizado = replace(usuario, **cambios)
        self._usuario_repo.actualizar_perfil(actualizado)
        return actualizado


def _borrar_archivo(almacenamiento: AlmacenamientoArchivosPort, ruta: str) -> None:
    # La base ya quedó bien: si el archivo viejo no se puede borrar solo se avisa en el log
    try:
        almacenamiento.eliminar(ruta)
    except OSError:
        logger.warning("No se pudo borrar la foto de perfil anterior %s", ruta)


class CambiarFotoPerfilUseCase(CambiarFotoPerfilPort):
    """Valida la imagen, la normaliza (cuadrada, JPEG, sin metadatos), la guarda y borra la anterior."""

    def __init__(
        self,
        usuario_repo: UsuarioRepositoryPort,
        almacenamiento: AlmacenamientoArchivosPort,
        procesador: ProcesadorImagenPort,
    ):
        self._usuario_repo = usuario_repo
        self._almacenamiento = almacenamiento
        self._procesador = procesador

    def ejecutar(self, id_usuario: int, archivo: ArchivoSubido) -> Usuario:
        usuario = _buscar_usuario(self._usuario_repo, id_usuario)

        validar_archivo(archivo)  # tipo, tamaño y extensión, igual que las fotos de caballos
        foto = self._procesador.foto_de_perfil(archivo.contenido)
        ruta = self._almacenamiento.guardar(".jpg", foto)

        try:
            self._usuario_repo.actualizar_foto_perfil(id_usuario, ruta)
        except Exception:
            self._almacenamiento.eliminar(ruta)  # no dejar el archivo nuevo huérfano
            raise

        if usuario.foto_perfil:
            _borrar_archivo(self._almacenamiento, usuario.foto_perfil)

        return replace(usuario, foto_perfil=ruta)


class QuitarFotoPerfilUseCase(QuitarFotoPerfilPort):
    def __init__(self, usuario_repo: UsuarioRepositoryPort, almacenamiento: AlmacenamientoArchivosPort):
        self._usuario_repo = usuario_repo
        self._almacenamiento = almacenamiento

    def ejecutar(self, id_usuario: int) -> Usuario:
        usuario = _buscar_usuario(self._usuario_repo, id_usuario)

        if usuario.foto_perfil:
            self._usuario_repo.actualizar_foto_perfil(id_usuario, None)
            _borrar_archivo(self._almacenamiento, usuario.foto_perfil)

        return replace(usuario, foto_perfil=None)
