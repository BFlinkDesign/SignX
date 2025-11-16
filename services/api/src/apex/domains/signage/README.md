# APEX Signage Engineering Module

Deterministic, auditable sign structure design platform. CalcuSign parity with APEX enhancements.

## Architecture

- **Models**: Pydantic v2 schemas for all domain objects
- **Solvers**: Pure Python deterministic calculations
- **Routes**: FastAPI endpoints returning APEX envelope format
- **Tasks**: Celery async jobs for PDF generation, PM submission, email

## Setup

### 1. Database Setup

```bash
# Apply schemas
psql $DATABASE_URL -f services/api/src/apex/domains/signage/db/schemas.sql

# Seed defaults
python scripts/seed_defaults.py

# Import AISC sections (requires download from https://www.aisc.org/resources/shapes-database/)
export AISC_CSV_PATH=data/aisc-shapes-v16.csv
python scripts/seed_aisc_sections.py
```

### 2. Environment Variables

```bash
DATABASE_URL=postgresql://apex:apex@localhost:5432/apex
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

## API Endpoints

All endpoints return APEX envelope: `{ result, assumptions[], confidence, trace{...} }`

### Common Design

- `POST /signage/site/resolve` - Resolve wind/snow loads from address
- `POST /signage/cabinets/derive` - Derive load parameters
- `POST /signage/poles/options` - Filter feasible pole sizes

### Direct Burial

- `POST /signage/direct_burial/footing/solve` - Compute footing depth
- `POST /signage/direct_burial/footing/assist` - Request engineering assist

### Base Plate

- `POST /signage/baseplate/checks` - Run design checks
- `POST /signage/baseplate/request_engineering` - Request assist

## Usage Examples

### Derive Loads

```bash
curl -X POST http://localhost:8000/signage/cabinets/derive \
  -H "Content-Type: application/json" \
  -d '{
    "overall_height_ft": 25.0,
    "cabinets": [
      {"width_ft": 14.0, "height_ft": 8.0}
    ]
  }'
```

### Solve Footing Depth

```bash
curl -X POST http://localhost:8000/signage/direct_burial/footing/solve \
  -H "Content-Type: application/json" \
  -d '{
    "mu_kipft": 100.0,
    "footing": {"diameter_ft": 4.0, "shape": "round"},
    "soil_psf": 3000.0,
    "poles": 1
  }'
```

### Base Plate Checks

```bash
curl -X POST http://localhost:8000/signage/baseplate/checks \
  -H "Content-Type: application/json" \
  -d '{
    "plate": {
      "plate_w_in": 12.0,
      "plate_l_in": 12.0,
      "plate_thk_in": 1.25,
      "weld_size_in": 0.25,
      "anchor_dia_in": 0.625,
      "anchor_grade_ksi": 60.0,
      "anchor_embed_in": 12.0,
      "rows": 3,
      "bolts_per_row": 2,
      "row_spacing_in": 10.0,
      "edge_distance_in": 2.0
    },
    "mu_kipft": 50.0
  }'
```

## Determinism & Testing

All solvers are pure functions with deterministic outputs:

- Fixed inputs → Fixed outputs (reproducible)
- Monotonicity enforced (e.g., smaller diameter → deeper footing)
- Unit tests in `tests/unit/test_signage_solvers.py`
- Async wrappers are generated via `make_async` (see `solvers.py`) to keep the
  engineering math pure. When adding a new solver:
  1. Implement the synchronous version first.
  2. Wrap it with `make_async()`.
  3. If caching is required, apply `deterministic_cache` (from
     `signage/cache.py`) so concurrent workers share memoized values safely.
  4. Document the associated code references in the function docstring using
     constants from `signage/code_refs.py`.

The workflow above keeps math deterministic while allowing FastAPI endpoints to
remain fully async.

Run tests:

```bash
pytest tests/unit/test_signage_solvers.py -v
```

## Roadmap

- [ ] ASCE 7-22 Hazard Tool API integration
- [ ] Auto-solve optimizer for base plates
- [ ] Interactive 2D canvas with two-way binding
- [ ] BOM export endpoints
- [ ] PDF report generation (ReportLab)
- [ ] PM submission adapter (OpenProject/Smartsheet)

## References

- AISC Steel Construction Manual v16.0
- ASCE 7-22 Minimum Design Loads
- ACI 318-19 Building Code
- AWS D1.1 Structural Welding Code

