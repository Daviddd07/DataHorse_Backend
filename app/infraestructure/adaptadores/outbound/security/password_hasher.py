
from passlib.context import CryptContext

from app.domain.ports.out.password_hasher_port import PasswordHasherPort

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordHasher(PasswordHasherPort):
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def hash(self, plain_password: str) -> str:
        return pwd_context.hash(plain_password)
