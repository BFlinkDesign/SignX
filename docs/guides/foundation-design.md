# Foundation Design Guide

Complete guide to foundation design: direct burial and baseplate options.

## Foundation Types

CalcuSign supports two foundation types:

1. **Direct Burial** - Cylindrical footing buried in soil
2. **Baseplate** - Anchor bolt foundation with steel baseplate

## Direct Burial Foundation

### Overview

Direct burial foundations are cylindrical concrete footings buried directly in soil. The system calculates:
- Required depth based on diameter and loads
- Concrete yardage for ordering
- Monotonic validation (diameter↓ ⇒ depth↑)

### Solve Footing Depth

Calculate required depth for given diameter:

```bash
curl -X POST http://localhost:8000/signage/direct_burial/footing/solve \
  -H "Content-Type: application/json" \
  -d '{
    "footing": {
      "diameter_ft": 3.0,
      "shape": "cylindrical"
    },
    "soil_psf": 3000.0,
    "num_poles": 1,
    "M_pole_kipft": 10.0
  }'
```

**Response:**
```json
{
  "result": {
    "min_depth_ft": 4.2,
    "min_depth_in": 50.4,
    "diameter_ft": 3.0,
    "concrete_yards": 1.47,
    "monotonic": true
  },
  "assumptions": ["soil_bearing=3000psf, K=calib_v1"],
  "confidence": 0.94
}
```

### Parameters

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| `footing.diameter_ft` | float | Footing diameter in feet | Yes |
| `footing.shape` | string | Shape type (`cylindrical`) | Yes |
| `soil_psf` | float | Soil bearing capacity (psf) | Yes |
| `num_poles` | int | Number of poles supported | Yes |
| `M_pole_kipft` | float | Moment per pole (kip-ft) | Yes |

### Multi-Pole Support

For multi-pole installations:

```bash
{
  "num_poles": 2,
  "M_pole_kipft": 10.0  # Moment split between poles
}
```

System automatically splits moment: `M_per_pole = M_total / num_poles`

### Monotonic Validation

The solver ensures monotonicity:
- **Decreasing diameter** → **Increasing depth**
- Verified for all diameter values
- Guarantees consistent behavior

### Complete Foundation Design

Get full design with safety factors:

```bash
curl -X POST http://localhost:8000/signage/direct_burial/footing/design \
  -H "Content-Type: application/json" \
  -d '{
    "loads": {
      "F_lbf": 5000.0,
      "M_inlb": 120000.0
    },
    "constraints": {
      "max_foundation_dia_in": 48,
      "max_embed_in": 60
    }
  }'
```

**Response includes:**
- Foundation dimensions
- Safety factors (OT, BRG, SLIDE, UPLIFT)
- Deflection check
- Concrete requirements

### Engineering Assist Mode

Get recommendations for spread footing:

```bash
curl -X POST http://localhost:8000/signage/direct_burial/footing/assist \
  -H "Content-Type: application/json" \
  -d '{
    "loads": {...},
    "soil_psf": 3000.0
  }'
```

## Baseplate Foundation

### Overview

Baseplate foundations use anchor bolts embedded in concrete with a steel baseplate. The system validates:
- Plate thickness (flexural capacity)
- Weld strength (fillet welds)
- Anchor tension capacity (ACI breakout)
- Anchor shear capacity

### Validate Baseplate

Check complete baseplate design:

```bash
curl -X POST http://localhost:8000/signage/baseplate/checks \
  -H "Content-Type: application/json" \
  -d '{
    "plate": {
      "w_in": 12.0,
      "l_in": 12.0,
      "t_in": 0.75,
      "fy_ksi": 36.0,
      "e_in": 3.0
    },
    "weld": {
      "size_in": 0.25,
      "strength": 70.0,
      "length_in": 12.0
    },
    "anchors": {
      "num_anchors": 4,
      "dia_in": 0.75,
      "embed_in": 10.0,
      "fy_ksi": 58.0,
      "fc_psi": 4000.0,
      "spacing_in": 6.0
    },
    "loads": {
      "T_kip": 5.0,
      "V_kip": 2.0,
      "M_kipin": 100.0
    }
  }'
```

**Response:**
```json
{
  "result": {
    "all_pass": true,
    "approved": true,
    "checks": [
      {
        "check": "plate_thickness",
        "pass": true,
        "demand": 0.52,
        "capacity": 0.75,
        "util": 0.69
      },
      {
        "check": "weld_strength",
        "pass": true,
        "demand": 0.45,
        "capacity": 0.70,
        "util": 0.64
      },
      {
        "check": "anchor_tension",
        "pass": true,
        "demand": 1250.0,
        "capacity": 3500.0,
        "util": 0.36
      },
      {
        "check": "anchor_shear",
        "pass": true,
        "demand": 500.0,
        "capacity": 2000.0,
        "util": 0.25
      }
    ]
  }
}
```

### Check Requirements

All checks must pass for approval:
- ✅ **Plate Thickness** - Flexural capacity sufficient
- ✅ **Weld Strength** - Fillet weld capacity adequate
- ✅ **Anchor Tension** - ACI breakout capacity
- ✅ **Anchor Shear** - Shear capacity

**If any check fails**, `approved: false` and system indicates which checks failed.

### Auto-Design Baseplate

Generate baseplate design from loads:

```bash
curl -X POST http://localhost:8000/signage/baseplate/design \
  -H "Content-Type: application/json" \
  -d '{
    "loads": {
      "F_lbf": 5000.0,
      "M_inlb": 120000.0
    }
  }'
```

**Response includes:**
- Plate dimensions (width, length, thickness)
- Anchor schedule (quantity, diameter, spacing)
- Weld specifications
- Embedment depth

### Request Engineering Review

Flag design for human review:

```bash
curl -X POST http://localhost:8000/signage/baseplate/request-engineering \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_abc123",
    "reason": "High utilization ratios",
    "notes": "Anchor tension at 85% capacity"
  }'
```

## Concrete Yardage Calculator

Standalone utility for concrete calculations:

```bash
curl -X POST http://localhost:8000/signage/common/concrete/yards \
  -H "Content-Type: application/json" \
  -d '{
    "diameter_ft": 3.0,
    "depth_ft": 4.2
  }'
```

**Formula:** `V = π × (d/2)² × h / 27` (cubic yards)

**Response:**
```json
{
  "result": {
    "concrete_yards": 1.47,
    "volume_cf": 39.79,
    "diameter_ft": 3.0,
    "depth_ft": 4.2
  }
}
```

## Design Process

### Direct Burial Workflow

1. **Estimate Loads**
   - Calculate wind loads from site resolution
   - Determine moment at base
   - Account for multiple poles if applicable

2. **Select Diameter**
   - Consider excavation constraints
   - Typical: 3-4 ft diameter

3. **Solve for Depth**
   - Use `/footing/solve` endpoint
   - Verify monotonic behavior
   - Check concrete yardage

4. **Validate Design**
   - Use `/footing/design` for safety factors
   - Ensure all safety factors > 1.0
   - Verify deflection limits

### Baseplate Workflow

1. **Estimate Loads**
   - Tension (uplift)
   - Shear (lateral)
   - Moment (overturning)

2. **Design Baseplate**
   - Use `/baseplate/design` for auto-design
   - Or manually specify dimensions

3. **Validate All Checks**
   - Use `/baseplate/checks` endpoint
   - All checks must pass
   - Review utilization ratios

4. **Request Review (if needed)**
   - Flag high utilization
   - Add engineering notes

## Best Practices

### Direct Burial

1. **Soil Bearing Capacity**
   - Conservative values recommended
   - Typical: 2000-4000 psf
   - Verify with geotechnical report

2. **Diameter Selection**
   - Smaller diameter = deeper footing
   - Consider excavation costs
   - Minimum: 2.5 ft practical

3. **Monotonic Validation**
   - System ensures consistency
   - Verify depth increases as diameter decreases

### Baseplate

1. **Anchor Spacing**
   - Minimum edge distance per ACI
   - Typical: 3-6 inches from edge
   - Verify spacing limits

2. **Utilization Ratios**
   - Keep below 80% for safety margin
   - Request review if >85%
   - Consider redundancy

3. **Material Specifications**
   - Plate: A36 or A992 steel
   - Anchors: Grade 5 or Grade 8
   - Concrete: Minimum 3000 psi

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Invalid diameter | diameter_ft ≤ 0 | Use positive value |
| Invalid soil bearing | soil_psf ≤ 0 | Check soil parameters |
| Check failure | One check fails | Review design, all must pass |

### Example Error Response

```json
{
  "result": {
    "all_pass": false,
    "approved": false,
    "checks": [
      {
        "check": "plate_thickness",
        "pass": false,
        "demand": 0.85,
        "capacity": 0.75,
        "util": 1.13,
        "message": "Plate thickness insufficient"
      }
    ]
  },
  "confidence": 0.4
}
```

## Next Steps

- [**Sign Design Workflow**](sign-design-workflow.md) - Complete workflow
- [**API Reference**](../reference/api-endpoints.md) - Endpoint details
- [**Project Management**](project-management.md) - Save designs

