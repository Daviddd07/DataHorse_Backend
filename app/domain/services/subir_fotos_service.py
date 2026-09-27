import uuid
from pathlib import Path
from typing import List

from app.config.settings import (
    FOTO_CABALLO_DIR,
    FOTO_CABALLO_URL_PREFIX,
    FOTO_MAX_SIZE,
    FOTO_ALLOWED_TYPES,
    FOTO_EXT_ALLOWED,
)
from app.domain.entities.foto_caballo import FotoCaballo
from app.domain.ports.out.foto_repository import FotoRepository


class SubirFotosService:

    def __init__(self, foto_repo: FotoRepository):
        self.foto_repo = foto_repo

    def ejecutar(
        self,
        id_caballo: int,
        archivos: List[tuple[str, str, bytes]],
    ) -> List[FotoCaballo]:
        ya_tiene = self.foto_repo.contar_por_caballo(id_caballo) > 0
        guardadas: List[FotoCaballo] = []

        for idx, (nombre_original, content_type, contenido) in enumerate(archivos):
            if content_type not in FOTO_ALLOWED_TYPES:
                raise ValueError(f"Tipo no permitido: {content_type}")

            if len(contenido) > FOTO_MAX_SIZE:
                raise ValueError(f"{nombre_original} excede 5MB")

            ext = Path(nombre_original).suffix.lower()
            if ext not in FOTO_EXT_ALLOWED:
                raise ValueError(f"Extensión no permitida: {ext}")

            nombre_uuid = f"{uuid.uuid4().hex}{ext}"
            ruta_fisica = FOTO_CALLO_DIR / nombre_uuid if False else FOTO_CABALLO_DIR / nombre_uuid

            with open(ruta_fisica, "wb") as f:
                f.write(contenido)

            foto = FotoCaballo(
                id_foto=None,
                id_caballo=id_caballo,
                ruta=f"{FOTO_CABALLO_URL_PREFIX.strip('/')}/{nombre_uuid}",
                es_principal=(not ya_tiene) and (idx == 0),
                orden=idx,
            )
            guardadas.append(self.foto_repo.guardar(foto))

        return guardadas