import logging
from typing import Optional

import requests

from app.domain.exceptions import ConfiguracionError, ServicioExternoError
from app.domain.ports.out.enviador_codigo_port import EnviadorCodigoPort

logger = logging.getLogger(__name__)

MAILJET_URL = "https://api.mailjet.com/v3.1/send"

PLANTILLAS = {
    "REGISTRO": (
        "Verifica tu cuenta de DataHorse",
        "Verifica tu correo",
        "Usa este código para activar tu cuenta de DataHorse.",
    ),
    "RECUPERAR_PASSWORD": (
        "Recuperación de contraseña - DataHorse",
        "Recupera tu contraseña",
        "Usa este código para establecer una nueva contraseña.",
    ),
}


def _html(titulo: str, nombre: str, mensaje: str, codigo: str, minutos: int) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: auto; padding: 30px;">
        <h2>{titulo}</h2>
        <p>Hola {nombre},</p>
        <p>{mensaje}</p>
        <div style="text-align: center; margin: 30px 0;">
            <strong style="font-size: 32px; letter-spacing: 8px;">{codigo}</strong>
        </div>
        <p>Este código vence en {minutos} minutos.</p>
        <p>Si no solicitaste este código, ignora este mensaje.</p>
        <p><strong>DataHorse</strong></p>
    </div>
    """


class MailjetEnviadorCodigo(EnviadorCodigoPort):

    def __init__(
        self,
        api_key: Optional[str],
        secret_key: Optional[str],
        remitente: Optional[str],
        nombre_remitente: str = "DataHorse",
        timeout: int = 15,
    ):
        self._api_key = api_key
        self._secret_key = secret_key
        self._remitente = remitente
        self._nombre_remitente = nombre_remitente
        self._timeout = timeout

    def enviar(
        self,
        correo: str,
        nombre: str,
        codigo: str,
        tipo: str,
        minutos_validez: int,
    ) -> None:
        if not all([self._api_key, self._secret_key, self._remitente]):
            raise ConfiguracionError("Mailjet no está configurado completamente")

        asunto, titulo, mensaje = PLANTILLAS.get(tipo, PLANTILLAS["RECUPERAR_PASSWORD"])

        payload = {
            "Messages": [
                {
                    "From": {"Email": self._remitente, "Name": self._nombre_remitente},
                    "To": [{"Email": correo, "Name": nombre}],
                    "Subject": asunto,
                    "TextPart": (
                        f"Hola {nombre}. Tu código DataHorse es {codigo}. "
                        f"Vence en {minutos_validez} minutos."
                    ),
                    "HTMLPart": _html(titulo, nombre, mensaje, codigo, minutos_validez),
                }
            ]
        }

        try:
            respuesta = requests.post(
                MAILJET_URL,
                auth=(self._api_key, self._secret_key),
                json=payload,
                timeout=self._timeout,
            )
        except requests.RequestException as e:
            logger.error("Error conectando con Mailjet: %r", e)
            raise ServicioExternoError("No fue posible conectar con Mailjet") from e

        if not respuesta.ok:
            logger.error("Mailjet respondió %s: %s", respuesta.status_code, respuesta.text)
            raise ServicioExternoError("Mailjet rechazó el envío del correo")
