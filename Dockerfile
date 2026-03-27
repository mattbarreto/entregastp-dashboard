FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python
COPY dashboard/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Código de la aplicación
COPY dashboard/ ./dashboard/

# Variables de entorno por defecto
ENV NOCODB_DB_PATH=/data/noco.db
ENV COHORTE_FILTRAR_ACTIVAS=true
ENV FLASK_ENV=production

EXPOSE 5000

# Health-check integrado
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Arranque con Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "dashboard.app:app"]
