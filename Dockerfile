
# Imagen base de Python
FROM python:3.12-slim

# Evitar archivos .pyc y mostrar logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Sin paquetes del sistema: todas las dependencias (PyMySQL, argon2, cryptography, pillow...)
# traen ruedas precompiladas para x86_64 (Windows/Docker Desktop) y arm64 (Ubuntu en AWS Graviton).

# Instalar dependencias de Python: solo ruedas (sin ejecutar setup.py) y verificando
# el hash SHA-256 de cada archivo contra el fijado en requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir --only-binary :all: --require-hashes -r requirements.txt

# Copiar el código de la aplicación
# Copiar el archivo principal de FastAPI
COPY main.py .

# Copiar los módulos de la aplicación
COPY app/ ./app/

# Crear usuario sin privilegios
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

# Ejecutar la aplicación como usuario no root
USER appuser

# Puerto de FastAPI
EXPOSE 8000

# Tope de conexiones simultáneas: por encima, uvicorn responde 503 al instante en vez de
# encolar peticiones que el cliente terminará abandonando (prueba E9: sin tope, el servidor
# tardó ~90 s en recuperarse tras la sobrecarga). Se ajusta con UVICORN_LIMIT_CONCURRENCY.
ENV UVICORN_LIMIT_CONCURRENCY=1000

# Arranque del backend (exec: uvicorn queda como proceso principal y recibe las señales de Docker)
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port 8000 --limit-concurrency ${UVICORN_LIMIT_CONCURRENCY}"]
