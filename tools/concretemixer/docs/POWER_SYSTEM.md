# Power System Design

## Overview

The optimized MudMixer requires a dual-power system:
1. **Primary**: 120V AC for jobsite continuous operation (12+ hours/day)
2. **Secondary**: DeWalt 20V/60V FlexVolt battery for portable short runs

---

## 1. OPERATIONAL REQUIREMENTS

### Duty Cycle: HEAVY CONTINUOUS

| Parameter | Value | Impact |
|-----------|-------|--------|
| Daily Runtime | 12+ hours | Thermal management critical |
| Sessions | Continuous | No cool-down periods |
| Environment | Jobsite | Dust, moisture, vibration |
| Power Reliability | Mission-critical | Dual-source redundancy |

### Power Budget

| Component | Power (W) | Current @ 120V | Current @ 60V | Current @ 20V |
|-----------|-----------|----------------|---------------|---------------|
| Motor (0.5 HP) | 373 | 3.1 A | 6.2 A | 18.7 A |
| Losses (~15%) | 56 | 0.5 A | 0.9 A | 2.8 A |
| **Total** | **429** | **3.6 A** | **7.1 A** | **21.5 A** |

---

## 2. PRIMARY: 120V AC SYSTEM

### Specifications

| Parameter | Value | Notes |
|-----------|-------|-------|
| Input Voltage | 120V AC, 60Hz | Standard US jobsite |
| Input Current | 3.6 A (continuous) | Well under 15A circuit |
| Motor Voltage | 24V DC (preferred) | Via AC-DC converter |
| Cord Length | 3 ft (stock) + extension | Use 12 AWG for long runs |

### AC-DC Converter Selection

For 12-hour continuous duty, the power supply must be:

| Requirement | Specification |
|-------------|---------------|
| Output Voltage | 24V DC |
| Output Current | 20A continuous |
| Power Rating | 480W minimum (with headroom) |
| Efficiency | >90% (reduces heat) |
| Cooling | Active fan or convection |
| Protection | Over-temp, over-current, short-circuit |
| Enclosure | IP65 (dust/water resistant) |

**Recommended**: Mean Well HLG-480H-24A or equivalent

```
AC-DC POWER SUPPLY BLOCK DIAGRAM

    120V AC ──┬──► [FUSE 5A] ──► [EMI FILTER] ──► [RECTIFIER]
              │                                        │
              │                                        ▼
              │                               [PFC STAGE]
              │                                        │
              │                                        ▼
              │                               [DC-DC CONVERTER]
              │                                        │
              │                                        ▼
    GND ──────┴───────────────────────────────► [24V DC OUT]
                                                       │
                                               To Motor Controller
```

---

## 3. SECONDARY: DeWALT FLEXVOLT BATTERY SYSTEM

### FlexVolt Technology Overview

DeWalt FlexVolt batteries automatically switch voltage based on tool:

| Battery | Nominal Voltage | Max Voltage | Capacity |
|---------|-----------------|-------------|----------|
| DCB606 | 18V / 54V | 20V / 60V | 6.0 Ah |
| DCB609 | 18V / 54V | 20V / 60V | 9.0 Ah |
| DCB612 | 18V / 54V | 20V / 60V | 12.0 Ah |
| DCB615 | 18V / 54V | 20V / 60V | 15.0 Ah |

### Configuration Options

#### Option A: Single 60V FlexVolt (Recommended for portability)

```
SINGLE 60V CONFIGURATION

    ┌─────────────────────────┐
    │   DeWalt FlexVolt       │
    │   DCB612 (12Ah)         │
    │   60V MAX               │
    │                         │
    │   ┌─────────────────┐   │
    │   │ ● ● ● ● ● ● ● ● │   │ ← 60V terminal (adapter required)
    │   └─────────────────┘   │
    └─────────────────────────┘
              │
              ▼
    ┌─────────────────────────┐
    │   60V Battery Adapter    │
    │   (3rd party or custom)  │
    │                          │
    │   Output: 54V nominal    │
    └────────────┬─────────────┘
                 │
                 ▼
    ┌─────────────────────────┐
    │   DC-DC Buck Converter   │
    │   Input: 48-60V          │
    │   Output: 24V @ 20A      │
    └────────────┬─────────────┘
                 │
                 ▼
           Motor Controller
```

**Runtime Calculation (60V, 12Ah battery)**:
```
Energy = 54V × 12Ah = 648 Wh
Motor power = 429 W
Runtime = 648 / 429 = 1.5 hours

With 2 batteries rotating: 3 hours portable operation
```

#### Option B: Dual 60V (120V MAX) Configuration

```
DUAL 60V CONFIGURATION (120V MAX)

    ┌──────────────┐    ┌──────────────┐
    │  FlexVolt    │    │  FlexVolt    │
    │  60V #1      │    │  60V #2      │
    │  DCB612      │    │  DCB612      │
    └──────┬───────┘    └──────┬───────┘
           │                    │
           └────────┬───────────┘
                    │ Series connection
                    ▼
           ┌────────────────────┐
           │  120V MAX Adapter  │
           │  (108V nominal)    │
           └────────┬───────────┘
                    │
                    ▼
           ┌────────────────────┐
           │  DC-DC Converter   │
           │  Input: 90-120V DC │
           │  Output: 24V @ 20A │
           └────────┬───────────┘
                    │
                    ▼
              Motor Controller
```

**Runtime (2× 60V 12Ah in series)**:
```
Energy = 108V × 12Ah = 1296 Wh
Motor power = 429 W
Runtime = 1296 / 429 = 3.0 hours
```

### Battery Adapter Design

#### Custom 60V Adapter Specifications

| Parameter | Value |
|-----------|-------|
| Input | DeWalt 60V FlexVolt battery rail |
| Output | Anderson SB50 connector (recommended) |
| Max Current | 25A continuous |
| Fuse | 30A automotive blade |
| Indicator | LED for battery voltage |

```
ADAPTER PINOUT (60V FlexVolt)

    DeWalt Rail (18 pins):

    ┌─────────────────────────────────────┐
    │ ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● ● │
    │ 1 2 3 4 5 6 7 8 9 ...              18│
    └─────────────────────────────────────┘

    Key pins (verify with multimeter):
    - B+ (60V positive): Pins vary by cell config
    - B- (negative/ground): Common return
    - Sense/communication: For BMS handshake

    ⚠️ WARNING: 60V DC is hazardous (>50V threshold)
    Treat as mains-equivalent for safety
```

### DC-DC Converter for Battery Mode

| Requirement | Specification |
|-------------|---------------|
| Input Range | 48-120V DC (covers 60V and 120V configs) |
| Output | 24V DC regulated |
| Current | 20A continuous |
| Efficiency | >95% (critical for battery life) |
| Features | Soft-start, under-voltage lockout |

**Recommended**: Victron Orion-Tr 48/24-16 or similar isolated converter

---

## 4. POWER SOURCE SWITCHING

### Automatic Switchover Design

```
DUAL-SOURCE POWER SYSTEM

                    ┌─────────────────────────────┐
    120V AC ───────►│                             │
                    │      AC-DC CONVERTER        │
                    │      (480W, 24V out)        │
                    │                             │
                    └──────────────┬──────────────┘
                                   │ 24V DC
                                   ▼
                    ┌──────────────────────────────┐
                    │                              │
                    │    AUTOMATIC TRANSFER        │
                    │         SWITCH               │
                    │                              │
                    │  AC Present ──► Use AC       │
                    │  AC Lost ──► Use Battery     │
                    │                              │
                    └──────────────┬───────────────┘
                                   │
    Battery ───────►│              │
    (60V/120V)      │              │
                    │              │
         ┌──────────┴──────────┐   │
         │   DC-DC CONVERTER   │   │
         │   (48-120V → 24V)   │   │
         └──────────┬──────────┘   │
                    │              │
                    └──────┬───────┘
                           │ 24V DC (switched)
                           ▼
                    ┌──────────────────────────────┐
                    │      MOTOR CONTROLLER        │
                    │      (24V DC input)          │
                    │      FWD / REV / SPEED       │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                              DC MOTOR
                              (0.5 HP)
```

### Priority Logic

| Condition | Action |
|-----------|--------|
| AC present, battery present | Use AC, battery standby |
| AC present, battery absent | Use AC only |
| AC lost, battery present | Switch to battery (automatic) |
| AC lost, battery absent | System shutdown |
| Low battery (<48V) | Warning LED, switch to AC if available |

---

## 5. MOTOR CONTROLLER UPGRADE

For 12-hour continuous duty with dual power sources:

### Controller Requirements

| Feature | Specification |
|---------|---------------|
| Input Voltage | 24V DC (18-30V tolerance) |
| Output Current | 20A continuous, 40A peak |
| Control | Forward / Reverse / Variable Speed |
| Protection | Over-temp, over-current, stall detection |
| Cooling | Heatsink with fan (mandatory for 12hr duty) |
| Interface | Analog speed dial + direction switch |

### Recommended Controllers

| Option | Model | Features | Cost |
|--------|-------|----------|------|
| Budget | RoboClaw 2x30A | Dual H-bridge, serial/analog | ~$150 |
| Mid | Kelly KLS7230S | BLDC/PMDC, regen braking | ~$250 |
| Premium | Curtis 1204M-5301 | Industrial, sealed, CAN bus | ~$400 |

---

## 6. THERMAL MANAGEMENT (12-Hour Duty)

### Heat Sources

| Component | Heat Generated | Mitigation |
|-----------|----------------|------------|
| Motor | ~75W (20% loss) | Sealed, self-cooled |
| AC-DC Converter | ~50W (10% loss) | Active fan cooling |
| Motor Controller | ~25W (5% loss) | Heatsink + fan |
| DC-DC (battery) | ~20W (5% loss) | Heatsink |
| **Total** | **~170W** | Distributed cooling |

### Cooling Strategy

```
THERMAL MANAGEMENT LAYOUT

    ┌─────────────────────────────────────────────────────┐
    │                    ENCLOSURE                         │
    │                                                      │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
    │  │ AC-DC PSU   │  │ CONTROLLER  │  │ DC-DC CONV  │  │
    │  │    ═══      │  │    ═══      │  │    ═══      │  │
    │  │   (fan)     │  │  (heatsink) │  │  (heatsink) │  │
    │  └─────────────┘  └─────────────┘  └─────────────┘  │
    │         ▲                ▲                ▲          │
    │         │                │                │          │
    │  ═══════╧════════════════╧════════════════╧═══════  │
    │              VENTILATION CHANNEL                     │
    │                      ▲                               │
    │                      │                               │
    │               [ INTAKE VENTS ]                       │
    └─────────────────────────────────────────────────────┘
                           │
                    Ambient air (filtered)
```

### Over-Temperature Protection

| Threshold | Action |
|-----------|--------|
| 60°C (140°F) | Normal operation |
| 70°C (158°F) | Warning LED, increase fan speed |
| 80°C (176°F) | Reduce motor speed 50% |
| 90°C (194°F) | Emergency shutdown |

---

## 7. WIRING SPECIFICATIONS

### Wire Gauge Selection (24V System)

| Run | Current | Length | Gauge | Voltage Drop |
|-----|---------|--------|-------|--------------|
| PSU to Controller | 20A | 2 ft | 10 AWG | 0.3V (1.3%) |
| Controller to Motor | 20A | 3 ft | 10 AWG | 0.5V (2.1%) |
| Battery to DC-DC | 10A | 2 ft | 12 AWG | 0.2V (0.3%) |
| DC-DC to Controller | 20A | 1 ft | 10 AWG | 0.15V (0.6%) |

### Connector Selection

| Connection | Connector Type | Rating |
|------------|----------------|--------|
| AC Input | IEC C14 panel mount | 10A 250V |
| Battery Input | Anderson SB50 (red) | 50A 600V |
| Motor Output | Amphenol MS3106 | 25A sealed |
| Control Signals | Deutsch DT04-4P | 13A sealed |

---

## 8. SAFETY SYSTEMS

### Required Protections

| Hazard | Protection | Component |
|--------|------------|-----------|
| Overcurrent | Fuse + electronic | 25A blade + controller |
| Short circuit | Fast fuse | 30A HRC fuse |
| Ground fault | GFCI | Built into AC input |
| Over-temperature | Thermal switch | 85°C cutoff |
| Overvoltage | TVS diode | 30V clamping |
| Reverse polarity | Schottky diode | Battery input |

### Emergency Stop

```
E-STOP CIRCUIT

    24V ───┬───► [E-STOP NC] ───► [CONTACTOR COIL] ───► GND
           │            │
           │            └──► Contactor opens = Motor stops
           │
           └───► Power to controller (kills PWM)
```

---

## 9. BATTERY RUNTIME CALCULATOR

### Formula

```python
def calculate_runtime(battery_voltage, battery_ah, motor_power, efficiency=0.85):
    """
    Calculate battery runtime for concrete mixer.

    Args:
        battery_voltage: Nominal voltage (e.g., 54V for FlexVolt)
        battery_ah: Amp-hour capacity
        motor_power: Motor power in watts (373W for 0.5HP)
        efficiency: System efficiency (DC-DC + controller)

    Returns:
        Runtime in hours
    """
    battery_wh = battery_voltage * battery_ah
    actual_power = motor_power / efficiency
    runtime_hours = battery_wh / actual_power
    return runtime_hours

# Examples:
# Single 60V 12Ah: 54 * 12 / (373/0.85) = 1.48 hours
# Dual 60V 12Ah:   108 * 12 / (373/0.85) = 2.95 hours
# Single 60V 15Ah: 54 * 15 / (373/0.85) = 1.85 hours
```

### Runtime Table

| Configuration | Voltage | Capacity | Runtime | Use Case |
|---------------|---------|----------|---------|----------|
| 1× DCB606 | 54V | 6 Ah | 0.74 hr | Quick touch-up |
| 1× DCB609 | 54V | 9 Ah | 1.11 hr | Small job |
| 1× DCB612 | 54V | 12 Ah | 1.48 hr | Medium job |
| 1× DCB615 | 54V | 15 Ah | 1.85 hr | Extended portable |
| 2× DCB612 | 108V | 12 Ah | 2.95 hr | Heavy portable |
| 2× DCB615 | 108V | 15 Ah | 3.69 hr | Max portable |

---

## 10. BILL OF MATERIALS - POWER SYSTEM

| Item | Description | Qty | Est. Cost |
|------|-------------|-----|-----------|
| AC-DC PSU | Mean Well HLG-480H-24A | 1 | $120 |
| DC-DC Converter | 60V→24V 500W isolated | 1 | $80 |
| Motor Controller | 24V 30A with reversing | 1 | $150 |
| FlexVolt Adapter | 60V battery adapter | 1 | $40 |
| Transfer Switch | Auto AC/DC switchover | 1 | $60 |
| Fuses & Holders | Assorted protection | 1 set | $25 |
| Wiring | 10/12 AWG, connectors | 1 lot | $50 |
| Enclosure | IP65 electrical box | 1 | $40 |
| Cooling | Fans, heatsinks | 1 set | $35 |
| **Total** | | | **~$600** |

---

## Sources

- [DeWalt FlexVolt System](https://www.dewalt.com/systems/cordless-platforms/60v/flexvolt-battery-system)
- [DeWalt Battery Compatibility](https://blog.acmetools.com/dewalt-battery-compatability/)
- [FlexVolt 60V Adapter Project](https://hackaday.io/project/45999-dewalt-flexvolt-60v-battery-adapter)
