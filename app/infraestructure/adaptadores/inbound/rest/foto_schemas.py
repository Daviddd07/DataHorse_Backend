from pydantic import BaseModel
from datetime import datetime


class FotoCaballoResponse(BaseModel):
    id_foto: int
    ruta: str
    es_principal: bool
    orden: int
    fecha_subida: datetime | None = None