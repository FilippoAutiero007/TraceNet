# Dockerfile per TraceNet - Fix dipendenze RE2/Abseil

FROM ubuntu:22.04

# Evita prompt interattivi durante l'installazione
ENV DEBIAN_FRONTEND=noninteractive

# Aggiorna il sistema e installa dipendenze di base
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    pkg-config \
    libssl-dev \
    zlib1g-dev

# Installa dipendenze RE2/Abseil compatibili (FIX PRINCIPALE)
RUN apt-get install -y \
    libabsl-dev \
    libre2-dev \
    libgtest-dev \
    libbenchmark-dev \
    libprotobuf-dev \
    protobuf-compiler \
    libgrpc++-dev \
    libgrpc-dev

# Installa librerie per compressione .pkt
RUN apt-get install -y \
    libbz2-dev \
    libxml2-dev \
    libxml2-utils

# Installa Node.js per il frontend (se necessario)
RUN apt-get install -y \
    nodejs \
    npm

# Pulizia cache apt
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Imposta directory di lavoro
WORKDIR /app

# Copia i file del progetto
COPY . /app

# Configura CMake con le opzioni corrette per RE2
RUN cmake -DRE2_TEST=ON \
          -DRE2_BENCHMARK=ON \
          -DRE2_USE_ICU=ON \
          -DCMAKE_BUILD_TYPE=Release \
          -S . -B build

# Compila il progetto
RUN cmake --build build -j$(nproc)

# Esponi le porte necessarie (modifica secondo necessità)
EXPOSE 8080 3000

# Comando di avvio
CMD ["./build/tracenet"]
