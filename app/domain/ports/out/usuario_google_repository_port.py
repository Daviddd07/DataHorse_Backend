from abc import ABC, abstractmethod
from typing import Optional


class UsuarioGoogleRepositoryPort(ABC):
    @abstractmethod
    def obtener_id_usuario(self, google_sub: str) -> Optional[int]: ...

    @abstractmethod
    def obtener_sub(self, id_usuario: int) -> Optional[str]: ...

    @abstractmethod
    def vincular(self, id_usuario: int, google_sub: str) -> None: ...
