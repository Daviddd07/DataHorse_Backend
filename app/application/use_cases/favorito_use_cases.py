from datetime import date
from typing import Optional

from app.domain.exceptions import RecursoNoEncontradoError
from app.domain.ports.in_.favorito_ports import AgregarFavoritoPort, QuitarFavoritoPort
from app.domain.ports.out.auditoria_port import AuditoriaPort
from app.domain.ports.out.caballo_repository_port import CaballoRepositoryPort
from app.domain.ports.out.favorito_repository_port import FavoritoRepositoryPort

MODULO_FAVORITOS = "FAVORITOS"


class AgregarFavoritoUseCase(AgregarFavoritoPort):
    def __init__(
        self,
        caballo_repo: CaballoRepositoryPort,
        favorito_repo: FavoritoRepositoryPort,
        auditoria: AuditoriaPort,
    ):
        self._caballo_repo = caballo_repo
        self._favorito_repo = favorito_repo
        self._auditoria = auditoria

    def ejecutar(self, id_usuario: int, id_caballo: int) -> Optional[int]:
        if not self._caballo_repo.existe(id_caballo):
            raise RecursoNoEncontradoError("Caballo no encontrado")

        if self._favorito_repo.existe(id_usuario, id_caballo):
            return None

        id_favorito = self._favorito_repo.agregar(id_usuario, id_caballo, date.today())

        self._auditoria.registrar(
            accion="AGREGAR_FAVORITO",
            modulo=MODULO_FAVORITOS,
            resultado="EXITOSO",
            usuario_id=id_usuario,
            detalle=f"Se agregó el caballo {id_caballo} a favoritos.",
        )

        return id_favorito


class QuitarFavoritoUseCase(QuitarFavoritoPort):
    def __init__(self, favorito_repo: FavoritoRepositoryPort, auditoria: AuditoriaPort):
        self._favorito_repo = favorito_repo
        self._auditoria = auditoria

    def ejecutar(self, id_usuario: int, id_caballo: int) -> bool:
        if self._favorito_repo.quitar(id_usuario, id_caballo) == 0:
            return False

        self._auditoria.registrar(
            accion="QUITAR_FAVORITO",
            modulo=MODULO_FAVORITOS,
            resultado="EXITOSO",
            usuario_id=id_usuario,
            detalle=f"Se quitó el caballo {id_caballo} de favoritos.",
        )

        return True
