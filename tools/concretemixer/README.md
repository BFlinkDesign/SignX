# MudMixer Reverse Engineering Project

## Overview

This project contains reverse-engineered documentation of the MudMixer portable continuous concrete/mortar mixer. The MudMixer is a patented continuous-feed mixing system that uses a shaftless helical auger to hydrate and mix bagged cementitious materials.

## Product Summary

| Attribute | Value |
|-----------|-------|
| **Manufacturer** | MudMixer, LLC (formerly Red Dog Mobile Shelters, LLC) |
| **Model** | MMXR-3221 / MMXR-3225 (Evolution) |
| **Type** | Continuous-feed portable electric mixer |
| **Patents** | US 10,259,140 B1, US 11,285,639 B2, D943,639 |

## Key Features

- **Continuous Mixing**: Unlike batch mixers, material flows through continuously
- **Shaftless Helical Auger**: Variable-pitch design for optimal mixing and conveyance
- **Dual Spray Nozzles**: Water injection system with adjustable flow control
- **330° Swivel**: Precision placement capability
- **Portable Design**: Flat-free tires, lightweight frame (145 lbs)

## Design Requirements (Optimized Version)

| Requirement | Specification | Rationale |
|-------------|---------------|-----------|
| **Duty Cycle** | 12+ hours/day continuous | Jobsite commercial operation |
| **Primary Power** | 120V AC | Unlimited runtime, standard outlet |
| **Secondary Power** | DeWalt 20V/60V FlexVolt | Portable runs (1.5-3 hr) |
| **Finger Material** | Steel (not UHMW) | 12-hr thermal exceeds UHMW limits |
| **Thermal Management** | Active cooling required | Electronics need ventilation |

## Documentation Structure

### Core Documentation (`docs/`)
- [Technical Specifications](./docs/SPECIFICATIONS.md) - Dimensions, power, capacity
- [Main Assemblies](./docs/ASSEMBLIES.md) - Frame, hopper, chute, drive system
- [Auger Design](./docs/AUGER_DESIGN.md) - Shaftless auger geometry and principles
- [Water System](./docs/WATER_SYSTEM.md) - Spray nozzle and flow control
- [**Power System**](./docs/POWER_SYSTEM.md) - ⚡ Dual power: 120V AC + DeWalt FlexVolt
- [Bill of Materials](./docs/BOM.md) - Component list for replication
- [Engineering Calculations](./docs/ENGINEERING.md) - Design calculations and principles
- [**Data Requirements**](./docs/DATA_REQUIREMENTS.md) - ⚠️ Known vs unknown specs, critical gaps

### Technical Drawings (`drawings/`)
- [Assembly Drawing](./drawings/ASSEMBLY_DRAWING.md) - Side/front/top views
- [Auger Drawing](./drawings/AUGER_DRAWING.md) - Shaftless auger geometry
- [Electrical Schematic](./drawings/ELECTRICAL_SCHEMATIC.md) - Drive system wiring

### Computational Tools (`src/`)
- [auger_optimizer.py](./src/auger_optimizer.py) - Generative design framework
- [requirements.txt](./src/requirements.txt) - Python dependencies

## Operation Principle

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   DRY MIX ──▶ HOPPER ──▶ AUGER + WATER ──▶ CHUTE ──▶ OUTPUT │
│              (120 lbs)    (dual spray)     (16")            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

1. Dry bagged mix (concrete, mortar, stucco) is loaded into the hopper
2. Material flows by gravity into the shaftless auger
3. Water is injected via dual spray nozzles at adjustable rate
4. Auger rotates, mixing and conveying material through chute
5. Mixed material exits through 330° swivel chute for placement

## Performance

- **Throughput**: 45+ bags (80 lb) per hour
- **Output Rate**: ~1 cubic yard per hour
- **Mix Rate**: ~1 bag (60 lb) per minute

## Key Confirmed Specifications

| Parameter | Value | Source |
|-----------|-------|--------|
| Max Aggregate Size | **0.5 inch** | MudMixer Specs |
| Motor Coupling | **Left-Hand Acme Thread** | Patent 10,259,140 |
| Hopper P/D Ratio | 0.2 - 0.9 (preferred 0.5-0.8) | Patent Claims |
| Chute P/D Ratio | 0.6 - 1.0 | Patent Claims |
| Chute Length | 16 - 30 inches | Patent Claims |

## Critical Unknown Dimensions

> ⚠️ **The following must be measured before replication:**

| Parameter | Impact | Acquisition Method |
|-----------|--------|-------------------|
| Housing Internal Diameter | Clearance calculation, CFD | Bore gauge |
| Auger Outer Diameter | Clearance, flow rate | Caliper |
| Acme Thread Size | Motor coupling adapter | Thread gauge |
| Bearing Specifications | Load path analysis | Disassembly |

See [DATA_REQUIREMENTS.md](./docs/DATA_REQUIREMENTS.md) for complete analysis.

## Patents Referenced

| Patent | Title | Filed | Issued |
|--------|-------|-------|--------|
| US 10,259,140 B1 | Portable concrete mixer for hydrating and mixing concrete mix containing gravel aggregate in a continuous process | Oct 19, 2018 | Apr 16, 2019 |
| US 11,285,639 B2 | Portable mixer for hydrating and mixing cementitious mix in a continuous process | Mar 13, 2019 | Mar 29, 2022 |
| D943,639 | Design Patent (Mixer appearance) | - | Feb 15, 2022 |

## Sources

- [MudMixer Official Website](https://mudmixer.com/)
- [MudMixer Specifications](https://mudmixer.com/pages/specs)
- [US Patent 10,259,140](https://patents.justia.com/patent/10259140)
- [Freepatentsonline US 11,285,639](https://www.freepatentsonline.com/11285639.html)

## Disclaimer

This reverse engineering documentation is for educational and research purposes only. The MudMixer design is protected by the patents listed above. Any commercial use or manufacture must respect applicable intellectual property rights.
