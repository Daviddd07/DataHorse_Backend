import logging
from typing import Optional

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.domain.exceptions import ConfiguracionError, NoAutenticadoError
from app.domain.ports.out.verificador_google_port import VerificadorGooglePort

logger = logging.getLogger(__name__)


class VerificadorGoogle(VerificadorGooglePort):

    def __init__(self, client_id: Optional[str]):
        self._client_id = client_id

    def verificar(self, credencial: str) -> dict:
        if not self._client_id:
            raise ConfiguracionError("GOOGLE_CLIENT_ID no está configurado")

        try:
            return google_id_token.verify_oauth2_token(
                credencial,
                google_requests.Request(),
                self._client_id,
                clock_skew_in_seconds=10,
            )
        except Exception as e:
            logger.warning("Token de Google rechazado: %r", e)
            raise NoAutenticadoError("Token de Google inválido") from e
