# Electrical Schematic - MudMixer Drive System

## System Overview

```
                        ELECTRICAL SYSTEM BLOCK DIAGRAM

    ┌─────────────────────────────────────────────────────────────────┐
    │                                                                 │
    │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
    │  │  120V AC │───►│  AC-DC   │───►│ FWD/REV  │───►│ DC MOTOR │  │
    │  │  OUTLET  │    │TRANSFORM │    │  SWITCH  │    │  0.5 HP  │  │
    │  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
    │       │               │               │               │         │
    │       │               │               │               │         │
    │  3' cord         Power supply    DPDT switch     Water-sealed  │
    │  grounded        with fuse       20A rated        gear motor   │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘
```

## Wiring Schematic

```
                    MAIN CIRCUIT DIAGRAM

                         120V AC
                           │
                           │
    ┌──────────────────────┴──────────────────────┐
    │                   PLUG                       │
    │               (3-prong grounded)             │
    │           ┌───────────────────┐              │
    │           │    L    N    G    │              │
    │           └────┬────┬────┬────┘              │
    └────────────────┼────┼────┼───────────────────┘
                     │    │    │
                     │    │    │
    ┌────────────────┴────┴────┴───────────────────┐
    │              POWER CORD (14 AWG)             │
    │                   3 feet                      │
    │         HOT ─┬─  NEUT ─┬─  GND ─┬─           │
    └──────────────┼─────────┼────────┼────────────┘
                   │         │        │
                   │         │        │
    ╔══════════════╪═════════╪════════╪════════════╗
    ║              │         │        │            ║
    ║         ┌────┴────┐    │        │            ║
    ║         │  FUSE   │    │        │            ║
    ║         │  15A    │    │        │            ║
    ║         └────┬────┘    │        │            ║
    ║              │         │        │            ║
    ║    ╔═════════╪═════════╪════════╪═════════╗  ║
    ║    ║         │         │        │         ║  ║
    ║    ║    ┌────┴─────────┴────┐   │         ║  ║
    ║    ║    │    AC-DC          │   │         ║  ║
    ║    ║    │    TRANSFORMER    │   │         ║  ║
    ║    ║    │                   │   │         ║  ║
    ║    ║    │  120V AC ──► DC   │   │         ║  ║
    ║    ║    │  (12V or 24V)     │   │         ║  ║
    ║    ║    │                   │   │         ║  ║
    ║    ║    └────┬─────────┬────┘   │         ║  ║
    ║    ║         │ +     - │        │         ║  ║
    ║    ║         │         │        │         ║  ║
    ║    ╚═════════╪═════════╪════════╪═════════╝  ║
    ║              │         │        │            ║
    ║    ╔═════════╪═════════╪════════╪═════════╗  ║
    ║    ║         │         │        │         ║  ║
    ║    ║    ┌────┴─────────┴────┐   │         ║  ║
    ║    ║    │                   │   │         ║  ║
    ║    ║    │   DPDT SWITCH     │   │         ║  ║
    ║    ║    │   (FWD/OFF/REV)   │   │         ║  ║
    ║    ║    │                   │   │         ║  ║
    ║    ║    │  ○  ───●───  ○    │   │         ║  ║
    ║    ║    │  1     C1    2    │   │         ║  ║
    ║    ║    │                   │   │         ║  ║
    ║    ║    │  ○  ───●───  ○    │   │         ║  ║
    ║    ║    │  3     C2    4    │   │         ║  ║
    ║    ║    │                   │   │         ║  ║
    ║    ║    └────┬─────────┬────┘   │         ║  ║
    ║    ║         │         │        │         ║  ║
    ║    ╚═════════╪═════════╪════════╪═════════╝  ║
    ║              │         │        │            ║
    ║    ╔═════════╪═════════╪════════╪═════════╗  ║
    ║    ║         │         │        │         ║  ║
    ║    ║    ┌────┴─────────┴────┐   │         ║  ║
    ║    ║    │                   │   │         ║  ║
    ║    ║    │    DC MOTOR       │   ╧ GND     ║  ║
    ║    ║    │    0.5 HP         │   │(chassis)║  ║
    ║    ║    │    (water-sealed) ├───┘         ║  ║
    ║    ║    │                   │             ║  ║
    ║    ║    │      ╭───╮        │             ║  ║
    ║    ║    │  +───┤ M ├───-    │             ║  ║
    ║    ║    │      ╰───╯        │             ║  ║
    ║    ║    │                   │             ║  ║
    ║    ║    └───────────────────┘             ║  ║
    ║    ║                                      ║  ║
    ║    ╚══════════════════════════════════════╝  ║
    ║                                              ║
    ╚══════════════════════════════════════════════╝
```

## DPDT Switch Wiring Detail

```
                FORWARD/OFF/REVERSE SWITCH
              (Double Pole Double Throw - Center Off)


                    SWITCH TERMINAL LAYOUT

                    ┌─────────────────┐
                    │                 │
                    │  ○ 1       2 ○  │
                    │     ╲     ╱     │
                    │      ╲   ╱      │
                    │       ╲ ╱       │
                    │    C1 ─●─ C2    │   ← Common terminals
                    │       ╱ ╲       │
                    │      ╱   ╲      │
                    │     ╱     ╲     │
                    │  ○ 3       4 ○  │
                    │                 │
                    └─────────────────┘


                    WIRING CONNECTIONS

    From Transformer:
        (+) ──────────► Terminal 1
        (+) ──────────► Terminal 4
        (-) ──────────► Terminal 2
        (-) ──────────► Terminal 3

    To Motor:
        Terminal C1 ──────────► Motor (+)
        Terminal C2 ──────────► Motor (-)


                    SWITCH POSITIONS

    FORWARD:                      OFF:                       REVERSE:
    ┌─────────┐                  ┌─────────┐                ┌─────────┐
    │ ●───●   │                  │ ○   ○   │                │   ●───● │
    │ 1   C1  │                  │ 1   C1  │                │   C1  2 │
    │         │                  │         │                │         │
    │ ●───●   │                  │ ○   ○   │                │   ●───● │
    │ 3   C2  │                  │ 3   C2  │                │   C2  4 │
    └─────────┘                  └─────────┘                └─────────┘

    Current flow:                No current                 Current flow:
    + → 1 → C1 → Motor(+)                                   + → 4 → C2 → Motor(-)
    - → 3 → C2 → Motor(-)                                   - → 2 → C1 → Motor(+)
    Motor runs FORWARD                                      Motor runs REVERSE
```

## Component Specifications

```
    ┌─────────────────────────────────────────────────────────────────┐
    │                    ELECTRICAL COMPONENTS                        │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                 │
    │  COMPONENT          SPECIFICATION               NOTES           │
    │  ──────────────────────────────────────────────────────────     │
    │                                                                 │
    │  Power Cord         14 AWG, 3-conductor        3' length        │
    │                     SJTW or equivalent         Grounded plug    │
    │                                                                 │
    │  Fuse               15A, 250V, fast-blow       Inline holder    │
    │                                                                 │
    │  AC-DC Transformer  120V AC input              Select for motor │
    │                     12V or 24V DC output       voltage          │
    │                     500W capacity              With cooling     │
    │                                                                 │
    │  DPDT Switch        20A @ 12V/24V DC           Center-off       │
    │                     Momentary or maintained    Weatherproof     │
    │                                                                 │
    │  DC Motor           0.5 HP (373W)              Water-sealed     │
    │                     12V or 24V DC              High torque      │
    │                     Gear reduced               25-40 RPM out    │
    │                                                                 │
    │  Wire               14 AWG stranded            Color-coded      │
    │                     Automotive grade           Moisture resist  │
    │                                                                 │
    │  Connectors         Crimp ring terminals       Insulated        │
    │                     Heat shrink butt splices   Waterproof       │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘
```

## Safety Features

```
    ┌─────────────────────────────────────────────────────────────────┐
    │                    ELECTRICAL SAFETY                            │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                 │
    │  1. GROUNDING                                                   │
    │     - Chassis ground connected to earth ground                  │
    │     - Motor housing grounded                                    │
    │     - All metal components bonded                               │
    │                                                                 │
    │  2. OVERCURRENT PROTECTION                                      │
    │     - 15A fuse protects against short circuits                  │
    │     - Transformer may have internal protection                  │
    │                                                                 │
    │  3. WATERPROOFING                                               │
    │     - Motor is water-sealed (IP65 or better)                    │
    │     - Switch box should be weatherproof                         │
    │     - All connections sealed with heat shrink                   │
    │                                                                 │
    │  4. STRAIN RELIEF                                               │
    │     - Power cord secured at entry point                         │
    │     - No tension on internal connections                        │
    │                                                                 │
    │  5. LABELING                                                    │
    │     - Warning labels for electrical hazard                      │
    │     - Operating instructions visible                            │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘
```

## Wiring Diagram - Physical Layout

```
                    PHYSICAL WIRING LAYOUT

                              TOP VIEW

                         ┌───────────────┐
                         │     MOTOR     │
                         │      ┌─┐      │
                         │   ───┤M├───   │
                         │      └─┘      │
                         └───────┬───────┘
                                 │
                    MOTOR WIRES  │  (to switch)
                     (2 wires)   │
    ┌────────────────────────────┼────────────────────────────────┐
    │                            │                                │
    │           HOPPER           │                                │
    │                            │                                │
    │                   ┌────────┴────────┐                       │
    │                   │   SWITCH BOX    │                       │
    │                   │   ┌────────┐    │                       │
    │                   │   │FWD OFF │    │                       │
    │                   │   │  REV   │    │                       │
    │                   │   └────────┘    │                       │
    │                   └────────┬────────┘                       │
    │                            │                                │
    └────────────────────────────┼────────────────────────────────┘
                                 │
                    DC WIRES     │  (from transformer)
                                 │
                    ┌────────────┴────────────┐
                    │      TRANSFORMER        │
                    │     ┌────────────┐      │
                    │     │ 120V ► DC  │      │
                    │     └────────────┘      │
                    └────────────┬────────────┘
                                 │
                    AC WIRES     │  (from plug)
                     (3 wires)   │
                    ┌────────────┴────────────┐
                    │                         │
                    │   ══════════════════    │ ◄── Power Cord (3')
                    │                         │
                    └────────────┬────────────┘
                                 │
                         ┌───────┴───────┐
                         │    PLUG       │
                         │  ┌─────────┐  │
                         │  │ L  N  G │  │
                         │  └─────────┘  │
                         └───────────────┘
                               ║
                         To 120V Outlet
```

## Wire Run Lengths and Gauges

```
    ┌─────────────────────────────────────────────────────────────────┐
    │                    WIRE SPECIFICATIONS                          │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                 │
    │  RUN               LENGTH    GAUGE    CURRENT    NOTES          │
    │  ────────────────────────────────────────────────────────────   │
    │                                                                 │
    │  Plug to Trans     3 ft      14 AWG   15A max    3-conductor   │
    │                                                                 │
    │  Trans to Switch   2 ft      14 AWG   30A+       2-conductor   │
    │                                                                 │
    │  Switch to Motor   3 ft      14 AWG   30A+       2-conductor   │
    │                                                                 │
    │  Ground bonding    As req    14 AWG   N/A        Green/bare    │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘


    VOLTAGE DROP CALCULATION (DC side at 24V, 20A):

    VD = (2 × L × I × R) / 1000

    Where:
      L = length (feet) = 5 ft total
      I = current (amps) = 20A
      R = resistance per 1000 ft (14 AWG = 2.525 Ω)

    VD = (2 × 5 × 20 × 2.525) / 1000
    VD = 0.505 V

    Voltage drop: 0.5V (2% of 24V) - ACCEPTABLE
```
