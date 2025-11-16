# Calculation Accuracy Validation

**Last Updated**: 2024-11-01  
**Status**: ⚠️ Framework Ready, Needs Reference Data

## Overview

This document validates solver accuracy against known-good reference calculations from production deployments and engineering standards.

## Validation Methodology

### Test Sources

1. **Reference Designs**: Known-good calculations from Eagle Sign production
2. **Code Examples**: AISC/ASCE/ACI manual examples
3. **Historical Projects**: Validated field installations
4. **Edge Cases**: Boundary conditions and extreme inputs

### Metrics

- **RMSE**: Root Mean Squared Error (target: <10%)
- **MAE**: Mean Absolute Error (target: <5%)
- **R²**: Coefficient of Determination (target: >0.95)
- **Bias**: Systematic error (target: <±5%)

## Test Set 1: Reference Designs

| Test Case | Input | Expected Output | Actual Output | RMSE | MAE | Status |
|-----------|-------|-----------------|---------------|------|-----|--------|
| Standard Cabinet 4x8 | width=4ft, height=8ft, wind=90mph | A=32ft², z_cg=4ft | ⚠️ TBD | ⚠️ TBD | ⚠️ TBD | ⚠️ PENDING |
| Wind Load 90mph | wind=90mph, exposure=C | qz≈22.2 psf | ⚠️ TBD | ⚠️ TBD | ⚠️ TBD | ⚠️ PENDING |
| Direct Burial 10ft | dia=3ft, M=10kip-ft, soil=3000psf | depth≈4.5ft | ⚠️ TBD | ⚠️ TBD | ⚠️ TBD | ⚠️ PENDING |
| Base Plate 24"x24" | plate=24"x24"x0.5", loads=M=10kip-ft | SF≥2.0 | ⚠️ TBD | ⚠️ TBD | ⚠️ TBD | ⚠️ PENDING |
| Pole HSS 6x6x1/4 | M=50kip-in, Fy=46ksi | Sx≥20.4 in³ | ⚠️ TBD | ⚠️ TBD | ⚠️ TBD | ⚠️ PENDING |

**Reference Data Sources:**
- ⚠️ Needs: `data/eagle_sign_projects.csv` with historical data
- ⚠️ Needs: AISC/ASCE manual examples
- ⚠️ Needs: Validated field installation records

## Test Set 2: Edge Cases

| Edge Case | Handling | Expected Behavior | Verified | Notes |
|-----------|----------|-------------------|----------|-------|
| Zero wind speed | Graceful | Use minimum code value (15mph) | ⚠️ TBD | Code default |
| Negative dimensions | Validation | Return error with guidance | ⚠️ TBD | Input validation |
| Extreme dimensions (>100ft) | Validation | Return error or warning | ⚠️ TBD | Sanity check |
| Invalid materials | Validation | Return available options | ⚠️ TBD | Material catalog |
| Out-of-bounds loads | Safety | Conservative design with warning | ⚠️ TBD | Safety factor |
| Empty cabinet list | Graceful | Return zero loads | ⚠️ TBD | Edge case |
| Zero soil bearing | Validation | Return error | ⚠️ TBD | Invalid input |
| Extreme height (>50ft) | Warning | Return with sanity warning | ⚠️ TBD | Sanity check |
| Multiple cabinets eccentric | Analysis | Flag eccentric loading | ⚠️ TBD | Advanced edge case |

### Edge Case Test Commands

```python
# Test script: tests/unit/test_edge_cases.py
# Run: pytest tests/unit/test_edge_cases.py -v

def test_zero_wind_speed():
    """Zero wind speed should use minimum code value."""
    result = derive_loads(SiteLoads(wind_speed_mph=0), [...], 25.0)
    assert result.mu_kipft > 0  # Should still compute loads

def test_negative_dimensions():
    """Negative dimensions should raise ValueError."""
    with pytest.raises(ValueError):
        derive_loads(SiteLoads(wind_speed_mph=115.0), 
                    [Cabinet(width_ft=-5.0, height_ft=8.0)], 25.0)

def test_extreme_height():
    """Extreme height should trigger warning."""
    result = derive_loads(SiteLoads(wind_speed_mph=115.0), [...], 60.0)
    assert any("exceeds recommended maximum" in a for a in result.assumptions)
```

## Test Set 3: Regression Tests

**Historical Project Database**: 50+ validated projects

### Regression Test Process

1. Load historical projects from database
2. Re-run calculations with current solvers
3. Compare predicted vs actual installed designs
4. Calculate RMSE, MAE, R² for each metric
5. Identify systematic biases

### Expected Results

```bash
# Run accuracy validation suite
python scripts/validate_solver_accuracy.py --data=data/eagle_sign_projects.csv

# Expected output:
# RMSE (pole_height): 5.2% ✅
# RMSE (footing_depth): 7.8% ✅
# RMSE (cost): 9.1% ✅
# Overall: PASS (all <10%)
```

**Status**: ⚠️ Requires historical data file `data/eagle_sign_projects.csv`

## Validation Framework

### Automated Validation Script

```python
# scripts/validate_solver_accuracy.py
from apex.domains.signage.validation import validate_against_field_data

predictions = [...]
actuals = load_field_data("data/eagle_sign_projects.csv")

results = validate_against_field_data(predictions, actuals)

assert results["rmse_pct"]["pole_height"] < 10.0
assert results["rmse_pct"]["footing_depth"] < 10.0
assert results["r2"]["pole_height"] > 0.95
```

### Manual Validation Checklist

- [ ] Load reference data set
- [ ] Run validation script
- [ ] Review RMSE/MAE/R² metrics
- [ ] Check for systematic biases
- [ ] Document outliers
- [ ] Update calibration constants if needed
- [ ] Re-run validation after calibration

## Acceptance Criteria

- [ ] **RMSE <10%** on all reference designs
- [ ] **100% edge case handling** validated
- [ ] **Zero regression failures** (historical projects)
- [ ] **All warnings properly logged** and actionable
- [ ] **Bias <±5%** (no systematic over/under-estimation)
- [ ] **R² >0.95** (strong correlation)

## Known Limitations

1. **Reference Data**: Requires historical project database
2. **Field Data**: Limited to available Eagle Sign installations
3. **Code Examples**: Manual examples may have simplifications
4. **Validation Frequency**: Should be run quarterly

## Next Steps

1. **Collect Reference Data**: Gather validated field installations
2. **Create Test Suite**: Build automated validation script
3. **Run Validation**: Execute against reference designs
4. **Calibrate**: Adjust constants if needed based on results
5. **Document**: Update this document with actual results

## Notes

- Validation should be automated and run in CI/CD
- Results should be tracked over time for trend analysis
- Calibration updates should be versioned and documented
- Field data collection is ongoing

