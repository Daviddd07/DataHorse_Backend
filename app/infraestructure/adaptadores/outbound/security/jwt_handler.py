import os

from datetime import (
    datetime,
    timedelta,
    timezone,
)

import jwt

from dotenv import load_dotenv


# ======================================================
# VARIABLES DE ENTORNO
# ======================================================

load_dotenv()


SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "cambia-esto-en-produccion",
)

ALGORITHM = os.getenv(
    "ALGORITHM",
    "HS256",
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "30",
    )
)


# ======================================================
# CREAR TOKEN
# ======================================================

def create_access_token(
    usuario_id: int | str,
) -> str:

    expiracion = (
        datetime.now(
            timezone.utc
        )
        +
        timedelta(
            minutes=
                ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )


    payload = {

        # IMPORTANTE:
        # JWT exige que "sub" sea string.
        "sub":
            str(usuario_id),

        "exp":
            expiracion,
    }


    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


# ======================================================
# DECODIFICAR TOKEN
# ======================================================

def decode_access_token(
    token: str,
) -> str | None:

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[
                ALGORITHM
            ],
        )


        usuario_id = payload.get(
            "sub"
        )


        if usuario_id is None:

            return None


        return str(
            usuario_id
        )


    except jwt.PyJWTError as e:

        print(
            "ERROR JWT:",
            repr(e),
        )

        return None