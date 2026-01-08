# RikaiOS API Dockerfile
# Multi-stage build for smaller final image

# =============================================================================
# Build Stage
# =============================================================================
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package installation
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml README.md ./
COPY rikaios/ rikaios/

# Install dependencies
RUN uv pip install --system -e .

# =============================================================================
# Runtime Stage
# =============================================================================
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash rikaios
USER rikaios

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=rikaios:rikaios rikaios/ rikaios/

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    RIKAI_VECTOR_BACKEND=pgvector

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the API server
CMD ["uvicorn", "rikaios.servers.api:app", "--host", "0.0.0.0", "--port", "8000"]
