# APEX Signage Engineering Solvers - Calibration

## Overview

Calibration constants are versioned engineering parameters that are tuned based on field performance data.

## Calibration Constants

### Footing Calibration Constant (K)

**Parameter**: `footing_calibration_k`  
**Default**: 1.0  
**Range**: 0.5 - 2.0  
**Purpose**: Adjusts footing depth calculation to match field performance

**Equation:**
```
depth_ft = K × Mu / (d³ × q_soil / 12.0)
```

**Tuning:**
- If field depths consistently deeper than predicted: K < 1.0
- If field depths consistently shallower: K > 1.0
- Auto-tuning minimizes RMSE while maintaining safety

### Soil Bearing Multiplier

**Parameter**: `soil_bearing_multiplier`  
**Default**: 1.0  
**Range**: 0.8 - 1.5  
**Purpose**: Adjusts soil bearing capacity for local conditions

**Tuning:**
- Conservative soils: multiplier < 1.0
- Aggressive soils: multiplier > 1.0 (with caution)
- Auto-tuning based on field performance

### Safety Factor Base

**Parameter**: `safety_factor_base`  
**Default**: 2.0  
**Range**: 1.5 - 3.0 (minimum 1.5 for safety)  
**Purpose**: Base safety factor for all checks

**Tuning:**
- Never reduce below 1.5
- Increase for critical applications
- Auto-tuning maintains minimum 1.5

### Wind Load Factor

**Parameter**: `wind_load_factor`  
**Default**: 1.6 (ASCE 7-22 LRFD)  
**Range**: 1.4 - 1.8  
**Purpose**: LRFD load factor for wind

**Note**: Generally not tuned (code requirement)

## Auto-Tuning Process

### 1. Collect Field Data

```csv
project_id,cabinet_area_ft2,height_ft,wind_speed_mph,actual_depth_ft,predicted_depth_ft,soil_psf
proj1,112.0,25.0,115.0,4.2,3.8,3000.0
proj2,150.0,30.0,120.0,5.1,4.5,3000.0
...
```

### 2. Run Validation

```python
from apex.domains.signage.validation import validate_against_field_data

results = validate_against_field_data(predictions, field_data_path)
print(results["rmse_pct"])  # Target: <10%
print(results["biases"])    # Identify systematic errors
```

### 3. Auto-Tune Parameters

```python
from apex.domains.signage.validation import auto_tune_parameters

tuned_params = auto_tune_parameters(
    Path("data/eagle_sign_projects.csv"),
    objective="minimize_error_with_safety",
)

print(tuned_params)
# {
#   "footing_calibration_k": 1.05,
#   "soil_bearing_multiplier": 0.95,
#   ...
# }
```

### 4. Validate Safety

```python
from apex.domains.signage.validation import SolverParameterTuner

tuner = SolverParameterTuner()
if not tuner.validate_safety(tuned_params):
    raise ValueError("Tuned parameters violate safety constraints")
```

### 5. Update Database

```sql
-- Insert new version
INSERT INTO calibration_constants (name, version, value, effective_from)
VALUES ('footing_calibration_k', 'v2', 1.05, NOW());

-- Activate new version
UPDATE calibration_constants
SET effective_to = NOW()
WHERE name = 'footing_calibration_k' AND version = 'v1';
```

## Calibration Report

Generate PDF calibration report:

```python
from apex.domains.signage.validation import generate_validation_report

report_path = generate_validation_report(
    validation_results,
    Path("calibration_report.pdf"),
    field_data=field_data,
)
```

Report includes:
- Scatter plots: Predicted vs Actual
- Statistical summary: RMSE, R², MAE, bias
- Recommendations for parameter adjustments
- Safety validation results

## Versioning

Calibration constants are versioned:

- **Version naming**: v1, v2, v3...
- **Effective dates**: Track when each version was active
- **Rollback**: Can revert to previous version if needed

## Best Practices

1. **Collect sufficient data**: Minimum 20-30 field projects
2. **Validate safety**: Never reduce safety factors below minimums
3. **Document changes**: Record tuning rationale in CALIBRATION.md
4. **Test before deploy**: Validate tuned parameters on test set
5. **Monitor performance**: Track prediction accuracy over time

