# Developer Onboarding Guide

Complete onboarding guide for developers working on SIGN X Studio Clone.

## Overview

**Total Duration**: 6 hours (self-paced)  
**Format**: Self-guided with code walkthrough  
**Prerequisites**: Python 3.11+, FastAPI experience, Git knowledge

## Module 1: Codebase Tour (60 minutes)

### Repository Structure

```
calcusign-apex-clone/
├── services/
│   ├── api/              # FastAPI application
│   │   └── src/apex/api/
│   │       ├── routes/   # API route handlers
│   │       ├── db.py     # Database models
│   │       ├── utils/    # Utility functions
│   │       └── common/   # Shared code
│   ├── worker/           # Celery workers
│   └── signcalc-service/ # Engineering calculations
├── tests/                # Test suites
├── docs/                 # Documentation
└── infra/                # Infrastructure configs
```

### Key Modules

#### API Routes (`services/api/src/apex/api/routes/`)

- `projects.py` - Project CRUD operations
- `site.py` - Site resolution (geocoding, wind data)
- `cabinets.py` - Cabinet geometry calculations
- `poles.py` - Pole filtering and selection
- `direct_burial.py` - Direct burial foundation design
- `baseplate.py` - Baseplate validation
- `submission.py` - Project submission workflow
- `payloads.py` - Design payload management

#### Common Utilities (`services/api/src/apex/api/common/`)

- `models.py` - Response envelope models
- `helpers.py` - Shared helper functions
- `transactions.py` - Database transaction management
- `envelope.py` - Envelope creation utilities

#### Database Models (`services/api/src/apex/api/db.py`)

- `Project` - Project metadata
- `ProjectPayload` - Design snapshots
- `ProjectEvent` - Audit trail

### Code Walkthrough

**Example: Creating an Endpoint**

```python
# services/api/src/apex/api/routes/example.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..common.models import make_envelope
from ..common.transactions import with_transaction
from ..db import get_db
from ..deps import get_code_version, get_model_config

router = APIRouter(prefix="/example", tags=["example"])

@router.post("/calculate")
@with_transaction
async def calculate(
    inputs: dict,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    # Business logic
    result = perform_calculation(inputs)
    
    # Return envelope
    return make_envelope(
        result=result,
        assumptions=["Calculation complete"],
        confidence=0.95,
        inputs=inputs,
        outputs=result,
        code_version=get_code_version(),
        model_config=get_model_config(),
    )
```

## Module 2: Development Setup (45 minutes)

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git
- VS Code (recommended)

### Local Environment Setup

#### Step 1: Clone Repository

```bash
git clone <repository-url>
cd calcusign-apex-clone
```

#### Step 2: Setup Python Environment

```bash
cd services/api
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### Step 3: Start Dependencies

```bash
# Start database, Redis, MinIO
docker compose -f infra/compose.yaml up -d db cache object search
```

#### Step 4: Run Migrations

```bash
cd services/api
alembic upgrade head
```

#### Step 5: Start API

```bash
uvicorn apex.api.main:app --reload --port 8000
```

### Development Tools

**Code Formatting:**
```bash
# Format code
ruff format services/

# Lint
ruff check services/

# Type checking
mypy services/api/src/apex
```

**Pre-commit Hooks:**
```bash
pre-commit install
# Hooks run on commit:
# - ruff format
# - ruff check
# - mypy
```

## Module 3: Testing Practices (60 minutes)

### Test Structure

```
tests/
├── unit/           # Unit tests
├── service/        # Service/integration tests
├── contract/       # Contract tests (Envelope)
├── e2e/            # End-to-end tests
└── conftest.py     # Test fixtures
```

### Writing Tests

#### Unit Test Example

```python
# tests/unit/test_calculations.py
import pytest
from apex.api.routes.cabinets import derive_cabinets

@pytest.mark.asyncio
async def test_derive_cabinets():
    inputs = {
        "overall_height_ft": 25.0,
        "cabinets": [
            {"width_ft": 14.0, "height_ft": 8.0, "depth_in": 12.0}
        ]
    }
    
    result = await derive_cabinets(inputs)
    
    assert result.data["A_ft2"] == 112.0
    assert result.confidence >= 0.9
    assert len(result.assumptions) > 0
```

#### Contract Test Example

```python
# tests/contract/test_envelope.py
@pytest.mark.parametrize("endpoint", ALL_ENDPOINTS)
async def test_endpoint_returns_envelope(client, endpoint):
    response = await client.post(endpoint, json={...})
    envelope = response.json()
    
    assert "data" in envelope
    assert "confidence" in envelope
    assert 0.0 <= envelope["confidence"] <= 1.0
    assert "content_sha256" in envelope
```

### Running Tests

```bash
# All tests
pytest

# Specific suite
pytest tests/unit/
pytest tests/service/
pytest tests/contract/

# With coverage
pytest --cov=services/api/src/apex --cov-report=html
```

## Module 4: Deployment Procedures (45 minutes)

### CI/CD Pipeline

**GitHub Actions Workflow:**
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: pytest
      - name: Check coverage
        run: pytest --cov --cov-report=xml
```

**Deployment Process:**
1. Push to `main` branch
2. CI runs tests
3. If tests pass: Deploy to staging
4. Manual approval: Deploy to production

### Local Testing

```bash
# Run full test suite
pytest tests/ -v

# Run with coverage
pytest --cov --cov-report=term-missing

# Run specific test
pytest tests/unit/test_calculations.py::test_derive_cabinets
```

### Deployment Commands

```bash
# Staging deployment
git checkout staging
git merge main
git push

# Production deployment (after approval)
git checkout production
git merge staging
git push
```

## Module 5: Code Standards (30 minutes)

### Coding Style

**Python:**
- Follow PEP 8
- Use type hints
- Document functions
- Keep functions small (<50 lines)

**Example:**
```python
from typing import Optional

async def calculate_footing(
    diameter_ft: float,
    soil_psf: float,
    num_poles: int = 1,
) -> dict[str, float]:
    """
    Calculate footing depth for given diameter.
    
    Args:
        diameter_ft: Footing diameter in feet
        soil_psf: Soil bearing capacity in psf
        num_poles: Number of poles supported
        
    Returns:
        Dictionary with depth_ft and concrete_yards
    """
    # Implementation
    ...
```

### Envelope Pattern

**Always Return Envelope:**
```python
return make_envelope(
    result=data,
    assumptions=["..."],
    confidence=0.95,
    inputs=request_data,
    outputs=result_data,
    code_version=get_code_version(),
    model_config=get_model_config(),
)
```

### Error Handling

**Use HTTPException:**
```python
from fastapi import HTTPException

if not project:
    raise HTTPException(
        status_code=404,
        detail="Project not found"
    )
```

## Module 6: Best Practices (30 minutes)

### Determinism

**Always Round Floats:**
```python
from apex.api.common.envelope import round_floats

result = {
    "depth_ft": round_floats(calculated_depth, precision=3)
}
```

**Deterministic Sorting:**
```python
import random
random.seed(hash(request_id))
sorted_list = sorted(items, key=lambda x: random.random())
```

### Performance

**Use Async/Await:**
```python
# Good
async def get_project(project_id: str):
    project = await db.get(Project, project_id)
    return project

# Bad
def get_project(project_id: str):
    project = db.query(Project).filter_by(id=project_id).first()
    return project
```

**Database Queries:**
- Use indexes
- Avoid N+1 queries
- Use eager loading when needed

### Security

**Input Validation:**
```python
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    customer: Optional[str] = Field(None, max_length=255)
```

**Secrets Management:**
- Never commit secrets
- Use environment variables
- Use Vault/AWS Secrets Manager in production

## Module 7: Debugging (30 minutes)

### Local Debugging

**VS Code Configuration:**
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "apex.api.main:app",
        "--reload"
      ],
      "jinja": true
    }
  ]
}
```

**Debugging Tips:**
- Use `logger.debug()` for detailed logs
- Check structured logs (JSON format)
- Use `pdb` breakpoints
- Review trace IDs for request tracking

### Production Debugging

**Access Logs:**
```bash
# Kubernetes
kubectl logs -n apex deployment/apex-api --tail=100

# Docker Compose
docker compose logs api --tail=100
```

**Query Database:**
```bash
# Connect to database
psql $APEX_DATABASE_URL

# Check project
SELECT * FROM projects WHERE project_id = 'proj_123';

# Check events
SELECT * FROM project_events 
WHERE project_id = 'proj_123' 
ORDER BY created_at DESC;
```

## Module 8: Contributing (30 minutes)

### Pull Request Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Make Changes**
   - Write code
   - Add tests
   - Update documentation

3. **Run Tests**
   ```bash
   pytest
   ruff check .
   mypy .
   ```

4. **Create PR**
   - Fill out PR template
   - Request reviews
   - Address feedback

### PR Template

```markdown
## Description
Brief description of changes

## Related Issue
Closes #123

## Testing
- [ ] Unit tests added
- [ ] Integration tests added
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Tests passing
- [ ] No linter errors
```

## Resources

### Documentation

- [API Reference](../api/api-reference.md)
- [Envelope Pattern](../api/envelope-pattern.md)
- [Operational Runbooks](../operations/operational-runbooks.md)

### Code Examples

- [Route Examples](../examples/routes/)
- [Test Examples](../examples/tests/)
- [Utility Examples](../examples/utils/)

### Community

- Slack: #apex-dev
- GitHub: Issues and Discussions
- Weekly Office Hours: Tuesdays 2-3 PM

---

**Next Steps:**
- [**User Training Guide**](user-training-guide.md)
- [**Admin Training Guide**](admin-training-guide.md)

