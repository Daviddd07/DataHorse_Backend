from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.domain.ports.out.password_hasher_port import PasswordHasherPort


class Argon2PasswordHasher(PasswordHasherPort):
    def __init__(self):
        self._ph = PasswordHasher()

    def hashear(self, contrasena: str) -> str:
        return self._ph.hash(contrasena)

    def verificar(self, contrasena: str, hash_guardado: str) -> bool:
        try:
            return self._ph.verify(hash_guardado, contrasena)
        except (VerificationError, InvalidHashError):
            return False
