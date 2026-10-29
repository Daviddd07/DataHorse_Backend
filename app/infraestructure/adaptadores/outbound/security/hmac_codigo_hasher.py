import hashlib
import hmac
from typing import Optional

from app.domain.exceptions import ConfiguracionError
from app.domain.ports.out.codigo_hasher_port import CodigoHasherPort


class HmacCodigoHasher(CodigoHasherPort):
    """Guarda los códigos como HMAC-SHA256 para no tenerlos en texto plano."""

    def __init__(self, secreto: Optional[str]):
        self._secreto = secreto

    def hashear(self, codigo: str) -> str:
        if not self._secreto:
            raise ConfiguracionError("CODIGO_SECRET no está configurado")

        return hmac.new(
            self._secreto.encode("utf-8"),
            codigo.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
