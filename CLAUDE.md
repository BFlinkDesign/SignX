# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

APEX is a mechanical engineering copilot system with deterministic calculations, test-first development, and full containerization. The system specializes in sign calculation workflows with complete audit trails.

## Architecture

The codebase follows a monorepo structure with two main service types:
- **Python Services**: FastAPI backend, Celery workers, domain services (signcalc, materials, etc.)
- **Frontend**: React/TypeScript app in `apex/apps/ui-web/`

Key directories:
- `services/api/` - Main FastAPI API server with Alembic migrations
- `apex/apps/ui-web/` - React frontend application
- `services/worker/` - Celery async task worker
- `services/signcalc-service/` - Core sign calculation engine
- `infra/` - Docker Compose and Kubernetes configurations
- `tests/` - Comprehensive test suites (unit, integration, contract, e2e)

## Essential Commands

### Development Setup
```bash
# Start all services
cd infra
docker-compose up -d

# Run database migrations
cd ../services/api
alembic upgrade head

# Health check
curl http://localhost:8000/health
```

### Frontend Development
```bash
cd apex/apps/ui-web
npm install
npm run dev          # Start development server
npm run build        # Production build
npm run typecheck    # TypeScript validation
npm run lint         # ESLint check
npm run validate     # Full validation (typecheck + lint + build)
```

### Backend Development
```bash
# Lint Python code
ruff check .

# Run all tests
pytest -v

# Run specific test suites
pytest tests/unit/ -v
pytest tests/service/ -v
pytest tests/e2e/ -v
pytest tests/contract/ -v

# Quick smoke test
python scripts/smoke.py
```

### Using Make (from root)
```bash
make up         # Start services
make health     # Health check
make lint       # Run linter
make contract   # Run contract tests
make smoke      # Run smoke test
make all        # lint + contract + smoke
```

### Database Operations
```bash
# Create new migration
cd services/api
alembic revision -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Key Development Principles

1. **Determinism**: All calculations must be pure functions - same inputs always produce same outputs
2. **Test-First**: Write tests before implementing features
3. **Envelope Pattern**: All API responses follow standardized envelope format with audit trails
4. **Graceful Degradation**: Services fallback when dependencies are unavailable
5. **Idempotency**: Critical operations use idempotency keys to prevent duplicates

## Service Dependencies

- **PostgreSQL** (port 5432): Primary database with pgvector extension
- **Redis** (port 6379): Caching and Celery queue
- **MinIO** (ports 9000/9001): S3-compatible object storage
- **OpenSearch** (port 9200): Search with DB fallback
- **Supabase** (optional): Authentication service

## Testing Strategy

The test pyramid includes:
- **Unit Tests**: Pure function validation, determinism checks
- **Integration Tests**: API route validation, service interaction
- **Contract Tests**: Envelope consistency, OpenAPI compliance
- **E2E Tests**: Full workflow validation from UI to database
- **Performance Tests**: Solver benchmarks, load testing with k6

Run tests with proper fixtures:
```bash
pytest -v --tb=short  # Verbose with short traceback
pytest -k "test_name" # Run specific test
pytest -m "not slow"  # Skip slow tests
```

## Common Workflows

### Adding a New API Endpoint
1. Define schema in `services/api/src/apex/api/schemas.py`
2. Implement route in appropriate file under `routes/`
3. Add unit tests in `tests/unit/`
4. Add integration tests in `tests/service/`
5. Update OpenAPI documentation

### Modifying Database Schema
1. Create migration: `alembic revision -m "description"`
2. Edit migration file in `services/api/alembic/versions/`
3. Test migration: `alembic upgrade head`
4. Add rollback test: `alembic downgrade -1`

### Frontend Component Development
1. Create component in `apex/apps/ui-web/src/components/`
2. Follow existing patterns for state management (Zustand)
3. Use MUI components for consistency
4. Add accessibility attributes
5. Test with `npm run test:a11y`

## Configuration

Environment variables are managed through:
- `infra/compose.yaml` - Docker Compose defaults
- `.env` files (not committed) - Local overrides
- `services/api/src/apex/api/deps.py` - Settings validation

Critical settings:
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection  
- `MINIO_URL` - Object storage endpoint
- `APEX_SUPABASE_URL/KEY` - Auth service (optional)

## Monitoring & Debugging

- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Ready: http://localhost:8000/ready
- Grafana: http://localhost:3001 (admin/admin)
- MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
- OpenSearch Dashboards: http://localhost:5601

## Error Handling Patterns

The codebase uses structured error responses:
```python
# Services return envelopes with error details
{
    "ok": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input",
        "details": {...}
    }
}
```

Always check `ok` field before accessing `result` in responses.