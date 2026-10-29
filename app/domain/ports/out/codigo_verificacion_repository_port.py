from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from app.domain.entities.codigo_verificacion import CodigoVerificacion


class CodigoVerificacionRepositoryPort(ABC):
    @abstractmethod
    def reemplazar(
        self,
        id_usuario: int,
        tipo: str,
        codigo_hash: str,
        fecha_expiracion: datetime,
    ) -> None:
        """Invalida los códigos vigentes del mismo tipo y guarda el nuevo."""

    @abstractmethod
    def obtener_vigente(self, id_usuario: int, tipo: str) -> Optional[CodigoVerificacion]: ...

    @abstractmethod
    def marcar_usado(self, id_verificacion: int) -> None: ...

    @abstractmethod
    def registrar_intento_fallido(self, id_verificacion: int, max_intentos: int) -> None: ...
