# Auger Design Specifications

## Overview

The MudMixer uses a **shaftless helical auger** as its core mixing and conveying element. This design is critical to the mixer's ability to handle aggregate-containing concrete mixes in a continuous process.

## Auger Type: Shaftless Helical

Unlike traditional shaft-center augers, the MudMixer employs a shaftless design:

```
TRADITIONAL AUGER (with shaft):          SHAFTLESS AUGER (MudMixer):

    ─────────────────────────             ─────────────────────────
   ╱ ╲     ╱ ╲     ╱ ╲     ╱ ╲           ╱ ╲     ╱ ╲     ╱ ╲     ╱ ╲
  ╱   ╲   ╱   ╲   ╱   ╲   ╱   ╲         ╱   ╲   ╱   ╲   ╱   ╲   ╱   ╲
 ╱  ●  ╲ ╱  ●  ╲ ╱  ●  ╲ ╱  ●  ╲       ╱     ╲ ╱     ╲ ╱     ╲ ╱     ╲
 ╲     ╱ ╲     ╱ ╲     ╱ ╲     ╱       ╲     ╱ ╲     ╱ ╲     ╱ ╲     ╱
  ╲   ╱   ╲   ╱   ╲   ╱   ╲   ╱         ╲   ╱   ╲   ╱   ╲   ╱   ╲   ╱
   ╲ ╱     ╲ ╱     ╲ ╱     ╲ ╱           ╲ ╱     ╲ ╱     ╲ ╱     ╲ ╱
    ─────────────────────────             ─────────────────────────
         │                                      │
    Center shaft present                  Open interior volume
    (material flows around)               (material flows through)
```

### Advantages of Shaftless Design

1. **Handles aggregates**: No center shaft to jam on gravel
2. **Self-cleaning**: Open center reduces material buildup
3. **Sticky materials**: Originally developed for wet, sticky products
4. **Better mixing**: Fingers extend into interior volume for enhanced mixing

---

## Auger Geometry

### Two-Section Design

The auger consists of two distinct sections with different pitch characteristics:

```
        HOPPER SECTION              CHUTE SECTION
      (First Body Portion)      (Second Body Portion)

       Lower Pitch                  Higher Pitch
      ┌─────────────────┐        ┌─────────────────────┐
      │  ╱╲    ╱╲    ╱╲ │        │╱╲      ╱╲       ╱╲  │
      │ ╱  ╲  ╱  ╲  ╱  ╲│        │  ╲    ╱  ╲     ╱  ╲ │
      │╱    ╲╱    ╲╱    │   ──►  │   ╲  ╱    ╲   ╱    ╲│
      │                 │        │    ╲╱      ╲ ╱      │
      └─────────────────┘        └─────────────────────┘

      Pitch-to-Diameter:          Pitch-to-Diameter:
         0.5 - 0.8                   0.6 - 1.0
```

### Pitch Specifications

| Section | Location | Pitch-to-Diameter Ratio | Purpose |
|---------|----------|------------------------|---------|
| First Body Portion | Hopper | 0.2 - 0.9 (preferred 0.5 - 0.8) | Controlled intake, initial mixing |
| Second Body Portion | Chute | 0.6 - 1.0 | Accelerated conveyance, final mixing |

### Pitch Transition

The pitch can increase from first to second portion in two ways:

1. **Continuous increase**: Gradual pitch growth along length
2. **Step-wise increase**: Discrete pitch changes at specific points

```
CONTINUOUS PITCH INCREASE:

Pitch
  │
  │                              ●
  │                         ●
  │                    ●
  │               ●
  │          ●
  │     ●
  │●
  └────────────────────────────────►
       Hopper      │      Chute
                Aperture


STEP-WISE PITCH INCREASE:

Pitch
  │
  │                        ●────●
  │               ●────●
  │     ●────●
  │●
  └────────────────────────────────►
       Hopper      │      Chute
                Aperture
```

---

## Interior Volume and Fingers

### Finger Configuration

The shaftless auger includes **fingers** that extend inward from the helical flight into the interior volume:

```
CROSS-SECTION VIEW:

         ┌─────────────────────┐
         │    ╲    flight   ╱  │
         │     ╲           ╱   │
         │      ╲    ●    ╱    │  ← finger extends inward
         │       ╲  ╱│╲  ╱     │
         │        ╲╱ │ ╲╱      │
         │       ╱   │   ╲     │
         │      ╱ interior╲    │
         │     ╱   volume  ╲   │
         │    ╱             ╲  │
         └─────────────────────┘

SIDE VIEW WITH FINGERS:

    ══════════════════════════════════
     ╱    ╱    ╱    ╱    ╱    ╱    ╱
    ╱ ●  ╱ ●  ╱ ●  ╱ ●  ╱ ●  ╱ ●  ╱   ← fingers (●) at intervals
   ╱    ╱    ╱    ╱    ╱    ╱    ╱
    ══════════════════════════════════
```

### Finger Placement

- One finger is disposed approximately at the **aperture** (hopper-to-chute transition)
- Multiple fingers distributed along auger length
- Fingers break up material and enhance mixing action

### Finger Function

1. **Breaking action**: Disrupts material clumps
2. **Enhanced mixing**: Creates turbulence in material flow
3. **Aggregate handling**: Prevents gravel from bypassing mixing zone
4. **Water integration**: Helps incorporate water into dry mix

---

## Dimensional Calculations

### Pitch-to-Diameter Ratio

```
P/D = Pitch / Outer Diameter

Where:
  P = Pitch (distance for one complete revolution)
  D = Outer diameter of auger flight
```

### Example Calculations

Assuming an auger outer diameter of approximately 6 inches (152 mm):

| Section | P/D Ratio | Pitch (inches) | Pitch (mm) |
|---------|-----------|----------------|------------|
| Hopper (low) | 0.5 | 3.0 | 76 |
| Hopper (high) | 0.8 | 4.8 | 122 |
| Chute (low) | 0.6 | 3.6 | 91 |
| Chute (high) | 1.0 | 6.0 | 152 |

### Flight Thickness

For shaftless augers handling abrasive materials like concrete:
- **Typical**: 10-12 gauge steel
- **Heavy duty**: 3/16" to 1/4" plate

---

## Material Specifications

### Auger Construction

| Component | Material | Specification |
|-----------|----------|---------------|
| Helical Flight | High-strength steel | Heavier gauge helicoid |
| Fingers | Steel rod/flat | Welded to flight |
| Wear Surface | Hardened steel | Optional hard-facing |

### Material Considerations

1. **Abrasion resistance**: Concrete aggregates are highly abrasive
2. **Corrosion resistance**: Cement is alkaline; moisture present
3. **Strength**: Must handle 120-300 lbs of material
4. **Flexibility**: Shaftless design requires inherent rigidity

---

## Manufacturing Notes

### Shaftless Flight Production

Shaftless auger flights can be manufactured by:

1. **Helicoid forming**: Cold-rolled from flat strip
2. **Sectional assembly**: Individual flights welded together
3. **CNC rolling**: Precision-formed continuous flight

### Key Dimensions to Control

| Dimension | Tolerance | Impact |
|-----------|-----------|--------|
| Outer diameter | ±1/16" | Clearance in chute |
| Pitch | ±1/8" | Flow rate, mixing |
| Flight thickness | ±10% | Strength, wear life |
| Finger length | ±1/8" | Mixing effectiveness |

---

## Performance Characteristics

### Throughput Calculation

```
Volumetric Flow = (π × D² × P × N × η) / 4

Where:
  D = Inner diameter (material passage)
  P = Pitch
  N = Rotational speed (RPM)
  η = Fill efficiency (typically 0.3-0.45 for inclined)
```

### Mixing Efficiency

The variable pitch design achieves:
- **Lower pitch in hopper**: Controls intake, prevents flooding
- **Higher pitch in chute**: Accelerates conveyance, extends mixing time
- **Fingers**: Add shear and turbulence for water integration

---

## Comparison to Traditional Designs

| Feature | Traditional Shaft Auger | MudMixer Shaftless |
|---------|------------------------|-------------------|
| Center | Solid shaft | Open (interior volume) |
| Aggregate handling | Limited | Excellent |
| Jamming risk | Higher | Lower |
| Cleaning | Difficult | Self-cleaning tendency |
| Mixing action | Conveying dominant | Enhanced by fingers |
| Variable pitch | Possible | Implemented |
| Manufacturing | Standard | Specialized |

---

## References

- US Patent 10,259,140 B1 - Describes shaftless helical auger with variable pitch
- US Patent 11,285,639 B2 - Details finger configuration and pitch ratios
- CEMA Book No. 350 - Screw Conveyor Standards
