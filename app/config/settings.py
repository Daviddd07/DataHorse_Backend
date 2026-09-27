from pathlib import Path
ROL_USUARIO_ID = 2          # rol "usuario" normal (nunca viene del cliente)
ESTADO_INICIAL = "activo"
ORIGENES_PERMITIDOS = ["http://localhost:4200"]


# Base del proyecto (donde está la carpeta app/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

UPLOAD_DIR = BASE_DIR / "uploads"
FOTO_CABALLO_DIR = UPLOAD_DIR / "caballos"
FOTO_CABALLO_URL_PREFIX = "/uploads/caballos"

# Límites de subida
FOTO_MAX_SIZE = 5 * 1024 * 1024            # 5 MB por foto
FOTO_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
FOTO_EXT_ALLOWED = {".jpg", ".jpeg", ".png", ".webp"}