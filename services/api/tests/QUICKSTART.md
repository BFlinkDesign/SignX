# Test Suite Quick Start Guide

## Prerequisites

- Python 3.11
- PostgreSQL 15+ running locally
- UV package manager (optional, recommended)

## Installation

### Option 1: Using UV (Recommended)

```bash
# Navigate to API directory
cd services/api

# Install with dev dependencies
uv pip install -e ".[dev]"

# Or if using regular pip
pip install -e ".[dev]"
```

### Option 2: Manual Installation

```bash
cd services/api

# Install package
pip install -e .

# Install test dependencies
pip install pytest==8.2.2 \
    pytest-asyncio==0.23.7 \
    pytest-benchmark==4.0.0 \
    pytest-cov==5.0.0 \
    httpx==0.27.0
```

## Database Setup

### Create Test Database

```bash
# Using psql
psql -U postgres -c "CREATE DATABASE apex_test;"
psql -U postgres -c "CREATE USER apex WITH PASSWORD 'apex';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE apex_test TO apex;"

# Or using Docker
docker exec -it postgres psql -U postgres -c "CREATE DATABASE apex_test;"
```

### Run Migrations

```bash
# Set test database URL
export TEST_DATABASE_URL="postgresql+asyncpg://apex:apex@localhost:5432/apex_test"

# Run Alembic migrations (if needed)
cd services/api
alembic upgrade head
```

## Verify Installation

```bash
# Check pytest is installed
pytest --version
# Expected output: pytest 8.2.2

# Check pytest-cov is installed
pytest --cov --version
# Should not error

# Check test discovery
pytest --collect-only
# Should show 200+ tests collected
```

## Run Your First Tests

### 1. Run Unit Tests (Fast)

```bash
cd services/api

# Run all unit tests
pytest tests/unit/ -v

# Expected output:
# ==================== test session starts ====================
# collected 50+ items
# tests/unit/test_asce7_wind.py::TestExposureCoefficients::test_kz_table_values_exact[15-B-0.57] PASSED
# tests/unit/test_asce7_wind.py::TestExposureCoefficients::test_kz_table_values_exact[20-B-0.62] PASSED
# ...
# ==================== 50+ passed in 2.5s ====================
```

### 2. Run Single Test File

```bash
# Test ASCE 7-22 wind calculations
pytest tests/unit/test_asce7_wind.py -v

# Test single pole solver
pytest tests/unit/test_single_pole_solver.py -v
```

### 3. Run with Coverage

```bash
# Run all tests with coverage
pytest --cov=apex --cov-report=term-missing

# Expected output:
# ---------- coverage: platform win32, python 3.11.x -----------
# Name                                    Stmts   Miss  Cover   Missing
# ---------------------------------------------------------------------
# src/apex/domains/signage/asce7_wind.py    150      5    96%   45-48
# src/apex/domains/signage/single_pole.py   200     10    95%   120-125
# ...
# ---------------------------------------------------------------------
# TOTAL                                    2000    150    92%
```

### 4. Run Database Tests (Requires PostgreSQL)

```bash
# Run AISC database tests
pytest tests/test_aisc_database.py -v -m database

# Expected: Tests may skip if AISC data not seeded
# To seed AISC data:
cd services/api
python scripts/seed_aisc_sections.py
```

## Common Test Commands

### By Test Type

```bash
# Unit tests only (fast, no database)
pytest -m "unit" -v

# Integration tests (slower, uses database)
pytest -m "integration" -v

# Database tests only
pytest -m "database" -v

# Skip slow tests
pytest -m "not slow" -v
```

### By Coverage

```bash
# Generate HTML coverage report
pytest --cov=apex --cov-report=html
# Then open: htmlcov/index.html

# Check if coverage meets 80% threshold
pytest --cov=apex --cov-fail-under=80
# Exits with error if coverage < 80%
```

### By Module

```bash
# Test wind load calculations only
pytest tests/unit/test_asce7_wind.py -v

# Test single pole solver only
pytest tests/unit/test_single_pole_solver.py -v

# Test AISC database only
pytest tests/test_aisc_database.py -v
```

### Debugging Tests

```bash
# Show print statements
pytest -v -s

# Stop on first failure
pytest -x

# Show full traceback
pytest --tb=long

# Run specific test
pytest tests/unit/test_asce7_wind.py::TestExposureCoefficients::test_kz_table_values_exact -v
```

## Expected Results

### ✅ Successful Run

```
==================== test session starts ====================
platform win32 -- Python 3.11.x, pytest-8.2.2
collected 200 items

tests/unit/test_asce7_wind.py ............................. [ 15%]
tests/unit/test_single_pole_solver.py .................... [ 35%]
tests/test_aisc_database.py ............................. [ 60%]
tests/unit/test_envelope.py ............................. [ 75%]
tests/unit/test_solvers.py .............................. [100%]

==================== 200 passed in 8.5s ====================
```

### ✅ With Coverage

```
==================== test session starts ====================
collected 200 items

tests/unit/test_asce7_wind.py ............................
tests/unit/test_single_pole_solver.py ....................
...

---------- coverage: platform win32, python 3.11.x -----------
Name                                    Stmts   Miss  Cover
-------------------------------------------------------------
src/apex/domains/signage/asce7_wind.py    150      5    96%
src/apex/domains/signage/single_pole.py   200     10    95%
-------------------------------------------------------------
TOTAL                                    2000    150    92%

==================== 200 passed in 10.2s ====================
```

## Troubleshooting

### Issue: "No module named pytest"

**Solution:**
```bash
pip install pytest pytest-asyncio pytest-cov
```

### Issue: "Database connection failed"

**Solution:**
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Verify test database exists
psql -U apex -d apex_test -c "SELECT 1"

# Create if missing
createdb -U apex apex_test

# Set environment variable
export TEST_DATABASE_URL="postgresql+asyncpg://apex:apex@localhost:5432/apex_test"
```

### Issue: "aisc_shapes_v16 table does not exist"

**Solution:**
```bash
# Run Alembic migrations
cd services/api
alembic upgrade head

# Or seed AISC data
python scripts/seed_aisc_sections.py
```

### Issue: "Async fixture error"

**Solution:**
Ensure `pytest-asyncio` is installed:
```bash
pip install pytest-asyncio==0.23.7
```

And tests use `@pytest.mark.asyncio`:
```python
@pytest.mark.asyncio
async def test_async_function(db_session):
    result = await db_session.execute(...)
```

### Issue: "Coverage not showing my module"

**Solution:**
Check `pyproject.toml` has correct source path:
```toml
[tool.coverage.run]
source = ["src/apex"]  # Must match your source directory
```

### Issue: "Tests are slow"

**Solution:**
Run only unit tests (skip integration/database tests):
```bash
pytest -m "unit and not slow" -v
```

## Next Steps

1. ✅ Verify installation: `pytest --version`
2. ✅ Run unit tests: `pytest tests/unit/ -v`
3. ✅ Check coverage: `pytest --cov=apex --cov-report=html`
4. ✅ Open coverage report: `htmlcov/index.html`
5. ✅ Read full documentation: `tests/README.md`

## Quick Reference

| Command | Purpose |
|---------|---------|
| `pytest` | Run all tests |
| `pytest -v` | Verbose output |
| `pytest -m "unit"` | Run unit tests only |
| `pytest -m "not slow"` | Skip slow tests |
| `pytest --cov=apex` | Run with coverage |
| `pytest --cov-report=html` | Generate HTML coverage |
| `pytest -x` | Stop on first failure |
| `pytest -s` | Show print statements |
| `pytest --collect-only` | List all tests |

## Resources

- 📖 **Full Documentation:** `tests/README.md`
- 📊 **Implementation Summary:** `tests/TESTING_IMPLEMENTATION_SUMMARY.md`
- 🔧 **Pytest Docs:** https://docs.pytest.org/
- 🐍 **pytest-asyncio:** https://pytest-asyncio.readthedocs.io/

## Success Criteria

You're ready to develop when:

- ✅ `pytest --version` shows pytest 8.2.2
- ✅ `pytest --collect-only` shows 200+ tests
- ✅ `pytest tests/unit/ -v` passes with 50+ tests
- ✅ `pytest --cov=apex` shows 80%+ coverage
- ✅ `htmlcov/index.html` opens in browser

**Happy testing!** 🎉
