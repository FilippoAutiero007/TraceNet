FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    cmake \
    libcrypto++-dev \
    libzip-dev \
    libre2-dev \
    zlib1g-dev \
    pkg-config \
    libabsl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install pka2xml with system libraries (no source build needed)
RUN git clone https://github.com/mircodz/pka2xml.git /tmp/pka2xml && \
    cd /tmp/pka2xml && \
    g++ -o pka2xml main.cpp \
        -I/usr/include \
        -L/usr/lib/x86_64-linux-gnu \
        -lzip -lre2 -lcryptopp -lz -lpthread \
        -std=c++17 && \
    cp pka2xml /usr/local/bin/ && \
    rm -rf /tmp/pka2xml

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8001

# Run command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
