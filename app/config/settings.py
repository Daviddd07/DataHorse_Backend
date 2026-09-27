from pathlib import Path


# ======================================================
# USUARIOS
# ======================================================

ROL_USUARIO_ID = 2

ESTADO_INICIAL = "activo"


# ======================================================
# CORS
# ======================================================

ORIGENES_PERMITIDOS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]


# ======================================================
# RUTAS DEL PROYECTO
# ======================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    .parent
)


# ======================================================
# ARCHIVOS / FOTOS
# ======================================================

UPLOAD_DIR = (
    BASE_DIR
    / "uploads"
)

FOTO_CABALLO_DIR = (
    UPLOAD_DIR
    / "caballos"
)

FOTO_CABALLO_URL_PREFIX = (
    "/uploads/caballos"
)


# ======================================================
# CONFIGURACIÓN DE FOTOS
# ======================================================

FOTO_MAX_SIZE = (
    5 * 1024 * 1024
)

FOTO_ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

FOTO_EXT_ALLOWED = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}