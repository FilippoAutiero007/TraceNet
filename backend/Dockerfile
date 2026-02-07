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

# Esponi porta API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando di avvio con Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
