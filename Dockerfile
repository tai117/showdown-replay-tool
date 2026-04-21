FROM python:3.13-slim AS base

# Variables de entorno configurables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app

WORKDIR $APP_HOME

# Instalar dependencias del sistema si fueran necesarias (ninguna para aiohttp/rich)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar solo requirements primero para aprovechar caché de Docker
COPY pyproject.toml .
RUN pip install --no-cache-dir ".[dev]"

# Copiar código fuente
COPY src/ ./src/
COPY config/ ./config/
COPY main.py cli.py ./

# Crear usuario no-root para seguridad
RUN groupadd -r appuser && useradd -r -g appuser -d $APP_HOME -s /sbin/nologin appuser \
    && chown -R appuser:appuser $APP_HOME

USER appuser

# Punto de entrada por defecto
ENTRYPOINT ["python", "cli.py"]
CMD ["fetch"]
