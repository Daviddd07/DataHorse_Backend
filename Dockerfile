
# Imagen base de Python
FROM python:3.12-slim

# Evitar archivos .pyc y mostrar logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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

# Arranque del backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
