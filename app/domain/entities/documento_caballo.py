from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# Tipos de documento de respaldo y su nombre para mostrar.
TIPOS_DOCUMENTO = {
    "pedigri": "Pedigrí / registro",
    "premio": "Premio",
    "prueba_genetica": "Prueba genética",
    "otro": "Otro",
}

ESTADO_SIN_REVISAR = "sin_revisar"


@dataclass
class DocumentoCaballo:
    """Documento que respalda lo que el propietario declara de un caballo macho."""
    id_documento: Optional[int]
    id_caballo: int
    tipo: str
    titulo: str
    ruta: str                     # "documentos/<uuid>.pdf" (privado, nunca bajo /uploads)
    nombre_original: str
    content_type: str
    tamano_bytes: int
    estado_verificacion: str = ESTADO_SIN_REVISAR
    fecha_subida: Optional[datetime] = None

    @property
    def tipo_etiqueta(self) -> str:
        return TIPOS_DOCUMENTO.get(self.tipo, self.tipo)

    @property
    def es_pdf(self) -> bool:
        return self.content_type == "application/pdf"


@dataclass(frozen=True)
class ContextoCaballo:
    """Lo mínimo para decidir quién puede ver los documentos de un caballo."""
    id_propietario: int
    eliminado: bool
    publicado: bool               # tiene una publicación activa en el marketplace
