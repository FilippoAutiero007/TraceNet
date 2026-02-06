FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including static libraries
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libcrypto++-dev \
    libzip-dev \
    libre2-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Build and install RE2 from source (static library)
RUN git clone https://github.com/google/re2.git /tmp/re2 && \
    cd /tmp/re2 && \
    make && \
    make install && \
    rm -rf /tmp/re2

# Build and install Crypto++ from source (static library)
RUN git clone https://github.com/weidai11/cryptopp.git /tmp/cryptopp && \
    cd /tmp/cryptopp && \
    make static && \
    make install && \
    rm -rf /tmp/cryptopp

# Install pka2xml with dynamic linking (simpler, works with installed libs)
RUN git clone https://github.com/mircodz/pka2xml.git /tmp/pka2xml && \
    cd /tmp/pka2xml && \
    sed -i 's/pka2xml-static/pka2xml-dynamic/' Makefile && \
    make pka2xml-dynamic && \
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
