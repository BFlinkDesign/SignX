# AISC Database Service - Migration Guide

**Purpose:** Replace hardcoded section properties with database lookups
**Service:** `ConcreteRebarService`, `get_section_properties_async()`
**Priority:** M3 - Medium (Code Quality)
**Date:** 2025-11-02

---

## Overview

This guide shows how to migrate from hardcoded AISC section properties to the new database-backed service across all solver modules.

**Files Requiring Migration:**
1. `cantilever_solver.py` - Lines 227-228
2. `single_pole_solver.py` - Any hardcoded fallbacks
3. `double_pole_solver.py` - Any hardcoded fallbacks
4. `monument_solver.py` - Any hardcoded properties

---

## Migration Pattern

### Before (Hardcoded)

```python
# cantilever_solver.py:227-228
# Using approximate I for HSS8x8x1/2: I ≈ 100 in⁴
I_arm_in4 = 100.0  # Would look up from database
S_arm_in3 = 25.0   # Section modulus
```

### After (Database Service)

```python
from apex.domains.signage.services import (
    get_section_properties_async,
    AISCDatabaseError,
)
from apex.api.deps import get_db

async def analyze_cantilever_sign_async(
    config: CantileverConfig,
    loads: CantileverLoads,
    db: AsyncSession = Depends(get_db),
) -> CantileverAnalysisResult:
    """
    Analyze cantilever sign with database-backed section properties.

    Args:
        config: Cantilever configuration
        loads: Applied loads
        db: Database session for AISC lookup

    Returns:
        CantileverAnalysisResult with deterministic outputs

    Raises:
        AISCDatabaseError: If arm_section not found in database
    """
    # Fetch section properties from database
    try:
        section = await get_section_properties_async(
            designation=config.arm_section,  # e.g., "HSS8X8X1/2"
            steel_grade="A500B",             # Or from config
            db=db,
        )
    except AISCDatabaseError as e:
        raise ValueError(
            f"Invalid cantilever arm section: {config.arm_section}. "
            f"Section not found in AISC database. {e}"
        )

    # Use validated properties from database
    I_arm_in4 = section.ix_in4
    S_arm_in3 = section.sx_in3

    # Existing calculation code continues...
    arm_moment_inlb = (wind_force_lb * arm_length_in) + (total_weight_lb * arm_length_in / 2)
    arm_bending_stress_psi = arm_moment_inlb / S_arm_in3
    arm_deflection_in = (wind_force_lb * arm_length_in**3) / (3 * E_STEEL_KSI * 1000 * I_arm_in4)

    # ... rest of analysis
```

---

## Detailed Example: Cantilever Solver Migration

### Step 1: Add Database Dependency

```python
# cantilever_solver.py (top of file)
from __future__ import annotations

from apex.domains.signage.services import (
    get_section_properties_async,
    AISCDatabaseError,
)
from sqlalchemy.ext.asyncio import AsyncSession
```

### Step 2: Update Function Signature

```python
# OLD (synchronous)
def analyze_cantilever_sign(
    config: CantileverConfig,
    loads: CantileverLoads,
    wind_cycles_per_year: int = 100000,
    design_life_years: int = 50,
    include_fatigue: bool = False,
) -> CantileverAnalysisResult:

# NEW (async with database)
async def analyze_cantilever_sign(
    config: CantileverConfig,
    loads: CantileverLoads,
    db: AsyncSession,  # Add database session
    wind_cycles_per_year: int = 100000,
    design_life_years: int = 50,
    include_fatigue: bool = False,
) -> CantileverAnalysisResult:
```

### Step 3: Replace Hardcoded Properties

```python
# OLD (lines 221-228)
# Arm analysis (simplified - would need section properties from database)
# Assume HSS section for now
arm_length_in = config.arm_length_ft * 12.0

# Cantilever deflection: δ = PL³/(3EI)
# Using approximate I for HSS8x8x1/2: I ≈ 100 in⁴
I_arm_in4 = 100.0  # Would look up from database
S_arm_in3 = 25.0   # Section modulus

# NEW (database lookup)
# Fetch cantilever arm section properties
arm_length_in = config.arm_length_ft * 12.0

try:
    arm_section = await get_section_properties_async(
        designation=config.arm_section,
        steel_grade="A500B",  # Default for HSS
        db=db,
    )
except AISCDatabaseError as e:
    raise ValueError(
        f"Cantilever arm section '{config.arm_section}' not found in AISC database. "
        f"Verify designation format (e.g., 'HSS8X8X1/2'). Error: {e}"
    )

# Use database properties
I_arm_in4 = arm_section.ix_in4
S_arm_in3 = arm_section.sx_in3
fy_arm_ksi = arm_section.fy_ksi  # Now variable based on grade
```

### Step 4: Update Stress Ratio Calculations

```python
# OLD (hardcoded Fy)
arm_stress_ratio = (arm_bending_stress_psi / 1000.0) / (PHI_BENDING * FY_STEEL_KSI)

# NEW (database Fy)
arm_stress_ratio = (arm_bending_stress_psi / 1000.0) / (PHI_BENDING * arm_section.fy_ksi)
```

### Step 5: Update API Routes

```python
# services/api/src/apex/api/routes/signcalc.py

from apex.api.deps import get_db

@router.post("/cantilever/analyze")
async def analyze_cantilever_sign_endpoint(
    config: CantileverConfig,
    loads: CantileverLoads,
    db: AsyncSession = Depends(get_db),  # Inject database
) -> dict:
    """
    Analyze cantilever sign structure.

    Now uses database-backed AISC section properties instead of hardcoded values.
    """
    result = await analyze_cantilever_sign(
        config=config,
        loads=loads,
        db=db,  # Pass database session
    )

    return {
        "ok": True,
        "result": result.dict(),
    }
```

---

## Migration Checklist

### For Each Solver File

- [ ] **Import Database Service**
  ```python
  from apex.domains.signage.services import get_section_properties_async, AISCDatabaseError
  from sqlalchemy.ext.asyncio import AsyncSession
  ```

- [ ] **Add Database Parameter**
  ```python
  async def solver_function(..., db: AsyncSession):
  ```

- [ ] **Replace Hardcoded Properties**
  ```python
  section = await get_section_properties_async(designation, steel_grade, db)
  sx_in3 = section.sx_in3  # Instead of: sx_in3 = 25.0
  ```

- [ ] **Add Error Handling**
  ```python
  try:
      section = await get_section_properties_async(...)
  except AISCDatabaseError as e:
      raise ValueError(f"Invalid section: {designation}. {e}")
  ```

- [ ] **Update Tests**
  - Add database fixture
  - Mock AISC database calls
  - Test invalid section handling

---

## Testing Pattern

### Test with Database Fixture

```python
# tests/unit/services/test_cantilever_solver.py

import pytest
from apex.domains.signage.services import get_section_properties_async
from apex.domains.signage.cantilever_solver import analyze_cantilever_sign

@pytest.mark.asyncio
async def test_cantilever_analysis_with_database(async_db_session):
    """Test cantilever analysis uses database section properties."""
    config = CantileverConfig(
        type=CantileverType.SINGLE,
        arm_length_ft=10.0,
        arm_angle_deg=0.0,
        arm_section="HSS8X8X1/2",
        connection_type=ConnectionType.BOLTED_FLANGE,
    )

    loads = CantileverLoads(
        sign_weight_lb=500.0,
        sign_area_ft2=48.0,
        wind_pressure_psf=25.0,
    )

    # Execute analysis (will fetch from database)
    result = await analyze_cantilever_sign(config, loads, db=async_db_session)

    # Verify results use real section properties
    assert result.arm_bending_stress_ksi > 0
    assert result.arm_deflection_in > 0

    # Verify section properties were fetched (not hardcoded)
    section = await get_section_properties_async("HSS8X8X1/2", "A500B", async_db_session)
    assert section.sx_in3 > 0  # Real value, not 25.0 hardcoded
```

### Mock Database for Unit Tests

```python
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_cantilever_with_mock_database():
    """Test cantilever with mocked database."""
    # Create mock database session
    mock_db = AsyncMock()

    # Mock section properties
    mock_section = MagicMock()
    mock_section.designation = "HSS8X8X1/2"
    mock_section.ix_in4 = 100.0
    mock_section.sx_in3 = 25.0
    mock_section.fy_ksi = 46.0

    # Patch the database service
    with patch('apex.domains.signage.services.get_section_properties_async') as mock_get:
        mock_get.return_value = mock_section

        config = CantileverConfig(
            type=CantileverType.SINGLE,
            arm_length_ft=10.0,
            arm_angle_deg=0.0,
            arm_section="HSS8X8X1/2",
            connection_type=ConnectionType.BOLTED_FLANGE,
        )

        loads = CantileverLoads(
            sign_weight_lb=500.0,
            sign_area_ft2=48.0,
            wind_pressure_psf=25.0,
        )

        result = await analyze_cantilever_sign(config, loads, db=mock_db)

        # Verify mock was called
        mock_get.assert_called_once_with("HSS8X8X1/2", "A500B", mock_db)
```

---

## Benefits of Migration

### Before (Hardcoded)
- ❌ Hardcoded section properties (I = 100 in⁴, S = 25 in³)
- ❌ No validation that section exists
- ❌ Limited to specific section sizes
- ❌ Cannot handle different steel grades
- ❌ Inaccurate for non-HSS8X8X1/2 sections

### After (Database Service)
- ✅ Real AISC properties from Shapes Database v16.0
- ✅ Validation that section designation exists
- ✅ Supports all HSS, Pipe, W-shapes from database
- ✅ Steel grade-specific yield strengths
- ✅ Accurate for all cantilever configurations
- ✅ Type-safe with Pydantic validation
- ✅ Proper error messages for missing sections

---

## Rollout Plan

### Phase 1: Cantilever Solver (This Document)
- [ ] Update `cantilever_solver.py` lines 227-228
- [ ] Add database parameter to `analyze_cantilever_sign()`
- [ ] Update API endpoint with database injection
- [ ] Add tests with database fixture

### Phase 2: Other Solvers
- [ ] Review `single_pole_solver.py` for hardcoded fallbacks
- [ ] Review `double_pole_solver.py` for hardcoded fallbacks
- [ ] Review `monument_solver.py` for hardcoded properties

### Phase 3: Validation
- [ ] Run full test suite
- [ ] Verify all calculations unchanged (determinism)
- [ ] PE review and approval

---

## Troubleshooting

### Issue: "Section not found in database"

**Cause:** Invalid AISC designation or section not in database

**Solution:**
1. Verify designation format: "HSS8X8X1/2" (not "8x8x1/2")
2. Check AISC database seeded: `python scripts/seed_aisc_sections.py`
3. Verify section exists in AISC Shapes Database v16.0
4. Use alternative section from database

### Issue: "Database session not provided"

**Cause:** Forgot to add `db` parameter to async function

**Solution:**
```python
# Add database parameter
async def my_function(..., db: AsyncSession):
    section = await get_section_properties_async(..., db=db)
```

### Issue: "Cannot await sync function"

**Cause:** Calling async service from sync function

**Solution:**
- Either make function async: `async def my_function(...)`
- Or use sync wrapper (deprecated): `get_section_properties_sync()`

---

## Summary

**M3 Resolution:** Complete migration pattern documented

**Files to Modify:**
1. `cantilever_solver.py` - Replace lines 227-228
2. Update API routes to inject database
3. Add comprehensive tests

**Next Steps:**
1. Implement pattern in cantilever_solver.py
2. Test with real AISC database
3. Verify determinism (results unchanged)
4. Roll out to remaining solvers

**Status:** Pattern ready for implementation

---

**Document Created:** 2025-11-02
**Last Updated:** 2025-11-02
**Related:** PHASE_2_COMPLETE.md, CODE_REVIEW_RESOLUTIONS.md
