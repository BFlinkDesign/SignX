# Code Architecture

## File Structure
Single file: `sign-engineering-calculator.html` (~1270 lines)

```
Lines 1-255:     CSS (styles, dark theme, component classes)
Lines 257-543:   HTML (header, tabs, sidebar controls, main area)
Lines 545-589:   Data arrays (PIPE, SQ, BOLT, SOIL)
Lines 590-599:   Kz calculation function
Lines 601-607:   State variables and input helpers
Lines 609-652:   UI helper functions (radio, toggle, tabs)
Lines 654-691:   Presets (sign and foundation)
Lines 693-750:   Core calculations (calcWindPSF, calcShared)
Lines 752-843:   Bolt and foundation calculations
Lines 845-911:   SVG diagram generators
Lines 913-1047:  Tab renderers (section modulus with auto-feasibility)
Lines 1049-1153: Tab renderers (bolt, foundation)
Lines 1155-1217: Tab renderers (gusset, soil reference)
Lines 1219-1267: Prompt generator, copy, main calc loop, init
```

## Data Flow

```
User Input (sidebar)
    |
    v
calc() ──> calcShared() ──> lastCalc object (shared state)
    |           |
    |           |──> calcWindPSF() ──> PSF value
    |           |──> Section modulus calculation
    |           |──> Pipe/tube recommendation
    |           |──> autoBoltSize() ──> summary strip
    |           |──> autoSizeFound() ──> summary strip
    |
    |──> renderers[curTab]() ──> preview HTML
    |       |
    |       |── renderSection(): diagram + calc steps + auto-feasibility grid
    |       |── renderBolt(): bolt analysis + pipe/base plate info
    |       |── renderFoundation(): foundation diagram + safety factors
    |       |── renderGusset(): full pipe/gusset table
    |       |── renderSoil(): soil classification + bearing reference
    |
    |──> updatePrompt() ──> prompt text (always includes all data)
```

## State Management

### Global State
```javascript
curTab = 'section'    // active tab name
curCode = 'asce722'   // active building code
lastCalc = {}         // shared calculation results object
```

### lastCalc Object Shape
```javascript
{
  // Inputs
  W, H, GC, N,           // sign dimensions
  PSF,                    // wind pressure (calculated or direct)
  st,                     // steel condition: 'new' or 'used'
  shape,                  // column shape: 'pipe' or 'square'

  // Calculated
  area,                   // sign face area (sf)
  centroid,               // height to centroid (ft)
  perimeter,              // sign perimeter (ft)
  windForce,              // total wind force (lbs)
  forcePerCol,            // force per column (lbs)
  momentFtLb,             // moment per column (ft-lbs)
  momentInLb,             // moment per column (in-lbs)
  Fy,                     // yield stress (psi)
  Fallow,                 // allowable stress (psi)
  Sreq,                   // required section modulus (in^3)
  recPipe,                // recommended pipe object (from PIPE array)
  recSq,                  // recommended square tube object (from SQ array)
  pbf                     // perimeter-based force (lbs/ft)
}
```

## Data Arrays

### PIPE[] - 21 Schedule 40 Pipe Sizes
Each element:
```javascript
{
  nom,    // nominal size (inches): 2, 2.5, 3, ... 36
  od,     // outside diameter (inches)
  wall,   // wall thickness (inches)
  sm,     // section modulus (in^3)
  gLeg,   // gusset leg length (inches)
  gThk,   // gusset plate thickness (inches)
  weld    // fillet weld size (inches)
}
```

### SQ[] - 10 Square Tube Sizes
```javascript
{
  side,   // side dimension (inches): 2, 2.5, 3, ... 12
  wall,   // wall thickness (inches)
  sm      // section modulus (in^3)
}
```

### BOLT[] - 11 A307 Bolt Sizes
```javascript
{
  dia,    // diameter (inches): 0.5, 0.625, ... 3.0
  At,     // tensile stress area (in^2)
  lbl     // display label: '1/2"', '5/8"', etc.
}
```

### SOIL{} - 4 Soil Types
```javascript
{
  clay:   {v: 1000, l: 100},   // vertical PSF, lateral PSF
  sand:   {v: 1500, l: 150},
  gravel: {v: 2000, l: 200},
  rock:   {v: 2000, l: 400}
}
```

## Key Functions

### Input Helpers
- `v(id, fallback)` - read numeric input value by DOM id
- `rv(groupId)` - read active radio button value from group

### UI Functions
- `setRadio(btn)` - set active state on radio button group
- `toggleSection(id)` - collapse/expand sidebar section
- `toggleCodeDropdown()` - open/close code picker
- `setCode(code)` - switch building code, update UI, recalculate
- `preset(name)` / `fpreset(name)` - apply sign/foundation presets
- `setSoil()` - update soil values from dropdown selection

### Calculation Functions
- `calcWindPSF()` - returns wind pressure in PSF
- `getKz(h, exp)` - returns Kz coefficient for height and exposure
- `calcShared()` - master calculation, returns and stores `lastCalc`
- `calcBoltData()` - bolt analysis, returns bolt result object
- `calcFoundSized(fw, fd, ...)` - foundation check for specific dimensions
- `autoSizeFound(c)` - iterates to find minimum passing foundation
- `autoBoltSize(c)` - finds smallest A307 bolt for default pattern
- `calcFoundData()` - foundation analysis using current sidebar inputs

### Rendering Functions
- `svgSign(c)` - generates sign elevation SVG
- `svgFound(f, pipeOD)` - generates foundation cross-section SVG
- `renderSection()` - section modulus tab + auto-feasibility grid
- `renderBolt()` - anchor bolt tab
- `renderFoundation()` - foundation tab
- `renderGusset()` - gusset table tab
- `renderSoil()` - soil reference tab

### Output Functions
- `updatePrompt()` - generates text summary of all calculations
- `copyPrompt()` - copies prompt text to clipboard
- `toFrac(d)` - converts decimal to fractional inch string
- `sfCls(v, t)` - returns CSS class based on safety factor vs threshold

## CSS Architecture

### Theme Variables (CSS Custom Properties)
```css
--bg: #0c0e14          /* page background */
--surface: #141720     /* sidebar, header */
--surface2: #1c2030    /* input backgrounds */
--surface3: #242940    /* readonly inputs */
--border: #2a3050      /* subtle borders */
--border2: #3a4570     /* active borders */
--text: #e4e8f4        /* primary text */
--text2: #8890aa       /* secondary text */
--accent: #4a9eff      /* primary accent (blue) */
--green: #34d399       /* pass/success */
--orange: #f59e0b      /* warning */
--red: #ef4444         /* fail/error */
--purple: #a78bfa      /* formulas */
--cyan: #22d3ee        /* bolt section */
```

### Component Classes
- `.card` - result card container
- `.rrow` - result row (label + value)
- `.step` - calculation step row
- `.pipe-card` - column recommendation card
- `.eng-table` - engineering data table
- `.info-box` / `.warn-box` / `.formula-box` - information callouts
- `.rbtn` - radio button in toggle group
- `.preset` - preset button pill
- `.badge` - header badge (code, company)

## Event Handling
- All inputs have `oninput="calc()"` or `onchange="calc()"`
- Radio buttons: `onclick="setRadio(this);calc()"`
- Tab clicks: delegated listener on `#tabBar`
- Code dropdown: click-outside listener closes dropdown
- Presets: direct `onclick` to preset functions
