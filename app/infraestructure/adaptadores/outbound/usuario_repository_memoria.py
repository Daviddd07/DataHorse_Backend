from dataclasses import replace
from threading import Lock
from typing import Optional

from app.domain.entities.Usuario import Usuario
from app.domain.exceptions import CorreoYaRegistradoError
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort


class UsuarioRepositoryMemoria(UsuarioRepositoryPort):
    """Temporal: los datos viven solo mientras el servidor está encendido."""

    def __init__(self):
        self._por_correo: dict[str, Usuario] = {}
        self._siguiente_id = 1
        self._lock = Lock()

    def find_by_email(self, correo: str) -> Optional[Usuario]:   # antes: buscar_por_correo
        return self._por_correo.get(correo)

    def create(self, usuario: Usuario) -> Usuario:               # antes: guardar
        with self._lock:
            if usuario.correo in self._por_correo:
                raise CorreoYaRegistradoError()
            guardado = replace(usuario, id_usuario=self._siguiente_id)
            self._siguiente_id += 1
            self._por_correo[guardado.correo] = guardado
            return guardado 