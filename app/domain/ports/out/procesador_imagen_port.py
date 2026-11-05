from abc import ABC, abstractmethod


class ProcesadorImagenPort(ABC):
    @abstractmethod
    def foto_de_perfil(self, contenido: bytes) -> bytes:
        """Comprueba que el archivo sea una imagen real y la deja lista como foto de perfil
        (cuadrada, tamaño fijo, JPEG y sin metadatos). Lanza SolicitudInvalidaError si no lo es."""
