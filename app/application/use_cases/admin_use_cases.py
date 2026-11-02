from typing import List

from app.domain.exceptions import AccesoDenegadoError, NoAutenticadoError
from app.domain.ports.in_.admin_ports import (
    ListarUsuariosAdminPort,
    ObtenerResumenAdminPort,
    VerificarAdministradorPort,
)
from app.domain.ports.out.admin_consultas_port import AdminConsultasPort
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort


class VerificarAdministradorUseCase(VerificarAdministradorPort):
    """Consulta el rol en la BD en cada solicitud: quitar el rol corta el acceso al instante."""

    def __init__(self, usuario_repo: UsuarioRepositoryPort):
        self._usuario_repo = usuario_repo

    def ejecutar(self, id_usuario: int) -> None:
        usuario = self._usuario_repo.find_by_id(id_usuario)

        if usuario is None:
            raise NoAutenticadoError("Usuario no encontrado")

        if not usuario.es_administrador():
            raise AccesoDenegadoError("Solo los administradores pueden acceder")


class ObtenerResumenAdminUseCase(ObtenerResumenAdminPort):
    def __init__(self, consultas: AdminConsultasPort, url_grafana: str = ""):
        self._consultas = consultas
        self._url_grafana = url_grafana

    def ejecutar(self) -> dict:
        # Sin URL configurada el panel oculta el botón de logs.
        return {**self._consultas.resumen(), "enlaces": {"grafana": self._url_grafana or None}}


class ListarUsuariosAdminUseCase(ListarUsuariosAdminPort):
    def __init__(self, consultas: AdminConsultasPort):
        self._consultas = consultas

    def ejecutar(self) -> List[dict]:
        return self._consultas.listar_usuarios()
