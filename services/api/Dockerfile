# ============================================================================
# Stage 1: Builder - Compile dependencies and generate requirements
# ============================================================================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project file and compile dependencies with hashes
COPY pyproject.toml /build/pyproject.toml
RUN pip install --upgrade pip && \
    pip install uv==0.4.18 && \
    uv pip compile --generate-hashes /build/pyproject.toml -o /build/requirements.txt

# Install dependencies to /install directory
RUN uv pip install --target=/install --system -r /build/requirements.txt

# ============================================================================
# Stage 2: Production Runtime - Minimal production image
# ============================================================================
FROM python:3.11-slim

LABEL maintainer="SignX Studio Engineering <engineering@signxstudio.com>"
LABEL description="SignX Studio API - Structural Engineering Calculation Service"
LABEL version="1.0.0"

# Security and performance environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONHASHSEED=random \
    PYTHONPATH=/app/src

# Create non-root user and group
RUN groupadd -r appuser -g 1000 && \
    useradd -r -u 1000 -g appuser -d /app -s /bin/bash appuser && \
    mkdir -p /app /tmp/apex /var/log/apex && \
    chown -R appuser:appuser /app /tmp/apex /var/log/apex

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Copy installed dependencies from builder stage
COPY --from=builder /install /usr/local/lib/python3.11/site-packages

# Copy application code with proper ownership
COPY --chown=appuser:appuser src /app/src
COPY --chown=appuser:appuser alembic /app/alembic
COPY --chown=appuser:appuser alembic.ini /app/alembic.ini
COPY --chown=appuser:appuser config /app/config
COPY --chown=appuser:appuser scripts /app/scripts

# Application metadata
ENV ENV=production \
    SERVICE_NAME=api \
    APP_VERSION=1.0.0

# Expose API port
EXPOSE 8000

# Health check - critical for production orchestration
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/health > /dev/null || exit 1

# Switch to non-root user for security
USER appuser

# Production server with optimized settings
CMD ["uvicorn", "apex.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*", \
     "--workers", "4", \
     "--log-level", "info", \
     "--access-log", \
     "--no-use-colors"]


