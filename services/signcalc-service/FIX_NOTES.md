# Signcalc Service - Docker Fix Notes

## Issue

The signcalc service was failing to start with error:
```
OSError: cannot load library 'libgobject-2.0-0': libgobject-2.0-0: cannot open shared object file: No such file or directory
```

## Root Cause

The `weasyprint` library (used for PDF generation) requires system libraries that weren't installed in the Docker image:
- `libgobject-2.0-0` (GObject library)
- `libpango-1.0-0` (Pango text layout)
- `libcairo2` (Cairo graphics)
- And other dependencies

## Fix

Updated `services/signcalc-service/Dockerfile` to install required system packages:

```dockerfile
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
```

## Verification

After rebuilding:
- ✅ Docker build completes successfully
- ✅ Service starts without errors
- ✅ Health check passes (`/healthz` returns 200 OK)
- ✅ Service running on port 8002

## Test Commands

```bash
# Rebuild
docker-compose -f infra/compose.yaml build signcalc

# Test standalone
docker-compose -f infra/compose.yaml run --rm signcalc python -m main

# Start service
docker-compose -f infra/compose.yaml up -d signcalc

# Check logs
docker-compose -f infra/compose.yaml logs signcalc --tail=50

# Health check
curl http://localhost:8002/healthz
```

