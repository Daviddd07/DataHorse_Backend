from dataclasses import dataclass


@dataclass
class Usuario:
    id: str
    correo: str
    password_hash: str
    nombre: str
