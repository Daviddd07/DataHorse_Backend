from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities.documento_caballo import ContextoCaballo, DocumentoCaballo


class DocumentoRepositoryPort(ABC):
    @abstractmethod
    def guardar(self, documento: DocumentoCaballo) -> DocumentoCaballo:
        """Persiste el documento y lo devuelve con id y fecha asignados."""

    @abstractmethod
    def listar_por_caballo(self, id_caballo: int) -> List[DocumentoCaballo]: ...

    @abstractmethod
    def contar_por_caballo(self, id_caballo: int) -> int: ...

    @abstractmethod
    def obtener(self, id_caballo: int, id_documento: int) -> Optional[DocumentoCaballo]:
        """El documento solo si pertenece a ese caballo."""

    @abstractmethod
    def eliminar(self, id_documento: int) -> None: ...

    @abstractmethod
    def contexto_caballo(self, id_caballo: int) -> Optional[ContextoCaballo]:
        """Dueño, si está eliminado y si tiene una publicación activa. None si no existe."""
