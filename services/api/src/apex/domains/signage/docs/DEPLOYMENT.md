# APEX Signage Engineering Solvers - Deployment Guide

## Environment Requirements

### Python
- **Version**: 3.11 (required)
- **Interpreter**: CPython (not PyPy)

### System Dependencies
```bash
# Ubuntu/Debian
apt-get install -y python3.11 python3-pip build-essential

# For LaTeX (optional, for PDF generation)
apt-get install -y texlive-latex-base texlive-latex-extra
```

### Python Dependencies
```toml
numpy==1.26.4
scipy==1.11.4
scikit-learn==1.4.1.post1
deap==1.4.1
matplotlib==3.9.0
jinja2==3.1.3
weasyprint==61.2
pandas==2.2.1
pint==0.24.3
pydantic==2.8.2
```

Install via:
```bash
pip install -r requirements.txt
# or
uv pip install -r pyproject.toml
```

## Configuration

### Environment Variables

```bash
# Solver Configuration
APEX_SOLVER_DEBUG=0              # Enable debug mode (verbose logging)
APEX_SOLVER_CACHE_SIZE=1000     # ML prediction cache size
APEX_SOLVER_COALESCING_MS=100   # Request coalescing window

# Performance
APEX_SOLVER_MAX_WORKERS=8        # Batch processing workers
APEX_SOLVER_GA_MAX_GEN=30       # GA max generations

# Calibration
APEX_SOLVER_FOOTING_K=1.0       # Footing calibration constant
APEX_SOLVER_SOIL_MULT=1.0       # Soil bearing multiplier

# Field Data
APEX_FIELD_DATA_PATH=/data/eagle_sign_projects.csv
```

### Solver Versions

Solver versions are tracked in `solver_versioning.py`. To update:

```python
from apex.domains.signage.solver_versioning import solver_version

@solver_version("1.3.0")
def my_new_solver(...):
    ...
```

## Deployment Steps

### 1. Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install uv && uv pip install -r pyproject.toml

# Copy source
COPY src /app/src

# Set environment
ENV PYTHONPATH=/app/src
ENV APEX_SOLVER_DEBUG=0

CMD ["python", "-m", "apex.api.main"]
```

### 2. Health Checks

Solver health check endpoint:
```bash
curl http://api:8000/health
```

Response:
```json
{
  "result": {"status": "ok"},
  "confidence": 1.0,
  "trace": {
    "solver_versions": {
      "derive_loads": "1.2.0",
      "filter_poles": "1.1.0",
      ...
    }
  }
}
```

### 3. Monitoring

**Metrics to Track:**
- Solver latency (p50, p95, p99)
- Cache hit rate
- Error rate by solver function
- Convergence rate (for optimization)

**Alerts:**
- p95 latency > 100ms
- Error rate > 1%
- Cache hit rate < 50%
- Convergence failures > 5%

## Maintenance

### Updating AISC Database

1. Export AISC sections to CSV:
```bash
python scripts/import_aisc_sections.py data/aisc_v16.csv
```

2. Update database:
```sql
-- Clear old data
TRUNCATE material_catalog;

-- Import new data
\copy material_catalog FROM 'aisc_v16.csv' CSV HEADER;
```

### Updating Calibration Constants

1. Run field validation:
```python
from apex.domains.signage.validation import auto_tune_parameters

tuned_params = auto_tune_parameters(
    Path("data/eagle_sign_projects.csv"),
    objective="minimize_error_with_safety",
)
```

2. Update database:
```sql
UPDATE calibration_constants
SET value = 1.05
WHERE name = 'footing_calibration_k' AND version = 'v1';
```

### Retraining ML Models

1. Collect training data:
```bash
# Export project data
psql -c "COPY (SELECT ...) TO 'projects.csv' CSV HEADER;"
```

2. Train models:
```python
from apex.domains.signage.ml_models import ConfigPredictor

predictor = ConfigPredictor()
predictor.train(training_data)
# Save model
```

3. Deploy:
```bash
# Update model file
cp new_model.pkl /app/models/config_predictor.pkl
# Restart service
```

### Versioning Solver Changes

1. Update version in `solver_versioning.py`:
```python
_SOLVER_VERSIONS["derive_loads"] = "1.3.0"
```

2. Tag in git:
```bash
git tag solver-v1.3.0
```

3. Document changes in CHANGELOG.md

## Troubleshooting

### Solver Fails

1. Check logs for `SolverError` or `ConvergenceError`
2. Review diagnostics in `trace.data.intermediates`
3. Check input validation errors
4. Verify solver versions

### Performance Degradation

1. Profile with cProfile:
```python
python -m cProfile -o profile.stats benchmarks/scale_test.py
```

2. Check cache hit rates
3. Review batch processing worker count
4. Verify numpy/SciPy versions

### Memory Issues

1. Reduce cache sizes
2. Limit batch size
3. Enable model quantization
4. Monitor memory usage

## Production Checklist

- [ ] All tests passing (pytest tests/ -v)
- [ ] Code coverage ≥90% (pytest --cov)
- [ ] Linting clean (ruff check)
- [ ] Type checking clean (mypy)
- [ ] Performance benchmarks pass (10K projects <100s)
- [ ] Field validation completed (RMSE <10%)
- [ ] Documentation updated (ARCHITECTURE.md, EQUATIONS.md)
- [ ] Environment variables configured
- [ ] Monitoring/alerts configured
- [ ] Health checks passing
- [ ] Deployment tested in staging

