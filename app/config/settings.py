from pathlib import Path


# ======================================================
# USUARIOS
# ======================================================

ROL_USUARIO_ID = 2          # rol "usuario" normal (nunca viene del cliente)
ESTADO_INICIAL = "activo"


# ======================================================
# CORS
# ======================================================

ORIGENES_PERMITIDOS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]


# ======================================================
# COMPATIBILIDAD CON IA (Groq). La API key va en el .env (GROQ_API_KEY)
# ======================================================

# Modelo principal y de respaldo (se usa si el principal no tiene cupo)
GROQ_MODELOS = ("openai/gpt-oss-120b", "openai/gpt-oss-20b")
GROQ_TIMEOUT_SEGUNDOS = 30

LIMITE_EVALUACIONES_DIARIAS = 5  # por usuario; las reutilizadas no cuentan
ZONA_HORARIA_HORAS = -5          # Colombia (UTC-5, sin horario de verano): define cuándo empieza "hoy"


# ======================================================
# RUTAS DEL PROYECTO
# ======================================================

# Base del proyecto (donde está la carpeta app/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# ======================================================
# ARCHIVOS / FOTOS
# ======================================================

UPLOAD_DIR = BASE_DIR / "uploads"
FOTO_CABALLO_DIR = UPLOAD_DIR / "caballos"
FOTO_CABALLO_URL_PREFIX = "/uploads/caballos"
FOTO_PERFIL_DIR = UPLOAD_DIR / "perfiles"
FOTO_PERFIL_URL_PREFIX = "/uploads/perfiles"
FOTO_PERFIL_LADO = 512                    # px: las fotos de perfil se guardan cuadradas

# Límites de subida
FOTO_MAX_SIZE = 5 * 1024 * 1024            # 5 MB por foto
FOTO_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
FOTO_EXT_ALLOWED = {".jpg", ".jpeg", ".png", ".webp"}
