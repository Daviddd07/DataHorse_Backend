from typing import List

from app.domain.entities.Raza import Raza
from app.domain.ports.in_.listar_razas_port import ListarRazasPort
from app.domain.ports.out.raza_repository_port import RazaRepositoryPort


class ListarRazasUseCase(ListarRazasPort):
    def __init__(self, raza_repo: RazaRepositoryPort):
        self._raza_repo = raza_repo

    def ejecutar(self) -> List[Raza]:
        return self._raza_repo.find_all()