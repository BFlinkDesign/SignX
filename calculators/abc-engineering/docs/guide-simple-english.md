# Sign Engineering Calculator — Simple English Guide

## What Is This Tool?

This is a calculator for sign companies and engineers. When you put up a big freestanding sign — like a pole sign at a gas station or a monument sign at a shopping center — you have to prove to the building department that the sign won't blow over in a windstorm.

This tool does all that math for you and tells you:
- What size steel pipe to use for the column
- How big the anchor bolts need to be
- How deep and wide to make the concrete foundation

---

## How to Use It

### Step 1 — Enter Your Sign Dimensions (left sidebar)

**Sign width** — how wide is the sign face? (feet)
**Sign height** — how tall is the sign face? (feet)
**Clearance** — how high above the ground is the bottom of the sign? (feet)
**Columns** — how many steel poles support the sign? (usually 1 or 2)

**Quick tip:** Use the preset buttons at the top of the sidebar to load common sign types:
- **Small** — 4'×4' on 6' clearance, single column
- **Medium** — 8'×4' on 8' clearance
- **Monument** — 6'×4' low to ground
- **Pole Sign** — 8'×6' on 18' clearance
- **Highway** — 12'×8' on 25' clearance
- **EMC** — 8'×6' electronic message center

### Step 2 — Check Your Wind Speed

The default is **115 mph** (correct for most of Iowa). If you're in a different area, enter the correct wind speed from your local building code or ASCE 7 wind map.

### Step 3 — Choose New or Used Steel

**New** = tighter allowable stress (0.66 × 36 ksi = 23.8 ksi)
**Used** = looser allowable stress (0.60 × 36 ksi = 21.6 ksi)

Use "New" for new construction. "Used" is for evaluating an existing sign.

### Step 4 — Read the Tabs

#### Section Modulus Tab (first tab)
This tells you **what size pipe** to use.

- The green box shows the recommended pipe size (e.g., "8" Sch 40")
- Below that is an auto-feasibility summary showing quick estimates for bolts, foundation, and gussets
- S_req is the "required section modulus" — a measure of how strong the pipe needs to be
- Higher S_req = bigger wind force = bigger pipe needed

#### Anchor Bolt Tab
This tells you **what size anchor bolts** to use.

Anchor bolts hold the base plate to the concrete foundation. They're in tension — wind tries to pull one side of the base plate up, and the bolts resist that.

- Default pattern: 2×2 (4 bolts) at 6" spacing
- The calculator finds the smallest A307 bolt that works
- A307 = common grade for sign anchor bolts (not high-strength)

#### Foundation Tab
This tells you **how big to make the concrete pier**.

You can pick:
- **Circular caisson** — a round hole filled with concrete (most common)
- **Square caisson** — square hole
- **Rectangular** — longer one direction

Three things must pass (safety factor ≥ 1.5 for each):
1. **Overturning** — the concrete must be heavy enough not to tip over
2. **Sliding** — the soil must grip the sides enough to resist horizontal force
3. **Bearing** — the soil at the bottom must support the weight

The "Auto-Min" feature finds the smallest caisson that passes all three checks.

**Foundation presets:**
- **Sm Caisson** — 24" dia × 6' deep (small signs)
- **Med Caisson** — 36" dia × 8' deep (medium signs)
- **Lg Square** — 4'×4' × 10' deep (large signs)
- **Spread** — 6'×6' × 4' deep (low monument signs)

#### Gusset Table Tab
This is a **reference table** showing what gusset plates to use with each pipe size.

Gussets are steel triangles welded at the base of the column to stiffen the connection to the base plate. The table shows:
- How long the gusset legs should be
- How thick the gusset plate should be
- What size fillet weld to use
- Minimum base plate size

The highlighted row is the pipe size recommended by the Section Modulus tab.

#### Soil Reference Tab
A reference table showing how much load different soil types can carry:

| Soil Type | How strong? |
|-----------|-------------|
| Clay | Weakest — 1,000 psf |
| Sand | Moderate — 1,500 psf |
| Gravel | Good — 2,000 psf |
| Rock | Best — 2,000 psf + strong lateral |

If you don't know your soil type, use Clay (most conservative). Use Gravel if you have a geotechnical report confirming good soil.

---

## The Summary Strip (Top of Screen)

The bar across the top always shows:
- **S_req** — required section modulus (in³)
- **Wind force** — total force on the sign (lbs)
- **Moment** — bending force at the base per column (ft-lbs)
- **Pipe** — recommended column size
- **Bolt** — recommended bolt size
- **Foundation** — recommended caisson size

This updates instantly as you change any input.

---

## The "Copy" Button

At the bottom of the screen is a text summary of all calculations. Click **Copy** to copy it to your clipboard. You can paste it into:
- An AI chat for further analysis or report writing
- A Word document for your engineering notes
- An email to a PE for review

---

## The Building Code Selector

The badge in the top-left (shows "ASCE 7-22" by default) lets you switch between four building codes:

| Code | Era | Use when |
|------|-----|----------|
| UBC 1997 | Pre-2000 | Old projects, some inspectors still reference this |
| ASCE 7-10 | 2012–2016 | Older permit submissions |
| ASCE 7-16 | 2016–2021 | Moderate vintage projects |
| ASCE 7-22 | Current | **Default — use this for new projects** |

Iowa has adopted IBC 2024 which uses ASCE 7-22.

---

## What This Tool Does NOT Do

This calculator gives you a structural engineering starting point. It does NOT:
- Generate permit-ready engineering documents (no PDF output yet)
- Apply ACI 318 concrete anchor bolt checks (breakout, pullout — coming later)
- Apply IBC 1807.3 embedded post formulas (more rigorous foundation method — coming later)
- Calculate for high-strength bolt grades (only A307 right now)
- Auto-lookup wind speed by zip code (you enter it manually)
- Provide construction drawings

For permit submission, a licensed PE must review and stamp the calculations.

---

## Quick Reference: Units

| What | Unit |
|------|------|
| Sign dimensions | Feet |
| Wind speed | MPH |
| Wind pressure | PSF (pounds per square foot) |
| Wind force | Lbs (pounds) |
| Moment | Ft-lbs (foot-pounds) |
| Section modulus | in³ (cubic inches) |
| Bolt tensile area | in² (square inches) |
| Foundation dimensions | Feet |
| Soil bearing | PSF |
| Stress | PSI or ksi (1 ksi = 1,000 psi) |

---

## Common Questions

**Why does the pipe recommendation sometimes jump two sizes?**
The calculator picks the FIRST pipe in the table whose section modulus meets S_req. Pipe sizes aren't evenly spaced — there can be a jump from, say, 6" (S=8.5) to 8" (S=16.8), skipping 7" (S=12.2) if S_req is 14.

**What if the foundation "Auto-Min" shows a very large caisson?**
It means the sign's overturning moment is very large relative to your soil capacity. Options:
- Use better soil (select Gravel instead of Clay)
- Use a spread footing (wider footprint)
- Reduce sign clearance height (lowers the moment arm)
- Use more columns (splits the force)

**Why are safety factors 1.5?**
That's the standard required by building codes for foundation overturning and sliding. It means the foundation has at least 50% more capacity than the expected force.

**What's the difference between S_req and S (section modulus)?**
- **S_req** = the minimum strength the column needs (calculated from your sign)
- **S** = the actual strength of the pipe (from the pipe table)
- The recommended pipe is the smallest pipe where S ≥ S_req

**What does "New" vs "Used" steel mean?**
New steel uses 0.66 × 36,000 psi = 23,760 psi allowable stress.
Used steel uses 0.60 × 36,000 psi = 21,600 psi allowable stress.
Used steel is more conservative — smaller allowable stress → higher S_req → larger pipe needed.
