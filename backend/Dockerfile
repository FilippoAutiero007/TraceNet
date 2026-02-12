# Dockerfile per TraceNet Backend - Python FastAPI

FROM python:3.11-slim

# Evita prompt interattivi
ENV DEBIAN_FRONTEND=noninteractive

# Variabili d'ambiente per Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Aggiorna sistema e installa dipendenze di sistema
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y \
    build-essential \
    git \
    wget \
    curl \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Crea directory di lavoro
WORKDIR /app

# Copia requirements prima (per cache Docker)
COPY requirements.txt /app/

# Installa dipendenze Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# Copia il codice dell'applicazione
COPY . /app/

# Crea directory per output files
RUN mkdir -p /tmp/tracenet

# Esponi porta API (Render uses PORT env var, default 10000)
EXPOSE 10000

# Health check (uses PORT env var)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/api/health || exit 1

# Comando di avvio con Uvicorn (uses PORT env var for Render compatibility)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
