"""Límite de intentos de login por IP (ventana deslizante en memoria).

Complementa el bloqueo por correo (LOGIN_MAX_FALLOS): ese protege una cuenta concreta,
este frena a una misma IP que prueba muchas cuentas o satura el login (cada intento
cuesta un hash Argon2).

Vive en memoria del proceso: con varios workers de uvicorn cada uno lleva su propia
cuenta (el límite efectivo se multiplica); para compartirlo haría falta Redis.
"""
import threading
import time
from collections import deque

from fastapi import HTTPException, Request

from app.config.settings import LOGIN_LIMITE_POR_IP, LOGIN_LIMITE_VENTANA_SEGUNDOS


class LimitadorPorIp:
    def __init__(self, maximo: int, ventana_segundos: int):
        self.maximo = maximo
        self.ventana = ventana_segundos
        self._intentos: dict[str, deque[float]] = {}
        self._lock = threading.Lock()  # las rutas síncronas corren en varios hilos

    @property
    def activo(self) -> bool:
        return self.maximo > 0

    def registrar(self, ip: str) -> int:
        """Registra un intento. Devuelve 0 si se permite, o los segundos que faltan para reintentar."""
        ahora = time.monotonic()
        with self._lock:
            intentos = self._intentos.setdefault(ip, deque())
            while intentos and ahora - intentos[0] >= self.ventana:
                intentos.popleft()
            if len(intentos) >= self.maximo:
                return int(self.ventana - (ahora - intentos[0])) + 1
            intentos.append(ahora)
            self._limpiar(ahora)
            return 0

    def _limpiar(self, ahora: float) -> None:
        # Evita que el diccionario crezca sin fin con IPs que ya no intentan.
        if len(self._intentos) < 10_000:
            return
        for ip in [ip for ip, i in self._intentos.items() if not i or ahora - i[-1] >= self.ventana]:
            del self._intentos[ip]


limitador_login = LimitadorPorIp(LOGIN_LIMITE_POR_IP, LOGIN_LIMITE_VENTANA_SEGUNDOS)


def limitar_login(request: Request) -> None:
    """Dependencia de FastAPI para POST /auth/login: responde 429 si la IP superó el límite."""
    if not limitador_login.activo:
        return
    ip = request.client.host if request.client else "desconocida"
    espera = limitador_login.registrar(ip)
    if espera:
        raise HTTPException(
            status_code=429,
            detail="Demasiados intentos de inicio de sesión. Intenta de nuevo en unos segundos.",
            headers={"Retry-After": str(espera)},
        )
