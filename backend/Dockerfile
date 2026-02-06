FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libcrypto++-dev \
    libzip-dev \
    cmake \
    libabsl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Clone and build pka2xml
RUN git clone https://github.com/mircodz/pka2xml.git /tmp/pka2xml \
    && cd /tmp/pka2xml \
    && make \
    && cp pka2xml /usr/local/bin/ \
    && chmod +x /usr/local/bin/pka2xml

# Final stage
FROM python:3.11-slim

# Copy pka2xml from builder
COPY --from=builder /usr/local/bin/pka2xml /usr/local/bin/

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libcrypto++-dev \
    libzip-dev \
    libre2-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create output directory
RUN mkdir -p /tmp/tracenet

EXPOSE 8001

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]