from typing import List

from app.domain.exceptions import RecursoNoEncontradoError
from app.domain.ports.in_.publicacion_ports import ListarPublicacionesPort, ObtenerPublicacionPort
from app.domain.ports.out.publicacion_consultas_port import PublicacionConsultasPort


class ListarPublicacionesUseCase(ListarPublicacionesPort):
    def __init__(self, consultas: PublicacionConsultasPort):
        self._consultas = consultas

    def ejecutar(self, id_usuario_actual: int) -> List[dict]:
        return self._consultas.listar_activas(id_usuario_actual)


class ObtenerPublicacionUseCase(ObtenerPublicacionPort):
    def __init__(self, consultas: PublicacionConsultasPort):
        self._consultas = consultas

    def ejecutar(self, id_publicacion: int, id_usuario_actual: int) -> dict:
        publicacion = self._consultas.obtener_detalle(id_publicacion, id_usuario_actual)

        if publicacion is None:
            raise RecursoNoEncontradoError("Publicación no encontrada")

        return publicacion
