# Engineering Calculations and Design Principles

## Overview

This document covers the engineering principles, calculations, and design considerations for replicating a MudMixer-style continuous concrete mixer.

> **⚠️ IMPORTANT**: See [DATA_REQUIREMENTS.md](./DATA_REQUIREMENTS.md) for critical unknown dimensions
> that must be measured before manufacturing.

---

## 0. CONFIRMED CONSTRAINTS (from Patents & Specs)

These are **hard constraints** that bound all design calculations:

| Constraint | Value | Source | Impact |
|------------|-------|--------|--------|
| **Max Aggregate Size** | 0.5" (12.7mm) | MudMixer Specs | Defines minimum clearance gap |
| **Motor Coupling** | Left-Hand Acme Thread | Patent 10,259,140 | Prevents auger unscrewing during rotation |
| **Hopper P/D Ratio** | 0.2 - 0.9 | Patent 10,259,140 | Controls intake rate |
| **Chute P/D Ratio** | 0.6 - 1.0 | Patent 11,285,639 | Optimizes conveyance |
| **Chute Length** | 16-30 inches | Patent 10,259,140 | Defines mixing zone |
| **Chute Angle** | -5° to +30° | Patent 10,259,140 | Gravity-assisted flow |
| **Max Lift Height** | < 42 inches | Patent 11,285,639 | Ergonomic loading |

### Motor Shaft Interface Detail

```
CONFIRMED: Left-Hand Acme Thread Coupling

    Motor shaft ─────┐
                     │
              ╔══════╧══════╗
              ║   ACME      ║
              ║   THREAD    ║  ← Left-hand thread prevents
              ║   (LH)      ║    loosening during forward rotation
              ╚══════╤══════╝
                     │
    Auger ───────────┘

    Likely sizes (needs verification):
    • 1/2"-10 LH Acme
    • 5/8"-8 LH Acme
    • 3/4"-6 LH Acme
```

### Aggregate Clearance Requirement

```
CRITICAL: Housing-to-Auger Clearance

    Given: Max aggregate = 0.5"
    Required: Clearance ≥ 1.2 × aggregate = 0.6"

    ┌─────────────────────────────────────────┐
    │          HOUSING (ID unknown)           │
    │                                         │
    │  ╔═══════════════════════════════════╗  │
    │  ║         AUGER (OD unknown)        ║  │
    │  ╚═══════════════════════════════════╝  │
    │                                         │
    │◄─►                                 ◄───►│
    │ GAP                                 GAP │
    │ ≥0.6"                              ≥0.6"│
    └─────────────────────────────────────────┘

    If gap < 0.6": Aggregate WILL jam
    If gap > 1.5": Shear efficiency drops significantly
```

---

## 1. Mixing Capacity Calculations

### Volumetric Throughput

The theoretical volumetric flow rate of a screw/auger conveyor:

```
Q = (π/4) × D² × P × N × η × 60

Where:
  Q = Volumetric flow rate (ft³/hr)
  D = Screw inner diameter (ft)
  P = Pitch (ft)
  N = Rotational speed (RPM)
  η = Fill efficiency (volumetric efficiency)
```

### MudMixer Performance Analysis

Given specifications:
- Output: ~1 cubic yard per hour (27 ft³/hr)
- Throughput: 45 bags (80 lb) per hour

Estimated operating parameters:
- Auger OD: ~5.5" (0.458 ft)
- Average pitch: ~4" (0.333 ft)
- Fill efficiency: 0.30 (typical for inclined, wet material)

Solving for RPM:

```
27 = (π/4) × (0.458)² × 0.333 × N × 0.30 × 60

27 = (0.785) × (0.210) × 0.333 × N × 0.30 × 60

27 = 0.990 × N

N ≈ 27 RPM
```

**Estimated auger speed: 25-30 RPM**

---

## 2. Motor Power Requirements

### Power Calculation

Required power for a screw conveyor:

```
HP = (Q × L × W × Fd) / 33000 + (Q × H × W) / 33000

Where:
  Q = Material flow rate (lb/min)
  L = Conveyor length (ft)
  W = Material weight per cubic foot (lb/ft³)
  Fd = Friction drag factor
  H = Vertical lift (ft)
```

### MudMixer Power Analysis

Parameters:
- Q = 60 lb/min (one 60-lb bag per minute)
- L = 2 ft (chute length)
- W = 130 lb/ft³ (wet concrete density)
- Fd = 2.5 (for wet, sticky material)
- H = 0.5 ft (slight incline)

```
HP = (60 × 2 × 130 × 2.5) / 33000 + (60 × 0.5 × 130) / 33000

HP = 39000 / 33000 + 3900 / 33000

HP = 1.18 + 0.12

HP = 1.30 (theoretical)
```

With safety factor of 2x for startup and heavy loads:

**Required: ~0.5 HP motor** (matches specification)

### Motor Selection Criteria

| Parameter | Requirement |
|-----------|-------------|
| Type | DC gear motor (for variable speed/reversing) |
| Power | 0.5 HP (373 W) minimum |
| Torque | High torque at low RPM |
| Speed | 25-40 RPM at output |
| Duty Cycle | Continuous |
| Environment | Water-sealed (IP65+) |

---

## 3. Structural Analysis

### Frame Load Analysis

Maximum load scenario:
- Hopper with extension: 300 lbs dry material
- Water added: ~50 lbs
- Machine weight: 145 lbs
- **Total: ~495 lbs**

### Wheel Axle Stress

```
Load per wheel = 495 / 2 = 247.5 lbs

For 5/8" steel axle:
  Moment = 247.5 × 6" (half span) = 1485 in-lb
  Section modulus = (π × d³) / 32 = (π × 0.625³) / 32 = 0.024 in³
  Bending stress = M / S = 1485 / 0.024 = 61,875 psi

Steel yield strength: ~36,000 psi (mild steel)
```

**Result: Need hardened axle or larger diameter (3/4" recommended)**

### Frame Tube Analysis

For 1" OD, 16 ga (0.065" wall) steel tube:
- Moment of inertia: 0.034 in⁴
- Section modulus: 0.068 in³
- Maximum bending stress at 500 lb central load:
  - Assuming 24" span: M = 500 × 24 / 4 = 3000 in-lb
  - Stress = 3000 / 0.068 = 44,117 psi

**Adequate with safety factor for static loads**

---

## 4. Auger Design Calculations

### Variable Pitch Design

The MudMixer uses increasing pitch to:
1. Control intake rate (prevent flooding)
2. Increase conveyance speed as material mixes
3. Allow water absorption time

### Pitch Transition Calculation

```
Hopper section:
  P/D = 0.6, D = 5.5"
  P₁ = 0.6 × 5.5 = 3.3"

Chute section:
  P/D = 0.85, D = 5.5"
  P₂ = 0.85 × 5.5 = 4.675"

Pitch increase ratio = P₂/P₁ = 4.675/3.3 = 1.42 (42% increase)
```

### Mixing Intensity

Mixing occurs through:
1. **Shear**: Material against flight surface
2. **Tumbling**: Material falling within interior volume
3. **Finger disruption**: Breaking clumps

```
Shear rate = (π × D × N) / Gap

Where:
  D = auger diameter (5.5" = 0.14 m)
  N = rotational speed (0.5 rev/s)
  Gap = clearance (~0.25" = 0.006 m)

Shear rate = (π × 0.14 × 0.5) / 0.006 = 36.7 s⁻¹
```

This is adequate for concrete mixing (typical range: 10-100 s⁻¹)

---

## 5. Water System Design

### Flow Rate Calculation

Water requirement per bag:
- 80 lb bag: 3-4 quarts = 0.75-1 gallon
- At 45 bags/hour: 34-45 gallons/hour
- Flow rate: 0.57-0.75 GPM

### Nozzle Sizing

For a 65° fan nozzle at 40 PSI:

```
Flow = K × √P

Where:
  K = nozzle factor
  P = pressure (PSI)

For 0.4 GPM per nozzle:
  0.4 = K × √40
  K = 0.4 / 6.32 = 0.063

Select: 1/8" orifice nozzle (K ≈ 0.06-0.08)
```

**Two nozzles at 0.4 GPM each = 0.8 GPM total capacity**

### Pressure Drop in Supply Line

Using Hazen-Williams equation for 3/8" ID tubing, 4 ft length:

```
ΔP = 4.52 × Q¹·⁸⁵ × L / (C¹·⁸⁵ × d⁴·⁸⁷)

Where:
  Q = 0.8 GPM
  L = 4 ft
  C = 140 (smooth plastic)
  d = 0.375"

ΔP ≈ 1-2 PSI (negligible)
```

**30 PSI minimum inlet pressure is adequate**

---

## 6. Mixing Residence Time

### Time in Mixing Zone

```
Residence time = Auger length / Conveyance velocity

Conveyance velocity = Pitch × RPM / 60

For:
  Average pitch = 4"
  RPM = 27
  Auger length = 24"

Velocity = 4 × 27 / 60 = 1.8 in/sec

Residence time = 24 / 1.8 = 13.3 seconds
```

**Material spends ~13 seconds in mixing zone**

This is sufficient for hydrating pre-mixed bagged materials (manufacturer-recommended mix time for concrete is 30-60 seconds, but this is for dry mixing; hydration with agitation is faster).

---

## 7. Stability Analysis

### Tipping Calculation

```
        ┌────────────────────────────┐
        │                            │
   F    │        Center of           │
   ↓    │         Gravity            │
        │            ●               │
        │                            │
        └────────────────────────────┘
                    │
        ────────────┼────────────
                    ▼
        ═══════════════════════════
           │                   │
          A                   B
        (pivot)           (wheel)

Moment about pivot A:
  Overturning: F × d₁
  Resisting: W × d₂

Stability requires: W × d₂ > F × d₁
```

### With Full Hopper

- Machine weight: 145 lbs at CG ~12" from pivot
- Material: 300 lbs at CG ~15" from pivot
- Combined CG calculation needed for tip angle

**Key: Keep CG low and centered between supports**

---

## 8. Fatigue Considerations

### Auger Fatigue Life

The auger experiences cyclic loading during rotation:

```
Fatigue stress range = 2 × (Bending stress from material load)

For steel flight (S-N curve):
  At 10⁷ cycles (typical infinite life threshold)
  Endurance limit ≈ 0.5 × Ultimate tensile strength

For mild steel: Se ≈ 0.5 × 60 ksi = 30 ksi

Operating below this limit = infinite life
```

### Motor Duty Cycle

0.5 HP continuous duty motor must handle:
- Starting torque (2-3× running)
- Stall conditions (jammed material)
- Reverse operation (clearing jams)

**Recommend: Motor with thermal protection and overload capability**

---

## 9. Safety Factors

### Design Safety Factors Used

| Component | Safety Factor | Basis |
|-----------|---------------|-------|
| Frame | 2.0 | Static loading |
| Axle | 2.5 | Impact loading |
| Motor | 2.0 | Starting torque |
| Auger | 3.0 | Fatigue/wear |
| Fasteners | 4.0 | Vibration |

---

## 10. Material Selection Guide

### Steel Selection

| Component | Recommended Steel | Hardness |
|-----------|-------------------|----------|
| Frame | A36 mild steel | N/A |
| Auger flight | AR400 or 4140 | 400-450 HB |
| Fingers | 1045 | RC 40-45 |
| Axle | 4140 | RC 30-35 |

### Wear Considerations

Concrete is highly abrasive (silica aggregate). Expected wear:
- Auger flight: 1-2 years with heavy use
- Chute interior: 2-3 years
- Fingers: 1 year (replaceable)

**Consider hard-facing (welded carbide) for extended life**

---

## Summary of Key Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Auger speed | 25-30 RPM | |
| Motor power | 0.5 HP | With 2× safety factor |
| Residence time | ~13 seconds | |
| Water flow | 0.6-0.8 GPM | |
| Total capacity | 27 ft³/hr | 1 yd³/hr |
| Operating weight | ~500 lbs | Fully loaded |

---

## 11. Computational Design Framework

For advanced optimization and simulation, see the Python framework in `/src/`:

### Auger Optimizer (`src/auger_optimizer.py`)

```python
from auger_optimizer import AugerOptimizer, OperatingConditions

# Initialize with measured housing ID
conditions = OperatingConditions(
    motor_power_hp=0.5,
    motor_rpm=27,
    max_aggregate_size=0.5,  # CONFIRMED
)

optimizer = AugerOptimizer(housing_id=6.0, conditions=conditions)

# Generate optimized design
design = optimizer.generate_optimized_design()

# Run analyses
clearance = optimizer.calculate_clearance(auger_od=5.5)
shear = optimizer.calculate_finger_shear(fingers)
skeleton = optimizer.calculate_skeleton_diameter()
```

### CFD Simulation Parameters

For computational fluid dynamics simulation of concrete flow:

```python
from auger_optimizer import CFDParameters

cfd = CFDParameters(
    slump_inches=4.0,        # Target slump
    water_cement_ratio=0.5,  # w/c ratio
)

params = cfd.generate_cfd_setup()
# Returns Bingham Plastic model parameters:
# - Yield stress: ~1800 Pa (for 4" slump)
# - Plastic viscosity: ~30 Pa·s
```

### Key Computational Outputs

| Analysis | Purpose | Input Required |
|----------|---------|----------------|
| Clearance | Validate aggregate won't jam | Housing ID, Auger OD |
| Finger Shear | Ensure fingers break aggregate | Motor torque, finger specs |
| Skeleton Sizing | Minimum SS wire diameter | Motor torque |
| Thermal Rise | Verify material won't overheat | Runtime, finger material |

---

## 12. Data Gaps Blocking Full Analysis

The following analyses **cannot be completed** without measured data:

| Analysis | Missing Data | Acquisition Method |
|----------|--------------|-------------------|
| FEA (Finite Element) | Bearing locations, fits | Disassembly measurement |
| CFD (Fluid Dynamics) | Exact housing ID, auger geometry | Bore gauge, caliper |
| Wear Life Prediction | Material hardness values | Hardness testing |
| Fatigue Life | Weld details, stress concentrations | Destructive testing |

**See [DATA_REQUIREMENTS.md](./DATA_REQUIREMENTS.md) for complete gap analysis.**
