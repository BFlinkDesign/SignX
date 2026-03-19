# Sign Engineering Calculator

A single-file HTML application for structural engineering calculations for freestanding signs. Open `sign-engineering-calculator.html` in any browser — no server, no dependencies, no build step.

## Current Capabilities

### Calculations
- **Wind Load**: ASCE 7-10/16/22 velocity pressure method (qz = 0.00256 * Kz * Kzt * Kd * Ke * V^2) and UBC 1997 legacy direct PSF
- **Section Modulus**: Required S for column sizing, auto-selects from 21 Sch 40 pipe sizes (2"-36") and 10 square tube sizes (2"-12")
- **Anchor Bolts**: A307 bolt sizing for moment resistance (11 sizes, 1/2" to 3"), auto-find smallest working bolt
- **Foundation**: Overturning, sliding, and bearing checks for circular/square/rectangular piers, auto-find minimum passing size
- **Gusset/Base Plate**: Pre-engineered gusset dimensions for all 21 pipe sizes, minimum base plate sizing
- **Auto-Feasibility**: Section Modulus tab shows at-a-glance bolt, foundation, gusset, and weight estimates

### Features
- Real-time recalculation on every input change
- 6 sign presets (Small, Medium, Monument, Pole Sign, Highway, EMC)
- 4 foundation presets (Sm Caisson, Med Caisson, Lg Square, Spread)
- Code selector: UBC 1997, ASCE 7-10, ASCE 7-16, ASCE 7-22 (default)
- SVG diagrams for sign elevation and foundation cross-section
- Copy-paste prompt summary for AI-assisted engineering
- Summary strip header showing S_req, wind force, moment, pipe, bolt, foundation

### Engineering Standards
- **Default code**: ASCE 7-22 / IBC 2024
- **Steel**: A36 (Fy = 36 ksi), New (0.66Fy) and Used (0.60Fy) allowable stress
- **Bolts**: A307 (Fb = 20 ksi allowable tensile stress)
- **Soil**: UBC Table 18-I-A (Clay, Sand, Gravel, Rock)
- **Iowa defaults**: 115 mph wind, 42" frost line, Exposure C

## Repository Structure

```
sign-engineering-calculator.html   # The application (self-contained)
CLAUDE.md                          # AI session context for Claude Code
README.md                          # This file
docs/
  engineering-codes.md             # Gold standard code references
  formulas.md                      # All engineering formulas used + needed
  competitor-analysis.md           # Market research on competing tools
  roadmap.md                       # Development priorities
  session-handoff.md               # Complete session context for continuation
  architecture.md                  # Code architecture and data flow
  context.md                       # How the tool works (technical overview)
  guide-simple-english.md          # Plain-language explanation of all calculations
```

## License

Proprietary. Not for redistribution.
