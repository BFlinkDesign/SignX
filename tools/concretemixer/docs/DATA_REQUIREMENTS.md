# Critical Data Requirements

## Overview

This document identifies the **KNOWN** specifications from public sources vs **UNKNOWN** specifications that require measurement, manufacturer contact, or destructive analysis for proper engineering replication.

---

## 1. KNOWN SPECIFICATIONS (High Confidence)

### 1.1 Overall Dimensions
| Parameter | Value | Source | Confidence |
|-----------|-------|--------|------------|
| Overall Length | 66.5 in (1689 mm) | MudMixer Specs | ★★★★★ |
| Overall Width | 27.5 in (699 mm) | MudMixer Specs | ★★★★★ |
| Overall Height | 35 in (889 mm) | MudMixer Specs | ★★★★★ |
| Chute Height | 16 in (406 mm) | MudMixer Specs | ★★★★★ |
| Dry Weight | 145 lbs (66 kg) | MudMixer Specs | ★★★★★ |

### 1.2 Capacity
| Parameter | Value | Source | Confidence |
|-----------|-------|--------|------------|
| Hopper Capacity | 120 lbs | MudMixer Specs | ★★★★★ |
| Extended Hopper | 300 lbs | MudMixer Specs | ★★★★★ |
| Throughput | 45+ bags/hr (80 lb) | MudMixer Specs | ★★★★★ |

### 1.3 Motor & Electrical
| Parameter | Value | Source | Confidence |
|-----------|-------|--------|------------|
| Motor Power | 0.5 HP (373 W) | MudMixer Specs | ★★★★★ |
| Motor Type | DC (water-sealed) | Patent 10,259,140 | ★★★★☆ |
| Input Voltage | 120V AC | MudMixer Specs | ★★★★★ |
| Current Draw | 2.6 A | MudMixer Specs | ★★★★★ |
| Power Supply | AC-DC Transformer | Patent 10,259,140 | ★★★★☆ |

### 1.4 Motor Shaft Interface ⚠️ CRITICAL FINDING
| Parameter | Value | Source | Confidence |
|-----------|-------|--------|------------|
| **Coupling Type** | **Left-Hand Acme Thread** | Patent 10,259,140 | ★★★★☆ |
| Thread Direction | Left-Hand (LH) | Patent 10,259,140 | ★★★★☆ |
| Thread Form | Acme (trapezoidal) | Patent 10,259,140 | ★★★★☆ |

**Note**: Left-hand thread prevents auger from unscrewing during forward rotation.

### 1.5 Auger Design
| Parameter | Value | Source | Confidence |
|-----------|-------|--------|------------|
| Type | Shaftless Helical | Patent 10,259,140 | ★★★★★ |
| P/D Ratio (Hopper) | 0.2 - 0.9 | Patent 10,259,140 | ★★★★☆ |
| P/D Ratio (Preferred) | 0.5 - 0.8 | Patent 11,285,639 | ★★★★☆ |
| P/D Ratio (Chute) | 0.6 - 1.0 | Patent 11,285,639 | ★★★★☆ |
| Variable Pitch | Yes (increasing) | Patent 10,259,140 | ★★★★★ |
| Fingers | Inward-extending | Patent 10,259,140 | ★★★★★ |

### 1.6 Chute Specifications
| Parameter | Value | Source | Confidence |
|-----------|-------|--------|------------|
| Length Range | 16-30 in | Patent 10,259,140 | ★★★★☆ |
| Angle Range | -5° to +30° | Patent 10,259,140 | ★★★★☆ |
| Tilt Positions | 15°, 25°, 35° | MudMixer Specs | ★★★★★ |
| Swivel Range | 330° | MudMixer Specs | ★★★★★ |
| Extension Available | +18 in | MudMixer Accessories | ★★★★★ |

### 1.7 Aggregate Limitation ⚠️ CRITICAL CONSTRAINT
| Parameter | Value | Source | Confidence |
|-----------|-------|--------|------------|
| **Max Aggregate Size** | **1/2 inch (12.7 mm)** | MudMixer Specs | ★★★★★ |

### 1.8 Construction Materials
| Parameter | Value | Source | Confidence |
|-----------|-------|--------|------------|
| Body/Hopper | 14 ga steel | MudMixer Specs | ★★★★★ |
| Frame Tubing | 1 in steel pipe | MudMixer Specs | ★★★★★ |
| Tires | Flat-free (Marathon) | MudMixer Specs | ★★★★★ |

### 1.9 Water System
| Parameter | Value | Source | Confidence |
|-----------|-------|--------|------------|
| Min Pressure | 30 PSI | MudMixer Specs | ★★★★★ |
| Nozzle Count | 2 (dual) | MudMixer Specs | ★★★★★ |
| Flow Control | Adjustable dial | MudMixer Specs | ★★★★★ |

---

## 2. UNKNOWN SPECIFICATIONS (Critical Gaps)

### 2.1 Auger Housing Interface ⛔ BLOCKING
| Parameter | Needed For | Impact Level |
|-----------|------------|--------------|
| **Housing Internal Diameter (ID)** | Clearance calculation, CFD | ⛔ CRITICAL |
| **Auger Outer Diameter (OD)** | Clearance calculation | ⛔ CRITICAL |
| **Clearance Gap** | Flow analysis, aggregate jamming | ⛔ CRITICAL |

**Why Critical**:
- Gap too small (<2mm): Friction, heat buildup, finger wear
- Gap too large (>6mm): Loss of shear efficiency, aggregate bypass
- Required for CFD simulation of concrete flow

**Estimation Method**:
```
Based on 1/2" max aggregate:
  Minimum clearance = 0.5" × 1.2 = 0.6" (15mm) safety factor

If chute is 4" ID tube (common steel pipe):
  Auger OD ≈ 5.0" - 3.25"
  Clearance ≈ 0.375" - 0.5" per side
```

### 2.2 Motor Shaft Specifications ⛔ BLOCKING
| Parameter | Needed For | Impact Level |
|-----------|------------|--------------|
| **Acme Thread Size** | Coupling adapter design | ⛔ CRITICAL |
| **Thread Pitch** | Engagement length calculation | ⛔ CRITICAL |
| **Shaft Diameter** | Motor replacement compatibility | ⚠️ HIGH |

**Common Acme Thread Sizes (likely candidates)**:
| Size | Major Dia | Pitch | TPI |
|------|-----------|-------|-----|
| 1/2"-10 LH | 0.500" | 0.100" | 10 |
| 5/8"-8 LH | 0.625" | 0.125" | 8 |
| 3/4"-6 LH | 0.750" | 0.167" | 6 |

### 2.3 Bearing Specifications ⛔ BLOCKING
| Parameter | Needed For | Impact Level |
|-----------|------------|--------------|
| **Bearing Type** | Load path analysis | ⛔ CRITICAL |
| **Bearing ID** | Shaft sizing | ⛔ CRITICAL |
| **Bearing OD** | Housing design | ⛔ CRITICAL |
| **Load Rating** | FEA validation | ⚠️ HIGH |

**Likely Configuration**:
- Sealed ball bearing at motor end
- Thrust bearing or bushing at discharge end
- May use UHMW or bronze bushings for simplicity

### 2.4 Water Nozzle Thread ⚠️ HIGH
| Parameter | Needed For | Impact Level |
|-----------|------------|--------------|
| **Thread Size** | Manifold CAD design | ⚠️ HIGH |
| **Thread Type** | NPT vs BSP vs Metric | ⚠️ HIGH |

**Likely Candidates**:
| Standard | Common Sizes |
|----------|--------------|
| NPT | 1/8" NPT, 1/4" NPT |
| Metric | M6×1.0, M8×1.25 |
| Push-fit | 1/4" OD tubing |

### 2.5 Finger Specifications ⚠️ HIGH
| Parameter | Needed For | Impact Level |
|-----------|------------|--------------|
| **Finger Material** | Wear life calculation | ⚠️ HIGH |
| **Finger Diameter** | Shear force calculation | ⚠️ HIGH |
| **Finger Length** | Mixing efficiency | ⚠️ MEDIUM |
| **Finger Count** | Torque distribution | ⚠️ MEDIUM |
| **Finger Angle** | Flow dynamics | ⚠️ MEDIUM |

**Material Options**:
| Material | Pros | Cons |
|----------|------|------|
| Steel (welded) | Strength, durability | Weight, corrosion |
| UHMW-PE | Low friction, replaceable | Lower shear strength |
| Stainless Steel | Corrosion resistant | Cost |

---

## 3. OPERATIONAL CONSTRAINTS (For Generative Design)

### 3.1 Duty Cycle ❓ UNKNOWN
| Mode | Thermal Impact | Material Selection |
|------|----------------|-------------------|
| Intermittent (5-10 bags) | Low heat buildup | Standard UHMW OK |
| Continuous (50+ bags) | High friction heat | High-temp UHMW or PTFE |

**Assumed**: Intermittent use (consumer/contractor tool)
**If continuous**: Requires thermal analysis, may need cooling

### 3.2 Aggregate Shear Requirements
```
Given:
  Max aggregate = 0.5" (12.7mm)
  Motor power = 0.5 HP = 373 W
  Estimated RPM = 25-30

Calculate:
  Torque = Power / (2π × RPM/60)
  Torque = 373 / (2π × 27.5/60)
  Torque ≈ 129 N·m (95 ft-lb)

Shear force at finger tip (assuming 2.5" radius):
  F = T / r = 129 / 0.0635
  F ≈ 2032 N (457 lbf)
```

### 3.3 Concrete Flow Properties (for CFD)
| Property | Value | Notes |
|----------|-------|-------|
| Density (wet) | 2400 kg/m³ (150 lb/ft³) | Fresh concrete |
| Viscosity Model | Bingham Plastic | Yield stress + plastic viscosity |
| Yield Stress | 100-500 Pa | Depends on slump |
| Plastic Viscosity | 10-50 Pa·s | Depends on w/c ratio |

---

## 4. DATA ACQUISITION METHODS

### 4.1 Non-Destructive
| Method | Data Obtained | Accuracy |
|--------|---------------|----------|
| External measurement | Overall dimensions | ±1mm |
| Bore gauge through chute | Housing ID | ±0.1mm |
| Endoscope inspection | Auger geometry | Visual only |
| Thread gauge on coupling | Thread identification | Exact |

### 4.2 Destructive / Disassembly
| Method | Data Obtained | Risk |
|--------|---------------|------|
| Remove auger | Auger OD, finger dimensions | Reassembly required |
| Remove motor | Shaft specifications | Motor may need recalibration |
| Section chute | Wall thickness, weld details | Destroys unit |

### 4.3 Manufacturer Contact
```
MudMixer Support: (806) 515-4683
Email: support@mudmixer.com
Website: mudmixer.com/pages/support

Request:
- Parts diagram with dimensions
- Replacement auger specifications
- Motor specifications sheet
```

---

## 5. MINIMUM VIABLE DATA SET

To proceed with computational design, the following **minimum data** is required:

| Priority | Parameter | Acquisition Method |
|----------|-----------|-------------------|
| 1 | Housing ID | Measure with bore gauge |
| 2 | Auger OD | Measure or infer from housing |
| 3 | Acme thread size | Thread gauge or measure pitch |
| 4 | Finger material | Visual/hardness test |
| 5 | Motor nameplate data | Read label or contact MFG |

---

## 6. ASSUMPTIONS FOR PROCEEDING

Until actual measurements are obtained, use these **conservative assumptions**:

```python
ASSUMPTIONS = {
    # Geometry
    "housing_id": 4.0,          # inches (standard 6" steel pipe)
    "auger_od": 3.25,            # inches (0.25" clearance per side)
    "clearance_gap": 0.25,      # inches per side

    # Motor
    "acme_thread": "5/8-8 LH",  # Common size for this torque class
    "motor_torque": 95,         # ft-lb (calculated from 0.5HP @ 27 RPM)
    "motor_rpm": 27,            # estimated output

    # Materials
    "finger_material": "steel", # Conservative assumption
    "finger_diameter": 0.375,   # inches (3/8")
    "finger_length": 2.0,       # inches
    "finger_count": 8,          # per full auger length

    # Constraints
    "max_aggregate": 0.5,       # inches (CONFIRMED)
    "duty_cycle": "intermittent",
    "safety_factor": 2.5,
}
```

---

## Sources

- [MudMixer Specifications](https://mudmixer.com/pages/specs)
- [US Patent 10,259,140](https://patents.justia.com/patent/10259140)
- [MudMixer Support](https://mudmixer.com/pages/support)
- [Home Depot Product Page](https://www.homedepot.com/p/MUDMIXER-Continuous-Feed-Portable-Electric-Concrete-Cement-and-Mortar-Mixer-MMXR-3221/330432979)
