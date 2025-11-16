# APEX Worker Service

Celery worker service for async task processing in the APEX mechanical engineering copilot.

## Tasks

All tasks follow deterministic principles - math/physics computed in Python, not LLM.

### Health & Monitoring

- **`health.ping`**: Worker health check
  ```python
  from apex.worker.main import app
  result = app.send_task("health.ping")
  ```

### Engineering Tasks

- **`materials.score`**: Score materials based on DFMA criteria
  ```python
  result = app.send_task("materials.score", args=[{
      "material_type": "steel",
      "grade": "A500B",
      "thickness_in": 0.25,
  }])
  ```

- **`dfma.analyze`**: Analyze design for manufacturability and assembly
  ```python
  result = app.send_task("dfma.analyze", args=[{
      "features": [...],
      "dimensions": {...},
      "material": {...},
  }])
  ```

- **`stackup.calculate`**: Calculate material stackup properties
  ```python
  result = app.send_task("stackup.calculate", args=[[
      {"material": "steel", "thickness_in": 0.125, "density_lb_ft3": 490},
      {"material": "foam", "thickness_in": 0.5, "density_lb_ft3": 2},
  ]])
  ```

- **`cad.generate_macro`**: Generate CAD macro/script from design
  ```python
  result = app.send_task("cad.generate_macro", args=[{
      "design_id": "xxx",
      "geometry": {...},
      "material": {...},
  }, "freecad"])
  ```

- **`standards.check`**: Check design compliance against engineering standards
  ```python
  result = app.send_task("standards.check", args=[{
      "design": {...},
  }, ["ASCE 7-16", "AISC 360"]])
  ```

## Configuration

Environment variables:
- `CELERY_BROKER_URL` or `REDIS_URL`: Redis broker URL (default: `redis://cache:6379/0`)
- `CELERY_RESULT_BACKEND`: Result backend URL (defaults to broker URL)
- `PREFETCH`: Worker prefetch multiplier (default: `1`)
- `VIS_TIMEOUT_S`: Broker visibility timeout in seconds (default: `120`)
- `TASK_RETRY_DELAY`: Default retry delay in seconds (default: `5`)

## Running

### Standalone
```bash
cd apex/services/worker
python -m apex.worker.main
```

### Docker Compose
The worker is included in `apex/infra/compose.yaml`:
```bash
cd apex
docker compose -f infra/compose.yaml up worker
```

## Task Features

- **Structured Logging**: All tasks use structlog for JSON logging
- **Retry Logic**: Automatic retries with exponential backoff (3 retries by default)
- **Error Handling**: BaseTask class provides consistent error logging
- **Deterministic**: All calculations are pure Python - no LLM computation
- **Idempotent**: Tasks designed to be safely retried

## Architecture Notes

- Tasks are separated from app configuration (`main.py` vs `tasks.py`)
- BaseTask provides structured logging hooks
- All tasks follow APEX envelope principles (trace IDs, assumptions, confidence)
- Tasks integrate with domain services (materials, dfma, stackup, cad, standards) when available

## Using Tasks from API

The `packages/clients/worker_client.py` module provides helper functions for enqueueing tasks:

```python
from packages.clients import (
    enqueue_materials_score,
    enqueue_dfma_analysis,
    enqueue_stackup_calculation,
    get_task_result,
)

# Enqueue a task
task_id = enqueue_materials_score({
    "material_type": "steel",
    "grade": "A500B",
})

# Optionally wait for result (with timeout)
result = get_task_result(task_id, timeout=10.0)
```

Tasks run asynchronously in the worker service, allowing the API to return immediately while computation happens in the background.

## Future Integrations

Tasks currently return deterministic stubs. Future work:
- Wire `materials.score` → `materials-service`
- Wire `dfma.analyze` → `dfma-service`
- Wire `stackup.calculate` → `stackup-service`
- Wire `cad.generate_macro` → `cad-worker`
- Wire `standards.check` → `standards-service`

