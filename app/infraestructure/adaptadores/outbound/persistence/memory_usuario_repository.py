"""
Implementación TEMPORAL de UsuarioRepositoryPort, mientras se define
la base de datos real.

Guarda los usuarios en una lista en RAM: se pierden cada vez que
reinicias el servidor (uvicorn --reload). Sirve solo para probar el
flujo de login/registro de punta a punta.

Cuando tengas la base de datos lista, crea un archivo nuevo (por ejemplo
usuario_repository.py) que implemente UsuarioRepositoryPort igual que
este, pero usando tu motor real (SQLAlchemy, etc.), y solo cambias
esa clase en app/config/dependencies.py. Nada más se toca.
"""

import uuid

from app.domain.entities.usuario import Usuario
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort

_usuarios_en_memoria: dict[str, Usuario] = {}


class MemoryUsuarioRepository(UsuarioRepositoryPort):
    def find_by_email(self, correo: str) -> Usuario | None:
        for usuario in _usuarios_en_memoria.values():
            if usuario.correo == correo:
                return usuario
        return None

    def create(self, correo: str, password_hash: str, nombre: str) -> Usuario:
        usuario = Usuario(
            id=str(uuid.uuid4()),
            correo=correo,
            password_hash=password_hash,
            nombre=nombre,
        )
        _usuarios_en_memoria[usuario.id] = usuario
        return usuario
