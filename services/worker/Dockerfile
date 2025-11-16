FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Create app user and directory
RUN groupadd -r appuser -g 1000 && \
    useradd -r -u 1000 -g appuser -d /app -s /bin/bash appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gcc \
        g++ \
        pkg-config \
        libffi-dev \
        libjpeg-dev \
        libcairo2-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=appuser:appuser pyproject.toml /app/pyproject.toml
RUN pip install --upgrade pip \
    && pip install uv==0.4.18 \
    && uv pip compile --generate-hashes /app/pyproject.toml -o /app/requirements.txt \
    && uv pip install --system -r /app/requirements.txt

COPY --chown=appuser:appuser src /app/src

ENV SERVICE_NAME=worker \
    PYTHONPATH=/app/src

USER appuser

CMD ["celery", "-A", "apex.worker.app", "worker", "--loglevel=info"]


