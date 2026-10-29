from passlib.context import CryptContext

from app.domain.ports.out.password_hasher_port import PasswordHasherPort


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordHasher(PasswordHasherPort):

    def hashear(self, plain_password: str) -> str:
        return pwd_context.hash(plain_password)

    def verificar(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    # Alias para mantener compatibilidad con llamadas existentes
    def hash(self, plain_password: str) -> str:
        return self.hashear(plain_password)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return self.verificar(plain_password, hashed_password)
