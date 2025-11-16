# SignX-Studio Test Suite

Comprehensive pytest test suite for structural engineering calculations with ASCE 7-22, IBC 2024, and AISC 360-22 compliance validation.

## Overview

This test suite provides:
- **80%+ code coverage** on domain modules
- **Async database fixtures** with transaction rollback
- **Deterministic calculation validation** (same inputs → same outputs)
- **Parametrized edge case testing** for extreme conditions
- **Performance benchmarks** for critical queries
- **Code reference documentation** (IBC, ASCE, AISC sections)

## Quick Start

```bash
# Install test dependencies
cd services/api
pip install -e ".[dev]"

# Run all tests with coverage
pytest

# Run specific test suites
pytest tests/unit/                          # Unit tests only (fast)
pytest tests/integration/                   # Integration tests
pytest tests/test_aisc_database.py          # AISC database tests

# Run with markers
pytest -m "unit"                            # Only unit tests
pytest -m "not slow"                        # Skip slow tests
pytest -m "database"                        # Only database tests
pytest -m "determinism"                     # Only determinism checks

# Coverage reports
pytest --cov-report=html                    # HTML coverage report
pytest --cov-report=term-missing            # Terminal with missing lines
open htmlcov/index.html                     # View coverage in browser
```

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures, database setup
├── unit/
│   ├── test_single_pole_solver.py # AISC 360-22 ASD structural analysis
│   ├── test_asce7_wind.py         # ASCE 7-22 wind load calculations
│   ├── test_envelope.py           # API envelope pattern validation
│   └── test_solvers.py            # Multi-solver integration tests
├── integration/
│   └── ...                        # API route integration tests
├── contract/
│   └── ...                        # OpenAPI contract tests
└── test_aisc_database.py          # AISC Shapes Database v16.0 tests
```

## Test Coverage by Module

### `apex.domains.signage.single_pole_solver`
**Target: 90%+ coverage**

Tests:
- ✅ AISC 360-22 ASD bending stress: `fb = M/Sx ≤ Fb = 0.66×Fy`
- ✅ AISC 360-22 ASD shear stress: `fv = V/A ≤ Fv = 0.40×Fy`
- ✅ Deflection limits: `δ = FL³/(3EI) ≤ L/240`
- ✅ IBC 2024 overturning: Safety Factor ≥ 1.5
- ✅ Foundation sizing with passive pressure
- ✅ Edge cases: zero area, extreme heights, invalid sections

Example test:
```python
def test_bending_stress_calculation_aisc_chapter_f(hss_8x8x1_4):
    """
    Test bending stress: fb = M / Sx
    Reference: AISC 360-22 Chapter F, Allowable Stress Design
    """
    result = analyze_single_pole_sign(config)
    assert result.bending_stress_ratio < 1.0  # Must pass
```

### `apex.domains.signage.asce7_wind`
**Target: 95%+ coverage**

Tests:
- ✅ Velocity pressure exposure coefficients (Kz) from Table 26.10-1
- ✅ Wind importance factors from Table 1.5-2
- ✅ Velocity pressure: `qz = 0.00256 × Kz × Kzt × Kd × Ke × V²`
- ✅ Design wind pressure with force coefficients
- ✅ Total wind force and moment calculations
- ✅ Iowa Grimes baseline (115 mph, Exposure C)

Example test:
```python
@pytest.mark.parametrize("height,exposure,expected_kz", [
    (15, ExposureCategory.C, 0.85),
    (30, ExposureCategory.C, 0.98),
    (100, ExposureCategory.C, 1.26),
])
def test_kz_table_values_exact(height, exposure, expected_kz):
    """Verify Kz matches ASCE 7-22 Table 26.10-1 exactly."""
    kz = calculate_kz(height, exposure)
    assert kz == pytest.approx(expected_kz, abs=0.001)
```

### AISC Shapes Database (aisc_shapes_v16)
**Target: 85%+ coverage**

Tests:
- ✅ Database schema validation
- ✅ HSS section property lookups
- ✅ PIPE section property lookups
- ✅ Section selection queries (by moment capacity, slenderness)
- ✅ A1085 vs A500 filtering
- ✅ Query performance benchmarks (<100ms)
- ✅ Data integrity checks (weight/area consistency)

Example test:
```python
async def test_lookup_hss_8x8x1_4(aisc_connection):
    """
    Test HSS 8×8×1/4 lookup against AISC Manual v16.0.
    Reference: AISC Manual Table 1-11, HSS Rectangular
    """
    result = await aisc_connection.fetchrow(
        "SELECT * FROM aisc_shapes_v16 WHERE aisc_manual_label = $1",
        "HSS8X8X1/4"
    )
    assert result["weight_plf"] == pytest.approx(24.2, abs=0.1)
```

## Fixtures

### Database Fixtures

```python
# Async database session with auto-rollback
async def test_something(db_session: AsyncSession):
    result = await db_session.execute(select(Project))
    # Changes are rolled back after test

# AISC database connection
async def test_aisc_query(aisc_connection):
    result = await aisc_connection.fetch(
        "SELECT * FROM aisc_shapes_v16 WHERE type = 'HSS'"
    )
```

### Pole Section Fixtures

```python
def test_with_hss_pole(hss_8x8x1_4: PoleSection):
    """HSS 8×8×1/4 from AISC database"""

def test_with_pipe(pipe_6_std: PoleSection):
    """PIPE 6 STD from AISC database"""

def test_with_heavy_pole(hss_10x10x3_8: PoleSection):
    """HSS 10×10×3/8 A1085 high-strength"""
```

### Wind Configuration Fixtures

```python
def test_grimes_iowa(grimes_iowa_wind_config):
    """115 mph, Exposure C, Risk Category II"""

def test_high_wind(high_wind_config):
    """150 mph, Exposure D, Risk Category III"""
```

## Test Markers

Use markers to select test subsets:

```python
@pytest.mark.unit          # Fast, isolated unit test
@pytest.mark.integration   # Tests multiple components
@pytest.mark.database      # Requires database connection
@pytest.mark.slow          # Takes >1 second
@pytest.mark.determinism   # Validates calculation determinism
@pytest.mark.benchmark     # Performance benchmark
```

Run with markers:
```bash
pytest -m "unit"           # Only unit tests
pytest -m "not slow"       # Skip slow tests
pytest -m "database"       # Only database tests
```

## Coverage Requirements

Minimum coverage targets by module:

| Module | Target | Current |
|--------|--------|---------|
| `single_pole_solver.py` | 90% | TBD |
| `asce7_wind.py` | 95% | TBD |
| `cantilever_solver.py` | 85% | TBD |
| `double_pole_solver.py` | 85% | TBD |
| `monument_solver.py` | 85% | TBD |
| **Overall** | **80%** | **TBD** |

Check coverage:
```bash
pytest --cov=apex --cov-report=html
open htmlcov/index.html
```

## Writing New Tests

### Unit Test Template

```python
"""
Tests for [module name] - [IBC/ASCE/AISC reference].

Test Coverage:
- [Test category 1]
- [Test category 2]

References:
- IBC 2024 Section X.Y
- ASCE 7-22 Chapter Z
- AISC 360-22 Chapter W
"""

import pytest
from apex.domains.signage.module import function_to_test

class TestFeatureName:
    """Test [feature description]."""

    def test_basic_case(self):
        """
        Test [what you're testing].

        Hand calculation:
        - Input: X = 10
        - Formula: Y = 2×X
        - Expected: Y = 20

        Reference: [Code section]
        """
        result = function_to_test(x=10)
        assert result.y == pytest.approx(20, abs=0.01)

    @pytest.mark.parametrize("input,expected", [
        (10, 20),
        (20, 40),
        (30, 60),
    ])
    def test_parametrized(self, input, expected):
        """Test with multiple input cases."""
        result = function_to_test(x=input)
        assert result.y == pytest.approx(expected, abs=0.01)

    @pytest.mark.determinism
    def test_determinism(self):
        """Verify same inputs produce same outputs."""
        results = [function_to_test(x=10) for _ in range(5)]
        assert all(r.y == results[0].y for r in results)
```

### Database Test Template

```python
@pytest.mark.database
@pytest.mark.asyncio
class TestDatabaseFeature:
    """Test database interactions."""

    async def test_query(self, db_session: AsyncSession):
        """Test database query."""
        result = await db_session.execute(
            select(Model).where(Model.id == 1)
        )
        assert result is not None

    async def test_aisc_lookup(self, aisc_connection):
        """Test AISC database lookup."""
        result = await aisc_connection.fetchrow(
            "SELECT * FROM aisc_shapes_v16 WHERE designation = $1",
            "HSS8X8X1/4"
        )
        assert result["weight_plf"] == pytest.approx(24.2, abs=0.1)
```

## Best Practices

### 1. Hand Calculations in Docstrings
Every test should include hand calculations showing expected results:

```python
def test_moment_calculation(self):
    """
    Test moment calculation: M = F × d

    Hand calculation:
    - Force: F = 1000 lbs
    - Distance: d = 15 ft
    - Moment: M = 1000 × 15 = 15,000 lb-ft = 15.0 kip-ft

    Reference: Statics, moment equation
    """
    result = calculate_moment(force_lbs=1000, distance_ft=15)
    assert result == pytest.approx(15.0, abs=0.01)
```

### 2. Engineering Tolerances
Use appropriate tolerances based on engineering precision:

```python
# Stresses: ±0.01 ksi (0.1% typical)
assert stress_ksi == pytest.approx(33.0, abs=0.01)

# Forces: ±1 lb (or 0.1% for large forces)
assert force_lbs == pytest.approx(1000, rel=0.001)

# Deflections: ±0.01 in
assert deflection_in == pytest.approx(1.5, abs=0.01)

# Ratios: ±0.001 (0.1%)
assert ratio == pytest.approx(0.85, abs=0.001)
```

### 3. Code References
Always cite relevant code sections:

```python
def test_wind_pressure(self):
    """
    Test velocity pressure per ASCE 7-22.

    Reference: ASCE 7-22 Equation 26.10-1
    qz = 0.00256 × Kz × Kzt × Kd × Ke × V²
    """
```

### 4. Determinism Validation
Critical calculations must be deterministic:

```python
@pytest.mark.determinism
def test_calculation_is_deterministic(self):
    """Verify same inputs always produce same outputs."""
    results = [calculate_thing(x=10) for _ in range(10)]
    assert all(r == results[0] for r in results)
```

### 5. Edge Cases
Test boundary conditions and invalid inputs:

```python
def test_zero_wind_speed(self):
    """Test with zero wind speed (should not error)."""
    result = calculate_wind_force(wind_speed_mph=0)
    assert result.force_lbs == 0

def test_negative_area_raises_error(self):
    """Test that negative area raises ValueError."""
    with pytest.raises(ValueError, match="Area must be positive"):
        calculate_thing(area=-10)
```

## Continuous Integration

Tests run automatically on:
- ✅ Every commit (pre-commit hook)
- ✅ Pull requests (GitHub Actions)
- ✅ Nightly builds (full suite with slow tests)

### Pre-commit Checks
```bash
# Run before committing
pytest -m "unit and not slow" --cov --cov-fail-under=80
ruff check .
mypy src/
```

### CI Pipeline
```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pytest --cov --cov-fail-under=80 -m "not slow"
```

## Performance Benchmarks

### Database Query Performance
```python
@pytest.mark.benchmark
async def test_lookup_performance(aisc_connection):
    """Single lookup should complete in <10ms."""
    import time
    start = time.perf_counter()
    await aisc_connection.fetchrow("SELECT * FROM aisc_shapes_v16 WHERE ...")
    duration = time.perf_counter() - start
    assert duration < 0.010  # <10ms
```

### Calculation Performance
```python
@pytest.mark.benchmark
def test_solver_performance(benchmark):
    """Solver should complete in <100ms for typical case."""
    result = benchmark(lambda: analyze_single_pole_sign(config))
    assert benchmark.stats.stats.mean < 0.100  # <100ms mean
```

## Troubleshooting

### Database Connection Errors
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Verify test database exists
psql -U apex -d apex_test -c "SELECT 1"

# Create test database if missing
createdb -U apex apex_test
```

### Async Test Failures
```python
# Ensure proper async fixture usage
@pytest.mark.asyncio  # Required for async tests
async def test_async_function(db_session: AsyncSession):
    result = await db_session.execute(...)
```

### Coverage Not Including Module
```bash
# Verify source path in pyproject.toml
[tool.coverage.run]
source = ["src/apex"]  # Must match your source location
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Guide](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov Coverage Plugin](https://pytest-cov.readthedocs.io/)
- [ASCE 7-22 Wind Loads](https://www.asce.org/publications-and-news/asce-7)
- [AISC 360-22 Steel Construction](https://www.aisc.org/publications/steel-construction-manual-resources/)
- [IBC 2024](https://codes.iccsafe.org/content/IBC2024P1)

## Contributing

When adding new features:
1. ✅ Write tests FIRST (TDD approach)
2. ✅ Include hand calculations in docstrings
3. ✅ Add code references (IBC/ASCE/AISC sections)
4. ✅ Test edge cases and invalid inputs
5. ✅ Verify determinism for calculations
6. ✅ Run full test suite before PR: `pytest --cov --cov-fail-under=80`

## License

Copyright © 2024 SignX-Studio. All rights reserved.
