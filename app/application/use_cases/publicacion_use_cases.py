from typing import List, Optional

from app.domain.exceptions import RecursoNoEncontradoError
from app.domain.ports.in_.publicacion_ports import ListarPublicacionesPort, ObtenerPublicacionPort
from app.domain.ports.out.publicacion_consultas_port import PublicacionConsultasPort


class ListarPublicacionesUseCase(ListarPublicacionesPort):
    def __init__(self, consultas: PublicacionConsultasPort):
        self._consultas = consultas

    def ejecutar(self, id_usuario_actual: Optional[int]) -> List[dict]:
        """Marketplace público: sin sesión (None) se ven todas, sin marcar "mía" ni "favorita"."""
        return self._consultas.listar_activas(id_usuario_actual)


class ObtenerPublicacionUseCase(ObtenerPublicacionPort):
    def __init__(self, consultas: PublicacionConsultasPort):
        self._consultas = consultas

    def ejecutar(self, id_publicacion: int, id_usuario_actual: Optional[int]) -> dict:
        publicacion = self._consultas.obtener_detalle(id_publicacion, id_usuario_actual)

        if publicacion is None:
            raise RecursoNoEncontradoError("Publicación no encontrada")

        if id_usuario_actual is None:
            # Visitante sin sesión: ve el caballo, pero no el contacto del vendedor
            # (evita que bots recojan teléfonos de un marketplace público).
            publicacion = {**publicacion, "propietario_telefono": None}

        return publicacion
