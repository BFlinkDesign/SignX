# Main Assemblies and Components

## Assembly Overview

The MudMixer consists of six main assemblies:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MUDMIXER ASSEMBLY                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │  FRAME   │    │  HOPPER  │    │   AUGER  │    │  CHUTE   │      │
│  │ ASSEMBLY │◄──►│ ASSEMBLY │◄──►│ ASSEMBLY │◄──►│ ASSEMBLY │      │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘      │
│       ▲               ▲               ▲               ▲             │
│       │               │               │               │             │
│       ▼               ▼               ▼               ▼             │
│  ┌──────────┐    ┌──────────┐                                       │
│  │  DRIVE   │    │  WATER   │                                       │
│  │  SYSTEM  │    │  SYSTEM  │                                       │
│  └──────────┘    └──────────┘                                       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. Frame Assembly

### Components

| Ref | Component | Specification | Qty |
|-----|-----------|---------------|-----|
| 101 | Main Frame | 1" steel pipe | 1 |
| 102 | Cross Members | 1" steel pipe | 2-4 |
| 105 | Handle Assembly | Steel tube | 1 |
| 106 | Handle Grips | Rubber/plastic | 2 |
| 110 | Wheels | Marathon flat-free | 2 |
| 111 | Wheel Axle | Steel rod | 1 |
| 112 | Axle Brackets | Steel plate | 2 |
| 160 | Support Rests | Steel feet | 2-4 |
| 202 | Motor Mount Plate | Steel plate | 1 |
| 214 | Pivot Mount | Steel bracket | 1 |

### Construction Details

- **Material**: 1-inch diameter steel pipe for main structure
- **Body panels**: 14 gauge high-strength steel
- **Wheels**: Marathon flat-free pneumatic-style (no punctures)
- **Finish**: Powder-coated for corrosion resistance

### Frame Functions

1. Supports all other assemblies
2. Provides mobility via wheels
3. Offers stable base via support rests
4. Allows pivoting of hopper/chute assembly

---

## 2. Hopper Assembly

### Components

| Ref | Component | Specification | Qty |
|-----|-----------|---------------|-----|
| 120 | Hopper Body | 14 ga steel | 1 |
| 122 | Hopper Rim | Rolled steel edge | 1 |
| 128 | Aperture Opening | To chute | 1 |
| 200 | Hopper Extension (optional) | Steel | 1 |
| 210 | Extension Brackets | Steel | 2-4 |

### Specifications

| Parameter | Value |
|-----------|-------|
| Capacity (standard) | 120 lbs |
| Capacity (with extension) | 300 lbs |
| Maximum Lift Height | < 42 inches |
| Wall Thickness | 14 gauge (1.9 mm) |
| Aperture | Connects to chute |

### Features

- **Bag Opening Blade**: Disposed within hopper for opening bags
- **Guard**: Pivotally coupled to hopper, covers auger portion
- **Rigid Coupling**: Hopper is rigidly attached to chute
- **Pivot Connection**: Hopper/chute pivots on frame

---

## 3. Chute Assembly

### Components

| Ref | Component | Specification | Qty |
|-----|-----------|---------------|-----|
| 130 | Chute Body | Steel tube | 1 |
| 136 | Chute Interior | Smooth bore | 1 |
| 140 | Discharge Opening | Flared end | 1 |
| - | Pivot Plate (1st) | Fixed to frame | 1 |
| - | Pivot Plate (2nd) | Attached to chute | 1 |
| - | Spring Assembly | Biasing spring | 1 |

### Specifications

| Parameter | Value |
|-----------|-------|
| Length | 16-30 inches |
| Angle (adjustable) | -5° to +30° declination |
| Tilt Positions | 15°, 25°, 35° |
| Swivel Range | 330° |
| Discharge Height | 16 inches |

### Pivot Assembly Details

The pivot assembly includes:
- First plate (fixed to frame)
- Second plate (attached to hopper/chute)
- Spring that biases second plate away from first
- Allows 240°+ rotation with respect to frame

---

## 4. Auger Assembly

### Components

| Ref | Component | Specification | Qty |
|-----|-----------|---------------|-----|
| 700 | Auger Body | Shaftless helical | 1 |
| 804 | First Body Portion | In hopper | 1 |
| 806 | Second Body Portion | In chute | 1 |
| 808 | Helical Flight | Shaftless spiral | 1 |
| 810 | Interior Volume | Open center | - |
| 820-832 | Fingers | Inward extending | Multiple |

### Key Design Features

| Feature | Description |
|---------|-------------|
| Type | Shaftless helical auger |
| Interior | Open (no center shaft) |
| Fingers | Extend inward from flight into interior volume |
| Variable Pitch | Second portion has greater pitch than first |

### Pitch Specifications

| Location | Pitch-to-Diameter Ratio |
|----------|------------------------|
| First Portion (hopper) | 0.2 to 0.9 (preferably 0.5 to 0.8) |
| Second Portion (chute) | 0.6 to 1.0 |
| Transition | Continuous or step-wise increase |

*See [AUGER_DESIGN.md](./AUGER_DESIGN.md) for detailed auger specifications*

---

## 5. Drive System

### Components

| Ref | Component | Specification | Qty |
|-----|-----------|---------------|-----|
| 150 | Motor | 0.5 HP DC motor | 1 |
| 151 | Motor Housing | Water-sealed | 1 |
| 152 | Motor Shaft | Coupled to auger | 1 |
| 300 | AC-DC Transformer | 120V AC to DC | 1 |
| - | Power Cord | 3 ft, grounded | 1 |
| - | Forward/Reverse Switch | DPDT type | 1 |

### Motor Specifications

| Parameter | Value |
|-----------|-------|
| Type | DC motor (water-sealed) |
| Power | 0.5 HP (373 W) |
| Input | 120V AC via transformer |
| Current | 2.6 Amps |
| Operation | Forward/reverse capable |
| Mounting | Coupled to hopper |
| Drive Type | Direct drive, high-torque |

### Electrical System

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  120V AC    │───►│  AC-to-DC   │───►│  DC Motor   │
│  Outlet     │    │ Transformer │    │  0.5 HP     │
└─────────────┘    └─────────────┘    └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │ Fwd/Rev     │
                   │ Switch      │
                   └─────────────┘
```

---

## 6. Water Supply System

### Components

| Ref | Component | Specification | Qty |
|-----|-----------|---------------|-----|
| - | Water Inlet | Garden hose fitting | 1 |
| - | Flow Control Dial | Adjustable valve | 1 |
| - | Supply Line | Internal tubing | 1 |
| - | Spray Nozzles | Dual internal | 2 |

### Specifications

| Parameter | Value |
|-----------|-------|
| Minimum Pressure | 30 PSI |
| Nozzle Count | 2 (dual) |
| Injection Point | At aperture/auger entry |
| Flow Control | Fully adjustable dial |
| Connection | Standard garden hose |

### Water System Operation

```
Garden Hose ──► Inlet ──► Flow Control ──► Internal Line ──► Dual Nozzles
   (30 PSI)              (adjustable)                        (spray into chute)
```

The water is applied to the cementitious mix as it enters the auger at the aperture between hopper and chute.

---

## Assembly Relationships

```
                    ┌─────────────┐
                    │   MOTOR     │
                    │   (150)     │
                    └──────┬──────┘
                           │ drives
                           ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   HOPPER    │────►│   AUGER     │────►│   CHUTE     │
│   (120)     │     │   (700)     │     │   (130)     │
└──────┬──────┘     └─────────────┘     └──────┬──────┘
       │                   ▲                    │
       │ rigid             │ extends            │ rigid
       │ coupling          │ through            │ coupling
       └───────────────────┴────────────────────┘
                           │
                     pivot joint
                           │
                    ┌──────▼──────┐
                    │   FRAME     │
                    │   (101)     │
                    └─────────────┘
```

---

## Optional Components

| Component | Function |
|-----------|----------|
| Hopper Extension | Increases capacity from 120 to 300 lbs |
| Bag Opening Blade | Cuts open bags within hopper |
| Auger Guard | Safety cover over exposed auger |
