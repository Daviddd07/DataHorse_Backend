from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from app.domain.entities.documento_caballo import DocumentoCaballo
from app.domain.ports.in_.foto_ports import ArchivoSubido


@dataclass(frozen=True)
class DocumentoNuevo:
    tipo: str
    titulo: str
    archivo: ArchivoSubido


@dataclass(frozen=True)
class DocumentosDeCaballo:
    documentos: List[DocumentoCaballo]
    es_propietario: bool          # puede subir, eliminar y descargar


@dataclass(frozen=True)
class ArchivoDocumento:
    documento: DocumentoCaballo
    contenido: bytes


class SubirDocumentosPort(ABC):
    @abstractmethod
    def ejecutar(
        self, id_caballo: int, id_usuario: int, nuevos: List[DocumentoNuevo]
    ) -> List[DocumentoCaballo]: ...


class ListarDocumentosPort(ABC):
    @abstractmethod
    def ejecutar(self, id_caballo: int, id_usuario: int) -> DocumentosDeCaballo: ...


class ObtenerArchivoDocumentoPort(ABC):
    @abstractmethod
    def ejecutar(
        self, id_caballo: int, id_documento: int, id_usuario: int, descargar: bool
    ) -> ArchivoDocumento:
        """Ver: dueño o cualquier usuario si el caballo está publicado. Descargar: solo el dueño."""


class EliminarDocumentoPort(ABC):
    @abstractmethod
    def ejecutar(self, id_caballo: int, id_documento: int, id_usuario: int) -> None: ...
