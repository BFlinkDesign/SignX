# Auger Drawing - Shaftless Helical Design

## Side Elevation - Complete Auger

```
                              MOTOR COUPLING END
                                    │
    ┌───────────────────────────────┴───────────────────────────────┐
    │                                                               │
    │   ╔═══════════════════════════════════════════════════════╗   │
    │   ║                                                       ║   │
    │   ║   ●      ●      ●      ●      ●      ●      ●      ●  ║   │
    │   ║  ╱ ╲    ╱ ╲    ╱ ╲    ╱ ╲    ╱  ╲   ╱  ╲   ╱  ╲   ╱ ╲ ║   │
    │   ║ ╱   ╲  ╱   ╲  ╱   ╲  ╱   ╲  ╱    ╲ ╱    ╲ ╱    ╲ ╱   ║   │
    │   ║╱     ╲╱     ╲╱     ╲╱     ╲╱      ╲╱      ╲╱     ╲╱    ║   │
    │   ║╲     ╱╲     ╱╲     ╱╲     ╱╲      ╱╲      ╱╲     ╱╲    ║   │
    │   ║ ╲   ╱  ╲   ╱  ╲   ╱  ╲   ╱  ╲    ╱  ╲    ╱  ╲   ╱  ╲  ║   │
    │   ║  ╲ ╱    ╲ ╱    ╲ ╱    ╲ ╱    ╲  ╱    ╲  ╱    ╲ ╱    ╲ ║   │
    │   ║   ●      ●      ●      ●      ●      ●      ●      ● ◄╫───┼── FINGERS
    │   ║                                                       ║   │
    │   ╚═══════════════════════════════════════════════════════╝   │
    │                                                               │
    └───────────────────────────────────────────────────────────────┘
                    │                               │
                    │                               │
    ◄───────────────┴───────────────►◄──────────────┴───────────────►
         SECTION 1 (HOPPER)                SECTION 2 (CHUTE)
         Lower Pitch (P/D = 0.6)           Higher Pitch (P/D = 0.85)
              ~10 inches                        ~14 inches

    ◄─────────────────────────────────────────────────────────────────►
                    TOTAL LENGTH: ~24 inches (610 mm)
```

## Cross-Section View - Shaftless Design

```
                        5.5" (140 mm) OUTER DIAMETER
                   ◄───────────────────────────────────►

                           ┌───────────────┐
                          ╱                 ╲
                         ╱                   ╲
                        ╱      INTERIOR       ╲
                       │        VOLUME         │
                       │     (open center)     │
           FLIGHT ───► │                       │ ◄─── FLIGHT
          THICKNESS    │    ┌─────────────┐    │    THICKNESS
           (3/16")     │    │             │    │     (3/16")
                       │    │   FINGER    │    │
                       │    │     ●       │    │
                       │    │    ╱│╲      │    │
                       │    │   ╱ │ ╲     │    │
                       │    │  ╱  │  ╲    │    │
                       │    │ ╱   │   ╲   │    │
                       │    └─────┴─────┘  │    │
                       │                       │
                        ╲                     ╱
                         ╲                   ╱
                          ╲                 ╱
                           └───────────────┘

                   ◄───────────────────────────────────►
                         ~4.5" INTERIOR OPENING
                            (material passage)

    NOTE: Shaftless design allows material to flow through
          the center, handling aggregates without jamming
```

## Detail View - Finger Configuration

```
                    FINGER DETAIL (SIDE VIEW)

          FLIGHT SURFACE
               │
               │      ●──── FINGER (3/8" rod)
               │     ╱│
               │    ╱ │
               │   ╱  │
               │  ╱   │ 2" (50mm)
    ═══════════╪═╱════╪═══════════════════════
               │╱     │
         ──────●──────┴────────────────────────
               │
               │
               ▼
         INTO INTERIOR VOLUME


                    FINGER DETAIL (END VIEW)

                         ┌─────┐
                        ╱│     │╲
                       ╱ │     │ ╲
                      ╱  │     │  ╲
                     │   │     │   │
                     │   │  ●  │   │  ← FINGER
                     │   │ ╱│╲ │   │    extends
                     │   │╱ │ ╲│   │    inward
                     │   ▼  │  ▼   │
                     │      │      │
                      ╲     │     ╱
                       ╲    │    ╱
                        ╲   │   ╱
                         ╲  │  ╱
                          ╲ │ ╱
                           ╲│╱


    FINGER PLACEMENT ALONG AUGER:

    ┌────────────────────────────────────────────────────────────┐
    │                                                            │
    │  ●      ●      ●      ●      ●      ●      ●      ●       │
    │  1      2      3      4      5      6      7      8       │
    │                 ▲                                          │
    │                 │                                          │
    │            APERTURE                                        │
    │         (one finger at                                     │
    │          this location)                                    │
    └────────────────────────────────────────────────────────────┘

    Finger count: 8-12 total (approx. every 2-3 inches)
```

## Variable Pitch Detail

```
    PITCH TRANSITION DIAGRAM

                    SECTION 1              SECTION 2
                   (HOPPER)                (CHUTE)
                   ◄────────►             ◄─────────►

    Pitch (P)
        │
      5"│                                    ┌─────────
        │                                ┌───┘
      4"│                            ┌───┘
        │                        ┌───┘
      3"│  ─────────────────┬───┘
        │                   │
      2"│                   │
        │                   │
        └───────────────────┼────────────────────────────►
                         APERTURE                    Position
                      (hopper/chute
                       transition)


    STEP-WISE PITCH INCREASE:

         P₁ = 3.3"          P₂ = 4.0"          P₃ = 4.7"
    ◄──────────────────►◄──────────────────►◄──────────────────►

         ╱╲    ╱╲    ╱╲     ╱ ╲    ╱ ╲    ╱ ╲    ╱  ╲   ╱  ╲   ╱
        ╱  ╲  ╱  ╲  ╱  ╲   ╱   ╲  ╱   ╲  ╱   ╲  ╱    ╲ ╱    ╲ ╱
       ╱    ╲╱    ╲╱    ╲ ╱     ╲╱     ╲╱     ╲╱      ╲╱      ╲╱
                        │              │
                     Step 1         Step 2
```

## Dimensional Table

```
    ┌─────────────────────────────────────────────────────────────────┐
    │                    AUGER DIMENSIONS                             │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                 │
    │  Parameter              Section 1        Section 2              │
    │                         (Hopper)         (Chute)                │
    │  ───────────────────────────────────────────────────────────    │
    │  Outer Diameter         5.5" (140mm)     5.5" (140mm)           │
    │  Inner Opening          ~4.5" (114mm)    ~4.5" (114mm)          │
    │  Flight Thickness       3/16" (5mm)      3/16" (5mm)            │
    │  Pitch-to-Diameter      0.6              0.85                   │
    │  Pitch                  3.3" (84mm)      4.7" (119mm)           │
    │  Length                 ~10" (254mm)     ~14" (356mm)           │
    │  Fingers                4                4-8                     │
    │  Finger Length          2" (50mm)        2" (50mm)              │
    │  Finger Diameter        3/8" (10mm)      3/8" (10mm)            │
    │                                                                 │
    │  TOTAL LENGTH:          ~24" (610mm)                            │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘
```

## Drive Coupling Detail

```
                    MOTOR COUPLING END

                         ┌─────────────┐
                         │   MOTOR     │
                         │   SHAFT     │
                         │      │      │
                         └──────┼──────┘
                                │
                         ╔══════╪══════╗
                         ║   COUPLING  ║
                         ║   FLANGE    ║
                         ║      │      ║
                         ║   ●  ●  ●   ║ ◄── Bolt holes (4x)
                         ║      │      ║     5/16"-18
                         ╚══════╪══════╝
                                │
    ════════════════════════════╪════════════════════════════
    ║                           │                           ║
    ║    AUGER FLIGHT           │                           ║
    ║         ╱╲   ╱╲   ╱╲     │                           ║
    ║        ╱  ╲ ╱  ╲ ╱  ╲    │                           ║
    ║       ╱    ╲    ╲    ╲   │                           ║
    ════════════════════════════════════════════════════════


                    COUPLING FLANGE DETAIL
                        (TOP VIEW)

                         ╔═════════╗
                        ╱           ╲
                       ╱      ●      ╲    ← Bolt hole
                      │               │
                    ● │       ●       │ ●  ← Bolt holes
                      │   (shaft)     │
                       ╲      ●      ╱    ← Bolt hole
                        ╲           ╱
                         ╚═════════╝

                    Bolt pattern: 4 holes
                    Bolt circle: ~3" diameter
```

## Manufacturing Notes

```
    ┌─────────────────────────────────────────────────────────────────┐
    │                  MANUFACTURING NOTES                            │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                 │
    │  1. MATERIAL:                                                   │
    │     - Flight: AR400 or 4140 steel (abrasion resistant)          │
    │     - Fingers: 1045 steel, hardened                             │
    │     - Coupling: Mild steel or 4140                              │
    │                                                                 │
    │  2. FABRICATION:                                                │
    │     - Helicoid flight: Cold-rolled from flat strip              │
    │     - OR sectional: Individual flights welded together          │
    │     - Fingers: Welded perpendicular to flight surface           │
    │     - Coupling: Welded to first flight                          │
    │                                                                 │
    │  3. TOLERANCES:                                                 │
    │     - Outer diameter: ±1/16" (1.5mm)                            │
    │     - Pitch: ±1/8" (3mm)                                        │
    │     - Straightness: 1/16" per foot max                          │
    │                                                                 │
    │  4. SURFACE FINISH:                                             │
    │     - Deburr all edges                                          │
    │     - Consider hard-facing for extended life                    │
    │     - Prime and paint for corrosion protection                  │
    │                                                                 │
    │  5. BALANCING:                                                  │
    │     - Auger should be dynamically balanced                      │
    │     - Imbalance causes vibration and premature wear             │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘
```

## Flat Pattern Development

```
    HELICOID FLIGHT - FLAT PATTERN

    For one pitch of flight:

    Outer edge length = π × D × √(1 + (P/πD)²)
    Where D = 5.5", P = 4" (average)

    Outer edge = π × 5.5 × √(1 + (4/π×5.5)²)
               = 17.28 × √(1 + 0.053)
               = 17.28 × 1.026
               = 17.7" per pitch


                    FLAT BLANK SHAPE
                    (one pitch section)

                    ╱───────────────────╲
                   ╱                     ╲
                  ╱                       ╲
                 ╱    OUTER EDGE           ╲
                ╱       (17.7")             ╲
               ╱                             ╲
              ╱                               ╲
             │                                 │
             │                                 │
             │                                 │
              ╲                               ╱
               ╲                             ╱
                ╲    INNER EDGE            ╱
                 ╲     (~14")             ╱
                  ╲                     ╱
                   ╲                   ╱
                    ╲─────────────────╱

    Inner opening allows shaftless center
```

## Wear Indicators

```
    WEAR INSPECTION POINTS

                    NEW                      WORN (replace)

    Flight edge:    ┌───┐                    ┌──
                    │   │                    │
                    │   │                    │   ← Edge worn
                    │   │ 3/16" thick        │     to <1/8"
                    │   │                    │
                    └───┘                    └──

    Finger:         │                        │
                    │  ●  2"                 │  ● 1.5" ← Tip worn
                    │ ╱│╲                    │ ╱│
                   ─┴──┴──                  ─┴──┴──

    Outer diameter: Should maintain 5.5"
                    Replace if worn to <5.25"
                    (excessive chute clearance = poor mixing)
```
