"""Reglas del dominio para la evaluación de compatibilidad.

Los cálculos (edad, diferencia de altura, distancia) se hacen aquí: los modelos de IA
se equivocan con la aritmética, así que reciben los valores ya calculados.
"""
import math
from datetime import date
from typing import Optional

from app.domain.entities.compatibilidad import (
    NIVELES_CONFIANZA,
    DatosEvaluacion,
    EjemplarEvaluado,
    ResultadoCompatibilidad,
)
from app.domain.entities.descendencia import Descendencia

RADIO_TIERRA_KM = 6371.0


def edad_en_meses(fecha_nacimiento: date, hoy: date) -> int:
    meses = (hoy.year - fecha_nacimiento.year) * 12 + (hoy.month - fecha_nacimiento.month)
    if hoy.day < fecha_nacimiento.day:
        meses -= 1
    return max(meses, 0)


def describir_edad(meses: int) -> str:
    anios, resto = divmod(meses, 12)
    partes = []
    if anios:
        partes.append(f"{anios} año" + ("s" if anios != 1 else ""))
    if resto or not anios:
        partes.append(f"{resto} mes" + ("es" if resto != 1 else ""))
    return " y ".join(partes)


def distancia_km(a: EjemplarEvaluado, b: EjemplarEvaluado) -> Optional[float]:
    """Distancia en línea recta (fórmula de haversine), o None si falta alguna ubicación."""
    coordenadas = (a.ubicacion_lat, a.ubicacion_lng, b.ubicacion_lat, b.ubicacion_lng)
    if any(c is None for c in coordenadas):
        return None

    lat1, lng1, lat2, lng2 = (math.radians(float(c)) for c in coordenadas)
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return round(2 * RADIO_TIERRA_KM * math.asin(math.sqrt(h)), 1)


def ficha_ejemplar(ejemplar: EjemplarEvaluado, hoy: date) -> dict:
    """Datos de un ejemplar para la IA: solo los del caballo, nunca los del dueño."""
    meses = edad_en_meses(ejemplar.fecha_nacimiento, hoy)
    descendencia = ejemplar.descendencia or Descendencia()

    return {
        "nombre": ejemplar.nombre,
        "sexo": ejemplar.sexo,
        "raza": ejemplar.raza,
        "edad": describir_edad(meses),
        "edad_meses": meses,
        "altura_m": ejemplar.altura,
        "color": ejemplar.color,
        "ciudad": ejemplar.ciudad,
        "departamento": ejemplar.departamento,
        "descripcion_del_dueno": ejemplar.descripcion,
        "descendencia": {
            campo: getattr(descendencia, campo)
            for campo in Descendencia.campos()
            if getattr(descendencia, campo) is not None
        },
        "descendencia_campos_sin_dato": descendencia.campos_vacios(),
    }


def construir_datos(
    caballo: EjemplarEvaluado,
    yegua: EjemplarEvaluado,
    porcentaje_razas: Optional[float],
    hoy: date,
) -> DatosEvaluacion:
    return DatosEvaluacion(
        caballo=ficha_ejemplar(caballo, hoy),
        yegua=ficha_ejemplar(yegua, hoy),
        diferencia_altura_cm=round(abs(caballo.altura - yegua.altura) * 100, 1),
        distancia_km=distancia_km(caballo, yegua),
        porcentaje_referencia_razas=porcentaje_razas,
    )


def resultado_es_valido(resultado: ResultadoCompatibilidad) -> bool:
    """La IA debe respetar los rangos; si no, el resultado no se guarda ni se muestra."""
    return (
        all(isinstance(p, int) and 0 <= p <= 100 for p in resultado.puntos())
        and resultado.nivel_confianza in NIVELES_CONFIANZA
        and bool(resultado.resumen_cria.strip())
    )
