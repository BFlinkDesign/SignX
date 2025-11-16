# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (including weasyprint requirements)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libfontconfig1 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libglib2.0-0 \
        libgobject-2.0-0 \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy project and install
COPY pyproject.toml /app/pyproject.toml
RUN pip install --upgrade pip \
    && pip install uv==0.4.18 \
    && uv pip compile --generate-hashes /app/pyproject.toml -o /app/requirements.txt \
    && uv pip install --system -r /app/requirements.txt

COPY . /app/

EXPOSE 8002

HEALTHCHECK --interval=15s --timeout=3s --retries=5 CMD curl -fsS http://localhost:8002/healthz || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]

