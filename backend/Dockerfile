FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# git, cmake, build-essential: for building pka2xml
# libcrypto++-dev, libzip-dev, libre2-dev, zlib1g-dev: pka2xml dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    cmake \
    libcrypto++-dev \
    libzip-dev \
    libre2-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install pka2xml
# Clone, build, and move binary to /usr/local/bin
RUN git clone https://github.com/mircodz/pka2xml.git /tmp/pka2xml && \
    cd /tmp/pka2xml && \
    mkdir build && cd build && \
    cmake .. && make && \
    cp pka2xml /usr/local/bin/ && \
    rm -rf /tmp/pka2xml

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (default for uvicorn)
EXPOSE 8001

# Run command
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
