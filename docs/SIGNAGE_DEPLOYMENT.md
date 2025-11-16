# APEX Signage Engineering - Deployment Guide

Complete CalcuSign-parity platform deployment instructions.

## Prerequisites

- Docker Compose (or equivalent orchestration)
- PostgreSQL 15+
- Redis 7+
- MinIO (S3-compatible)
- Python 3.12+

## Quick Start

### 1. Database Setup

```bash
# Create database
createdb apex

# Apply schemas
psql postgresql://apex:apex@localhost:5432/apex -f services/api/src/apex/domains/signage/db/schemas.sql

# Seed defaults
python scripts/seed_defaults.py

# Import AISC sections (optional, requires download)
# Download: https://www.aisc.org/resources/shapes-database/
export AISC_CSV_PATH=data/aisc-shapes-v16.csv
python scripts/seed_aisc_sections.py
```

### 2. Environment Configuration

Create `.env`:

```bash
DATABASE_URL=postgresql://apex:apex@db:5432/apex
REDIS_URL=redis://cache:6379/0
MINIO_ENDPOINT=object:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# External APIs (optional)
ASCE_API_KEY=your_key_here
```

### 3. Start Services

```bash
docker compose up -d --build
```

Verify health:

```bash
curl http://localhost:8000/health
```

## Testing

### Unit Tests

```bash
pytest tests/unit/test_signage_solvers.py -v
```

### Integration Tests

```bash
# Test load derivation
curl -X POST http://localhost:8000/signage/cabinets/derive \
  -H "Content-Type: application/json" \
  -d '{"overall_height_ft": 25.0, "cabinets": [{"width_ft": 14.0, "height_ft": 8.0}]}'

# Test footing solve
curl -X POST http://localhost:8000/signage/direct_burial/footing/solve \
  -H "Content-Type: application/json" \
  -d '{"mu_kipft": 100.0, "footing": {"diameter_ft": 4.0}, "soil_psf": 3000.0}'
```

### Contract Tests

```bash
pytest tests/contract/ -v
```

## Verification Checklist

- [ ] Database schemas applied
- [ ] Calibration constants seeded
- [ ] Pricing table populated
- [ ] AISC sections imported (if applicable)
- [ ] API health check returns 200
- [ ] Unit tests pass
- [ ] Footing monotonicity verified
- [ ] Base plate checks return proper structure

## Troubleshooting

### Database Connection Error

Check `DATABASE_URL` environment variable and ensure Postgres is running:

```bash
pg_isready -h localhost -p 5432
```

### Missing AISC Sections

Pole filtering will return empty until AISC CSV is imported. This is expected for stub deployment.

### ASCE API Integration

Site resolve currently returns stub data. Implement ASCE Hazard Tool API integration for production.

## Production Deployment

### Environment Separation

- **Development**: Use stub data, local Postgres
- **Staging**: Real ASCE API, shared DB
- **Production**: All external integrations, separate DB cluster

### Scaling

- API: Horizontal scaling via load balancer
- Worker: Multiple Celery workers per queue
- Cache: Redis cluster for session/task data

### Monitoring

- Prometheus metrics exported at `/metrics`
- Structured logs (JSON) to OpenSearch/Kibana
- Health checks at `/health` and `/ready`

## Next Steps

- [ ] Integrate ASCE Hazard Tool API
- [ ] Implement PDF report generation
- [ ] Add auto-solve optimizer for base plates
- [ ] Wire PM submission adapter
- [ ] Deploy interactive 2D canvas frontend

