import os
from pathlib import Path


# ======================================================
# USUARIOS
# ======================================================

ROL_USUARIO_ID = 2          # rol "usuario" normal (nunca viene del cliente)
ESTADO_INICIAL = "activo"


# ======================================================
# SEGURIDAD
# ======================================================

# Login: tras LOGIN_MAX_FALLOS contraseñas incorrectas para un mismo correo
# dentro de la ventana, ese correo queda bloqueado hasta que caduque el fallo más antiguo.
LOGIN_MAX_FALLOS = 5
LOGIN_VENTANA_SEGUNDOS = 15 * 60

# Login: máximo de intentos por IP dentro de la ventana (aciertos y fallos), para frenar
# fuerza bruta contra muchas cuentas y la saturación del login. 0 lo desactiva
# (lo usa el entorno de pruebas de carga, donde todos los usuarios virtuales comparten IP).
LOGIN_LIMITE_POR_IP = int(os.getenv("LOGIN_LIMITE_POR_IP", "20"))
LOGIN_LIMITE_VENTANA_SEGUNDOS = 60

# Largo mínimo de los secretos del .env (se revisa al arrancar)
LARGO_MINIMO_SECRETO = 32


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

# Documentos de respaldo (pedigrí, premios...): PRIVADOS. Van fuera de UPLOAD_DIR,
# que se sirve en público por /uploads; solo se entregan por la API con sesión.
# Límites y formatos: app/domain/services/validador_documento.py
DOCUMENTO_DIR = BASE_DIR / "documentos"
DOCUMENTO_PREFIJO = "documentos"

# Límites de subida
FOTO_MAX_SIZE = 5 * 1024 * 1024            # 5 MB por foto
FOTO_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
FOTO_EXT_ALLOWED = {".jpg", ".jpeg", ".png", ".webp"}
