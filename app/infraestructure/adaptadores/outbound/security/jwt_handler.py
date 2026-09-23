import os
from datetime import datetime, timedelta, timezone

import jwt

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "cambia-esto-en-produccion")
ALGORITHM = "HS256"
EXPIRE_MINUTES = 30


def create_access_token(usuario_id: str) -> str:
    payload = {
        "sub": usuario_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
