from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.domain.ports.out.password_hasher_port import PasswordHasherPort


class Argon2PasswordHasher(PasswordHasherPort):
    # Argon2id con la configuración mínima recomendada por OWASP (19 MiB, 2 pasadas, 1 hilo).
    # Los valores por defecto de argon2-cffi (64 MiB, t=3, p=4) costaban ~3x más CPU por login
    # y limitaban el servidor a ~17 logins/s en las pruebas de carga (E1, E5, E9).
    # Los hashes guardados con la configuración anterior siguen verificando: cada hash
    # incluye sus propios parámetros.
    TIME_COST = 2
    MEMORY_COST_KIB = 19 * 1024
    PARALLELISM = 1

    def __init__(self):
        self._ph = PasswordHasher(
            time_cost=self.TIME_COST,
            memory_cost=self.MEMORY_COST_KIB,
            parallelism=self.PARALLELISM,
        )

    def hashear(self, contrasena: str) -> str:
        return self._ph.hash(contrasena)

    def verificar(self, contrasena: str, hash_guardado: str) -> bool:
        try:
            return self._ph.verify(hash_guardado, contrasena)
        except (VerificationError, InvalidHashError):
            return False
