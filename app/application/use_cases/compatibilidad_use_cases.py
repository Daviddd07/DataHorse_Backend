import logging
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Callable, List

from app.domain.entities.compatibilidad import EjemplarEvaluado, ResultadoCompatibilidad
from app.domain.exceptions import (
    DemasiadosIntentosError,
    RecursoNoEncontradoError,
    ServicioExternoError,
    SolicitudInvalidaError,
)
from app.domain.ports.in_.compatibilidad_ports import (
    ConsultarCupoCompatibilidadPort,
    EvaluarCompatibilidadPort,
    ListarResultadosCompatibilidadPort,
    ObtenerResultadoCompatibilidadPort,
)
from app.domain.ports.out.compatibilidad_repository_port import CompatibilidadRepositoryPort
from app.domain.ports.out.evaluador_compatibilidad_port import EvaluadorCompatibilidadPort
from app.domain.services.datos_compatibilidad import construir_datos, resultado_es_valido

logger = logging.getLogger(__name__)

AVISO = (
    "Estimación orientativa generada con inteligencia artificial a partir de los datos registrados. "
    "Consulta a un médico veterinario antes de tomar decisiones de cría."
)


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _inicio_del_dia_utc(ahora_local: datetime) -> datetime:
    """Medianoche local expresada en UTC sin zona (así guarda la BD creado_en)."""
    medianoche = ahora_local.replace(hour=0, minute=0, second=0, microsecond=0)
    return medianoche.astimezone(timezone.utc).replace(tzinfo=None)


def _resumen_ejemplar(ejemplar: EjemplarEvaluado) -> dict:
    return {
        "id_caballo": ejemplar.id_caballo,
        "nombre": ejemplar.nombre,
        "raza": ejemplar.raza,
        "propietario": ejemplar.propietario,
    }


class EvaluarCompatibilidadUseCase(EvaluarCompatibilidadPort):
    def __init__(
        self,
        repo: CompatibilidadRepositoryPort,
        evaluador: EvaluadorCompatibilidadPort,
        limite_diario: int,
        zona_horaria_horas: int,
        reloj: Callable[[], datetime] = _ahora_utc,
    ):
        self._repo = repo
        self._evaluador = evaluador
        self._limite = limite_diario
        self._zona = timezone(timedelta(hours=zona_horaria_horas))
        self._reloj = reloj

    def ejecutar(self, id_usuario: int, id_caballo: int, id_yegua: int) -> dict:
        caballo = self._caballo_del_marketplace(id_caballo)
        yegua = self._yegua_del_usuario(id_yegua, id_usuario)

        ahora_local = self._reloj().astimezone(self._zona)
        datos = construir_datos(
            caballo,
            yegua,
            self._repo.porcentaje_razas(yegua.id_raza, caballo.id_raza),
            ahora_local.date(),
        )
        huella = datos.huella()

        usadas = self._repo.contar_evaluaciones_desde(id_usuario, _inicio_del_dia_utc(ahora_local))

        # Mismo par con los mismos datos: se reutiliza sin gastar cupo
        guardado = self._repo.buscar_resultado(id_caballo, id_yegua, huella)
        if guardado is not None:
            return self._respuesta(guardado, caballo, yegua, True, self._limite - usadas)

        if usadas >= self._limite:
            raise DemasiadosIntentosError(
                f"Alcanzaste el límite de {self._limite} evaluaciones por hoy. Vuelve mañana."
            )

        resultado = self._evaluador.evaluar(datos)

        if not resultado_es_valido(resultado):
            logger.error("La IA devolvió un resultado fuera de rango: %s", asdict(resultado))
            raise ServicioExternoError("El servicio de IA devolvió una respuesta no válida. Intenta de nuevo.")

        self._repo.guardar(id_usuario, id_caballo, id_yegua, huella, ahora_local.date(), resultado)
        return self._respuesta(resultado, caballo, yegua, False, self._limite - usadas - 1)

    # ======================================================
    # VALIDACIONES
    # ======================================================

    def _caballo_del_marketplace(self, id_caballo: int) -> EjemplarEvaluado:
        caballo = self._repo.obtener_ejemplar(id_caballo)

        if caballo is None or caballo.eliminado:
            raise RecursoNoEncontradoError("Caballo no encontrado")
        if caballo.sexo != "Macho":
            raise SolicitudInvalidaError("El ejemplar del marketplace debe ser un caballo (macho)")
        if not caballo.publicado:
            raise SolicitudInvalidaError("El caballo no tiene una publicación activa en el marketplace")

        return caballo

    def _yegua_del_usuario(self, id_yegua: int, id_usuario: int) -> EjemplarEvaluado:
        yegua = self._repo.obtener_ejemplar(id_yegua)

        # Misma respuesta si no existe o es de otro usuario: no se revela qué yeguas existen
        if yegua is None or yegua.eliminado or yegua.id_propietario != id_usuario:
            raise RecursoNoEncontradoError("Yegua no encontrada")
        if yegua.sexo != "Hembra":
            raise SolicitudInvalidaError("Debes elegir una de tus yeguas")

        return yegua

    # ======================================================
    # RESPUESTA
    # ======================================================

    @staticmethod
    def _respuesta(
        resultado: ResultadoCompatibilidad,
        caballo: EjemplarEvaluado,
        yegua: EjemplarEvaluado,
        desde_cache: bool,
        restantes: int,
    ) -> dict:
        return {
            "resultado": asdict(resultado),
            "caballo": _resumen_ejemplar(caballo),
            "yegua": _resumen_ejemplar(yegua),
            "desde_cache": desde_cache,
            "evaluaciones_restantes_hoy": max(restantes, 0),
            "aviso": AVISO,
        }


class ConsultarCupoCompatibilidadUseCase(ConsultarCupoCompatibilidadPort):
    def __init__(
        self,
        repo: CompatibilidadRepositoryPort,
        limite_diario: int,
        zona_horaria_horas: int,
        reloj: Callable[[], datetime] = _ahora_utc,
    ):
        self._repo = repo
        self._limite = limite_diario
        self._zona = timezone(timedelta(hours=zona_horaria_horas))
        self._reloj = reloj

    def ejecutar(self, id_usuario: int) -> dict:
        ahora_local = self._reloj().astimezone(self._zona)
        usadas = self._repo.contar_evaluaciones_desde(id_usuario, _inicio_del_dia_utc(ahora_local))

        return {
            "limite": self._limite,
            "usadas": usadas,
            "restantes": max(self._limite - usadas, 0),
        }


class ListarResultadosCompatibilidadUseCase(ListarResultadosCompatibilidadPort):
    def __init__(self, repo: CompatibilidadRepositoryPort):
        self._repo = repo

    def ejecutar(self, id_usuario: int) -> List[dict]:
        return self._repo.listar_de_usuario(id_usuario)


class ObtenerResultadoCompatibilidadUseCase(ObtenerResultadoCompatibilidadPort):
    """Devuelve el estudio tal como se guardó: no llama a la IA ni gasta estimaciones."""

    def __init__(self, repo: CompatibilidadRepositoryPort):
        self._repo = repo

    def ejecutar(self, id_usuario: int, id_solicitud: int) -> dict:
        guardada = self._repo.obtener_evaluacion(id_solicitud)

        # Misma respuesta si no existe o es de otro usuario
        if guardada is None or guardada.id_usuario != id_usuario:
            raise RecursoNoEncontradoError("Estudio no encontrado")

        caballo = self._repo.obtener_ejemplar(guardada.id_caballo)
        yegua = self._repo.obtener_ejemplar(guardada.id_yegua)

        if caballo is None or yegua is None:
            raise RecursoNoEncontradoError("Estudio no encontrado")

        return {
            "id_solicitud": guardada.id_solicitud,
            "fecha": guardada.creado_en,
            "resultado": asdict(guardada.resultado),
            "caballo": _resumen_ejemplar(caballo),
            "yegua": _resumen_ejemplar(yegua),
            "desde_cache": True,
            "aviso": AVISO,
        }
