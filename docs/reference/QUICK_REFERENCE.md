# Quick Reference

## Environment Variables

| Variable | Default | Required |
|----------|---------|----------|
| `APEX_DATABASE_URL` | `postgresql://apex:apex@db:5432/apex` | Yes (prod) |
| `APEX_REDIS_URL` | `redis://cache:6379/0` | Yes (prod) |
| `APEX_MINIO_URL` | `http://object:9000` | Yes |
| `APEX_MINIO_ACCESS_KEY` | `None` | Yes (prod) |
| `APEX_MINIO_SECRET_KEY` | `None` | Yes (prod) |
| `APEX_OPENSEARCH_URL` | `http://search:9200` | No |
| `APEX_CORS_ALLOW_ORIGINS` | `[]` | Yes (prod) |
| `APEX_RATE_LIMIT_PER_MIN` | `60` | No |

**Full Reference**: [Environment Variables](environment-variables.md)

## API Endpoints

### Core
- `GET /health` - Health check
- `GET /ready` - Readiness probe
- `GET /metrics` - Prometheus metrics
- `GET /docs` - API documentation

### Projects
- `GET /projects` - List projects
- `POST /projects` - Create project
- `GET /projects/{id}` - Get project
- `PUT /projects/{id}` - Update project
- `POST /projects/{id}/submit` - Submit project
- `POST /projects/{id}/report` - Generate report

### Sign Design
- `POST /signage/common/site/resolve` - Resolve address
- `POST /signage/common/cabinets/derive` - Calculate cabinets
- `POST /signage/common/poles/options` - Get pole options
- `POST /signage/direct_burial/footing/solve` - Solve footing
- `POST /signage/baseplate/checks` - Baseplate validation

**Full Reference**: [API Endpoints](api-endpoints.md)

## Common Commands

```bash
# Start services
docker compose up -d

# Run migrations
docker compose exec api alembic upgrade head

# Check health
curl http://localhost:8000/health

# View logs
docker compose logs -f api

# Restart service
docker compose restart api

# Scale services
docker compose up -d --scale api=3
```

## Response Envelope

```json
{
  "result": {...},
  "assumptions": [...],
  "confidence": 0.95,
  "trace": {...}
}
```

**Full Reference**: [Response Envelope](response-envelope.md)

## Status Codes

- `200` - Success
- `201` - Created
- `404` - Not Found
- `412` - Precondition Failed
- `422` - Validation Error
- `429` - Rate Limit
- `500` - Server Error

**Full Reference**: [Error Codes](error-codes.md)

