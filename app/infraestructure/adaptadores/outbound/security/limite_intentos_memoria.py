import threading
import time
from collections import deque
from typing import Callable, Deque, Dict

from app.domain.ports.out.limite_intentos_port import LimiteIntentosPort


class LimiteIntentosEnMemoria(LimiteIntentosPort):
    """Ventana deslizante en memoria del proceso.

    Sirve mientras el backend corra en un solo proceso (como hoy en Docker).
    Se reinicia si el backend se reinicia. Con varios procesos o servidores
    habría que cambiarlo por una implementación compartida (MySQL o Redis)
    del mismo puerto.
    """

    def __init__(
        self,
        max_fallos: int,
        ventana_segundos: int,
        reloj: Callable[[], float] = time.monotonic,
    ):
        self._max_fallos = max_fallos
        self._ventana = ventana_segundos
        self._reloj = reloj
        self._fallos: Dict[str, Deque[float]] = {}
        self._candado = threading.Lock()

    def _vigentes(self, clave: str, ahora: float) -> Deque[float]:
        fallos = self._fallos.get(clave)
        if fallos is None:
            return deque()
        while fallos and ahora - fallos[0] >= self._ventana:
            fallos.popleft()
        if not fallos:
            del self._fallos[clave]
        return fallos

    def segundos_bloqueado(self, clave: str) -> int:
        with self._candado:
            ahora = self._reloj()
            fallos = self._vigentes(clave, ahora)
            if len(fallos) < self._max_fallos:
                return 0
            # Se desbloquea cuando el fallo más antiguo de la ventana caduca
            return max(1, int(fallos[0] + self._ventana - ahora + 0.999))

    def registrar_fallo(self, clave: str) -> None:
        with self._candado:
            ahora = self._reloj()
            self._vigentes(clave, ahora)
            self._fallos.setdefault(clave, deque()).append(ahora)

    def limpiar(self, clave: str) -> None:
        with self._candado:
            self._fallos.pop(clave, None)
