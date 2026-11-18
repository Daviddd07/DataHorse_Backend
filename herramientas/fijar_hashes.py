"""Añade los hashes SHA-256 oficiales de PyPI a los archivos de dependencias.

pip se ejecuta con ``--require-hashes --only-binary :all:`` (CI y Dockerfile), así que cada
paquete fijado con ``nombre==versión`` debe llevar el hash de sus ruedas (.whl). Con eso pip
rechaza cualquier archivo que no sea exactamente el publicado para esa versión.

Uso, cada vez que cambie una versión en los requirements (desde cualquier carpeta):

    python herramientas/fijar_hashes.py

Procesa siempre los mismos dos archivos de la carpeta backend (no recibe rutas).

El script es idempotente: borra los hashes anteriores y vuelve a escribirlos.
"""

import json
import re
import urllib.request
from pathlib import Path

PYPI = "https://pypi.org/pypi/{nombre}/{version}/json"
# Archivos fijos: el script no acepta rutas de fuera
CARPETA_BACKEND = Path(__file__).resolve().parent.parent
ARCHIVOS = ("requirements.txt", "requirements-dev.txt")
FIJADO = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;\\]+)")


def hashes_de_ruedas(nombre: str, version: str) -> list[str]:
    """Devuelve los SHA-256 de todas las ruedas publicadas para esa versión."""
    url = PYPI.format(nombre=nombre, version=version)
    with urllib.request.urlopen(url, timeout=30) as respuesta:  # NOSONAR: URL fija de PyPI
        datos = json.load(respuesta)
    hashes = sorted(
        archivo["digests"]["sha256"]
        for archivo in datos["urls"]
        if archivo["packagetype"] == "bdist_wheel" and not archivo.get("yanked")
    )
    if not hashes:
        raise SystemExit(f"{nombre}=={version} no tiene ruedas en PyPI")
    return hashes


def procesar(ruta: Path) -> None:
    lineas_entrada = ruta.read_text(encoding="utf-8").splitlines()
    salida: list[str] = []
    for linea in lineas_entrada:
        recortada = linea.strip()
        if recortada.startswith("--hash="):
            continue  # hash viejo: se regenera
        coincidencia = FIJADO.match(recortada)
        if not coincidencia:
            salida.append(linea)
            continue
        nombre, version = coincidencia.groups()
        hashes = hashes_de_ruedas(nombre, version)
        salida.append(f"{nombre}=={version} \\")
        for indice, valor in enumerate(hashes):
            final = "" if indice == len(hashes) - 1 else " \\"
            salida.append(f"    --hash=sha256:{valor}{final}")
        print(f"{ruta.name}: {nombre}=={version} ({len(hashes)} hashes)")
    ruta.write_text("\n".join(salida) + "\n", encoding="utf-8")


if __name__ == "__main__":
    for nombre_archivo in ARCHIVOS:
        procesar(CARPETA_BACKEND / nombre_archivo)
