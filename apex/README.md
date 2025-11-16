# APEX Monorepo

Deterministic, test-first, and containerized mechanical-engineering copilot.

## Quickstart

```bash
cd apex
cp .env.example .env
make up
make smoke
```

## Architecture

- **API Service** (`services/api`): FastAPI with envelope responses, health/ready endpoints, rate limiting, structured logging
- **Worker Service** (`services/worker`): Celery worker for async tasks
- **Infrastructure** (`infra/`): Docker Compose, K8s manifests, devcontainer
- **Shared Packages** (`packages/`): Schemas, clients, utils for cross-service use
- **Services** (`services/*`): Domain-specific microservices (materials, dfma, stackup, standards)

## API Endpoints

### Core

- `GET /health` - Shallow health check (no dependencies)
- `GET /ready` - Deep readiness (checks Redis)
- `GET /metrics` - Prometheus metrics
- `GET /docs` - Interactive API documentation

### Projects

- `GET /projects` - List projects
- `POST /projects` - Create project
  ```json
  {"name": "My Sign", "notes": "Optional notes"}
  ```
- `GET /projects/{id}` - Get project by ID

### Pricing

- `POST /projects/{project_id}/estimate` - Get pricing estimate
  ```json
  {"height_ft": 20, "addons": ["calc_packet"]}
  ```

### Site & Common

- `POST /signage/common/site/resolve` - Resolve address to location/wind zone
  ```json
  {"address": "123 Main St, City, State"}
  ```

- `POST /signage/common/cabinets/derive` - Calculate cabinet area/volume/weight
  ```json
  {"width_in": 48, "height_in": 96, "depth_in": 12, "density_lb_ft3": 50}
  ```

- `POST /signage/common/cabinets/add` - Sum multiple cabinets
  ```json
  {"items": [{"width_in": 48, "height_in": 96, "depth_in": 12, "density_lb_ft3": 50}]}
  ```

- `POST /signage/common/poles/options` - Get pole options by moment requirement
  ```json
  {"moment_required_ft_lb": 2500, "material": "steel"}
  ```

### Foundations

- `POST /signage/direct_burial/footing/solve` - Calculate footing volume/weight
  ```json
  {"diameter_in": 18, "height_ft": 3}
  ```

- `POST /signage/baseplate/checks` - Baseplate stress checks
  ```json
  {"plate_thickness_in": 0.5, "weld_size_in": 0.25, "anchors": 4}
  ```

## Response Envelope

All endpoints return a standardized envelope:

```json
{
  "result": {...},
  "assumptions": ["assumption1"],
  "confidence": 0.95,
  "trace": {
    "data": {
      "inputs": {...},
      "intermediates": {...},
      "outputs": {...}
    },
    "code_version": {"git_sha": "...", "dirty": false},
    "model_config": {"provider": "apex", "model": "dev", "temperature": 0.0}
  }
}
```

## Development

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local dev)
- `make` (or run commands directly)

### Environment Variables

Copy `.env.example` to `.env` and adjust:

- `APEX_ENV` - Environment (dev/production)
- `PRICING_VERSION` - Pricing config version (v1)
- `REDIS_URL` - Redis broker URL
- `CORS_ALLOWED_ORIGINS` - Comma-separated origins

### Running Services

```bash
make up          # Start all services
make down        # Stop all services
make logs        # Tail logs
make smoke       # Run smoke tests
make verify TASK=demo-materials-1  # Verify task
```

### Optional Services

Enable optional services with profiles:

```bash
docker compose --profile db --profile search --profile storage -f infra/compose.yaml up
```

## Testing

```bash
pytest tests/    # Run all tests
pytest tests/test_health_ready_pricing.py  # Specific test
```

## Kubernetes

Manifests in `infra/k8s/`:

- `api-deployment.yaml` - API deployment with healthchecks
- `api-service.yaml` - LoadBalancer service

## Make Targets

- `up` - Start dev stack
- `down` - Stop dev stack
- `logs` - Tail service logs
- `smoke` - Run smoke checks
- `verify TASK=...` - Verify task integrity
- `gc-dry` - Dry-run CAS garbage collection
- `gc` - Prune unreferenced CAS blobs
- `lint` - Run ruff
- `typecheck` - Run mypy
- `test` - Run pytest
- `sync-api` - Sync API dependencies
- `sync-worker` - Sync worker dependencies

## Service Status

- ✅ API service: Complete with envelope, middleware, error handlers
- ✅ Worker service: Complete with Celery tasks
- ✅ Infrastructure: Compose + K8s manifests
- ✅ Shared packages: Schemas, clients, utils
- 🟡 Domain services: Stub implementations (materials, dfma, stackup, standards)
- 🟡 Route stubs: Enhanced with mock calculations
- ✅ Testing: Health, ready, pricing, e2e flows
