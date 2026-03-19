# Sign Engineering Calculator - Claude Code Context

## Project Overview
Single-file HTML application for sign structural engineering calculations.
Primary file: `sign-engineering-calculator.html` (~1270 lines, self-contained, no dependencies).

## Architecture
- **Single HTML file** with embedded CSS + JS (no build system, no dependencies)
- **Shared state model**: sign dimensions + wind + steel inputs flow to ALL tabs automatically via `calcShared()` -> `lastCalc` object
- **5 tabs**: Section Modulus, Anchor Bolt, Foundation, Gusset Table, Soil Reference
- **Code selector**: UBC 1997 (legacy PSF direct), ASCE 7-10/16/22 (V mph + factors)
- **Default code**: ASCE 7-22 / IBC 2024 (current gold standard, adopted in Iowa)
- **Real-time**: every input change triggers full recalculation across all tabs

## Key Functions
- `calcWindPSF()` - wind pressure calculation (UBC direct or ASCE 7 formula)
- `calcShared()` - master calculation, populates `lastCalc` object
- `calcBoltData()` - anchor bolt analysis
- `calcFoundSized()` - foundation check for given dimensions
- `autoSizeFound()` - iterates to find minimum passing foundation
- `autoBoltSize()` - finds smallest A307 bolt for 2x2 pattern @ 6" spacing
- `renderSection/Bolt/Foundation/Gusset/Soil()` - tab renderers
- `updatePrompt()` - generates copy-paste summary text

## Engineering Constants
- Steel: A36 (Fy=36ksi), New=0.66Fy, Used=0.60Fy
- Bolts: A307 (Fb=20ksi allowable), max 3" diameter
- ASCE 7: F = qz * G * Cf * As, qz = 0.00256 * Kz * Kzt * Kd * Ke * V^2
- Kz from ASCE 7 Table 26.10-1 (power-law formula)
- Foundation: overturning SF >= 1.5, sliding SF >= 1.5, bearing <= soil capacity
- Soil: UBC Table 18-I-A values (Clay/Sand/Gravel/Rock)

## Iowa Defaults (hardcoded)
- Wind speed: 115 mph (Risk Cat II)
- Frost line: 42" (foundations must extend below)
- Ground snow: 33 psf
- Code: IBC 2024 (references ASCE 7-22)

## Data Arrays
- `PIPE[]` - 21 Schedule 40 pipe sizes (2" to 36") with gusset data
- `SQ[]` - 10 square tube sizes (2" to 12")
- `BOLT[]` - 11 bolt sizes (1/2" to 3") with tensile areas
- `SOIL{}` - 4 soil types with vertical/lateral bearing values

## Development Priorities (from research)
See `docs/roadmap.md` for full prioritized list.
1. IBC 1807.3 foundation formulas (nonconstrained Eq 18-1, constrained Eq 18-2)
2. ACI 318-19 Ch.17 anchor bolt checks (breakout, pullout, side-face blowout)
3. AISC 360-22 baseplate bearing (Eq. J8-2)
4. Cf auto-calculation from ASCE 7 Fig 29.3-1
5. PDF report generation (PE-stampable)

## Code Style
- Compact, functional JavaScript (no frameworks)
- CSS custom properties for theming (dark theme)
- Inline styles in generated HTML for result cards
- `v(id, fallback)` helper reads numeric inputs
- `rv(groupId)` helper reads radio button state
- SVG diagrams generated inline

## Known Patterns
- Radio buttons use `.rbtn.active` class, set via `setRadio(btn)`
- Presets set input values then call `calc()`
- Auto-sizing iterates small arrays of candidate dimensions
- Summary strip in header shows key values at a glance
