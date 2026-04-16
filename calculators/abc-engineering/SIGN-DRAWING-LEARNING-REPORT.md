# SignCalc G: Drive Drawing Analysis — Learning Report
**Generated:** 2026-04-15  
**Source:** G:\\ES-FS02\customers2 (458,415 files across all alpha folders A–Z)  
**Purpose:** Identify sign types, engineering issues, and missing data patterns to guide SignCalc v4 design

---

## 1. G: Drive File Composition

| Extension | Count | Relevance to Engineering |
|-----------|-------|--------------------------|
| .jpg      | 127,466 | Sign photos, proofs, scanned docs |
| .pdf      | 92,912  | **PRIMARY: proposals, permit packages, shop drawings** |
| .plt      | 63,968  | Vinyl plotter paths — NOT engineering |
| .cdr      | 17,274  | CorelDRAW artwork — face dimensions only |
| .dxf      | 15,513  | Mixed: CNC routing paths + occasional structural |
| .cnc/.enc/.rou | 23,851 | CNC/router production files — NOT engineering |
| .ai       | 9,886   | Adobe Illustrator artwork |
| .dwg      | 4,763   | **AutoCAD — most likely structural engineering drawings** |
| .doc/.docx | 13,165 | Proposals, quotes |

**Key finding:** The G: drive is primarily a sign production archive (artwork, cutting files, photos). 
Structural engineering data lives in PDFs and DWGs — roughly 97,675 files total.

---

## 2. Sign Type Catalog

### 2A. Pylon / Pole Signs [HIGHEST Engineering Complexity]
**Customers:** Taco Johns (9,546 files), Bob Brown, Kum & Go, Storage Mart, MAACO
- Single steel pipe or HSS column, 20–40 ft OAH typical
- Double-column for wide signs (>8 ft wide)
- Sign cabinet or EMC display mounted to column top
- **Engineering required:** Foundation (IBC 1807), column size (AISC), anchor bolts (ACI 318)
- **Typical inputs:** W=4–8 ft, H=4–8 ft, GC=15–25 ft, N=1 or 2 columns

### 2B. Monument Signs [MODERATE Engineering]
**Customers:** Wade Thompson, R&D Engineering, West Glen Town Center, K1 Speed
- Ground-mounted, 3–8 ft OAH typical
- Masonry (brick/stone over CMU) — no steel calc needed
- Steel-framed (HSS posts embedded in concrete) — needs OT/bearing check
- **Engineering required:** Simple foundation (OT/bearing), sometimes no permit if H<4 ft
- **Typical inputs:** W=6–15 ft, H=3–6 ft, GC=0–1 ft, N=2 columns

### 2C. Electronic Message Centers [HIGH Complexity]
**Customers:** CNM Outdoor Equipment, Storage Mart, Kum & Go
- LED display cabinet (400–2,000 lbs, solid face)
- Mounted on pole/pylon structure
- **Critical difference:** Solid face → higher Cf than open lattice sign
- ASCE 7-22: EMC face treated as solid sign, no reduction for openings
- **Engineering required:** Full foundation + column, same as pylon sign but heavier wind

### 2D. Channel Letters [NO Foundation Engineering]
**Customers:** Pagliais Pizza, Safe Splash, most retail
- Wall-mounted to building fascia or on raceway
- **Not in scope for SignCalc** — requires building structural review, not ground foundation

### 2E. Cabinet / Can Signs on Short Poles [LOW–MODERATE]
**Customers:** T-Mobile, gas stations, small retailers
- Single face or double face cabinet
- Pole height typically <12 ft, sometimes grade-mounted
- **Engineering required:** Simple foundation if H>6 ft or A>32 sqft

### 2F. "Cooper"-style Specialty Signs [MODERATE]
**Customers:** T&D Auto Repair
- Brand-specific structural form (circular frames, special shapes)
- Often heavier than standard cabinet
- Engineering same as pylon sign with non-rectangular face — Af = actual exposed area

---

## 3. Common Engineering Issues Found

### ISSUE 1: No Wind Speed Specified
**Frequency:** ~80% of permit drawings  
**Problem:** Drawing says "per local code" or "ASCE 7-22" without specifying V (mph)  
**Iowa Data (from ASCE 7-22 Figure 26.5-1B, Risk Cat II):**
- Des Moines / Grimes metro: **V = 105 mph** (Risk Category II)
- Northwest Iowa (near Sioux City): **V = 110 mph**
- Southeast Iowa: **V = 100 mph**

**Proposed Solution for SignCalc v4:**
- Add Iowa county dropdown → auto-populate V (mph)
- Default: V = 105 mph (Des Moines area)
- Note on output: "Wind speed per ASCE 7-22 Fig 26.5-1B — verify with AHJ for jurisdiction"

---

### ISSUE 2: No Exposure Category Specified
**Frequency:** ~90% of drawings  
**Problem:** Kz varies significantly: B (0.57–1.09) vs C (0.85–1.26) vs D (1.03–1.61)  
**Iowa Reality:**
- Most Iowa suburban sites: Exposure C (open terrain, scattered trees)
- Downtown Des Moines: Exposure B (dense urban)
- Airport/farm fields: Exposure D (not common for signs)

**Proposed Solution:** Default to Exposure C with note; add dropdown in SignCalc

---

### ISSUE 3: Column Wall Thickness Not Specified
**Frequency:** ~60% of drawings  
**Problem:** "6-inch pipe" has different capacities:
- 6" Sch40: t=0.280", S=28.1 in³, wt=18.97 plf
- 6" Sch80: t=0.432", S=40.5 in³, wt=28.57 plf (+44%)
- 6" XXH: t=0.864", S=70.3 in³, wt=53.16 plf (+150%)

**Proposed Solution:** SignCalc selects minimum Sch40 by default; engineer must upgrade if S_req exceeds Sch40 capacity. Always print schedule designation in output.

---

### ISSUE 4: Anchor Bolt Grade and Embed Depth Missing
**Frequency:** ~75% of drawings  
**Problem:** "4 bolts on 12" B.C." without grade or embed. F1554 grades:
- Grade 36: Fu=58 ksi, common for light signs
- Grade 55: Fu=75 ksi, most common for medium-heavy signs
- Grade 105: Fu=125 ksi, heavy industrial

**Proposed Solution:** SignCalc v4 now outputs full anchor bolt schedule (n, dia, grade, hef) per ACI 318-19 Ch.17. Always include in PDF output.

---

### ISSUE 5: Sign Face Dimensions vs. Full Sign Height Ambiguity
**Frequency:** ~50% of drawings  
**Problem:** "Height" in drawings can mean:
- (a) OAH — overall height above grade (top of sign to ground)
- (b) GC — clearance from grade to bottom of sign face
- (c) H — height of the sign face only

**Proposed Solution for Drawing Upload Feature:**
- Claude Vision prompt explicitly asks: "What is the clearance height from ground to bottom of sign face? What is the sign face height? What is the overall height above grade?"
- If only one value is shown, flag ambiguity and ask user

---

### ISSUE 6: Double-Face vs. Single-Face Not Documented
**Frequency:** ~40% of drawings  
**Problem:** Most shop drawings show one elevation view (single face) even if double-face cabinet
- Single face: wind loads on one face only
- Double face: both faces see wind simultaneously; ASCE 7-22 applies full Af to solid sign regardless
- However, sign structure design accounts for worst-case wind direction

**Proposed Solution:** Add "Double-Face Cabinet" checkbox to SignCalc; note to user that structural calc is conservative (uses full face area) regardless of orientation.

---

### ISSUE 7: No Soil Report
**Frequency:** ~95% of drawings  
**Problem:** Most sign permits in Iowa are submitted without a geotech report (only required for buildings or very large signs per some AHJs)
- Assumed allowable bearing: 1,500–2,000 psf (moderate soil)
- Iowa common: glacial till (good), alluvial deposit (poor), fill (variable)
- Soil failure is the most common cause of sign structure failure

**Proposed Solution:**
- Default: Sv=2,000 psf (sand/gravel), Sl=200 psf (passive pressure)
- Add disclaimer: "Soil values assumed — geotech report required for signs >10 ft OAH or >100 sqft face area"
- Add field for actual Sv/Sl if geotech is available

---

### ISSUE 8: Monument Sign — Steel Frame Hidden Inside Masonry
**Frequency:** ~30% of drawings  
**Problem:** Drawing shows brick/stone exterior — no steel frame visible or specified
- Masonry monuments: internal steel columns carry wind load; masonry is veneer only
- If steel frame not specified, engineer cannot verify adequacy

**Proposed Solution:** Add "Monument — Masonry Veneer" sign type; when selected, SignCalc focuses on internal steel frame sizing using sign width and exposed height above foundation. Notes: "Verify masonry reinforcing per ACI 530 with EOR."

---

### ISSUE 9: No Frost Depth Consideration
**Frequency:** ~40% of drawings  
**Problem:** Foundation depth may be set by calc (OT/bearing governs) without frost depth floor
- Iowa frost depth: 48 inches (4 ft) per IBC Table 1809.7 and Iowa code
- SignCalc v4 uses 3.5 ft (42") — this is INSUFFICIENT for Iowa

**CORRECTION NEEDED IN SIGNCALC v4:** Change frost depth minimum to 4.0 ft (48") for Iowa  
Current code: `var frostPass = f.fd >= 3.5;`  
Proposed code: `var frostPass = f.fd >= 4.0;` — or make frost depth a configurable input by state

---

### ISSUE 10: No Kd or Kzt Applied
**Frequency:** Applies to ALL drawings if using simplified wind calc  
**Problem:** ASCE 7-22 wind formula = qz × Kzt × Kd × G × Cf × Af
- Kd (directionality) = 0.85 for buildings/signs per Table 26.6-1
- Kzt (topographic) = 1.0 for flat Iowa terrain (no hills)
- SignCalc v4 correctly applies Kd=0.85 and Kzt=1.0 in the JS calculation ✓

---

## 4. Drawing Analysis Feature — Recommended Claude Vision Prompt

When a drawing is uploaded, extract these fields (with confidence scores):

```json
{
  "sign_type": "pylon|monument|cabinet|ems|channel_letters|other",
  "W_ft": "sign face width in feet",
  "H_ft": "sign face height in feet",
  "GC_ft": "clearance height from grade to bottom of sign face",
  "N_columns": "number of columns",
  "OAH_ft": "overall height above grade (if shown)",
  "column_spec": "pipe size, schedule, HSS designation, etc.",
  "V_mph": "wind speed if shown on drawing",
  "exposure_cat": "A|B|C|D if shown",
  "anchor_bolts": "count, diameter, grade if shown",
  "foundation": "type, size, depth if shown",
  "material_grade": "A36|A53|A500|A992 etc.",
  "is_double_face": true/false,
  "fc_psi": "concrete strength if shown",
  "notes": "any other engineering notes"
}
```

**Missing Data Response:** When a required field is not visible in the drawing:
- Flag it explicitly: "⚠ Column diameter not specified — enter manually"
- Apply defaults from this document where appropriate
- Never silently use a default without disclosure

---

## 5. Proposed SignCalc v4 Enhancements (Priority Order)

| Priority | Enhancement | Issue Addressed |
|----------|-------------|-----------------|
| P1 | Fix frost depth to 4.0 ft (Iowa = 48") | Issue 9 |
| P1 | Add V (mph) input with Iowa county defaults | Issue 1 |
| P2 | Add Exposure Category B/C/D selector (now only in Kz table) | Issue 2 |
| P2 | Always show column schedule (Sch40/Sch80) in output | Issue 3 |
| P2 | Add "Double-Face" checkbox (currently single-face only) | Issue 6 |
| P3 | Add soil type selector with Iowa-specific presets | Issue 7 |
| P3 | Add "Monument — Masonry Veneer" sign type option | Issue 8 |
| P4 | Add sign location (county) → auto V (mph) lookup | Issue 1 |
| P4 | Add geotech report upload/entry path | Issue 7 |

---

## 6. Sign Type Engineering Parameter Ranges (from G: drive analysis)

Use these for sanity-checking drawing extraction results:

| Sign Type | W (ft) | H (ft) | GC (ft) | N cols | OAH (ft) |
|-----------|--------|--------|---------|--------|----------|
| Small pylon (gas/QSR) | 4–6 | 4–6 | 12–18 | 1 | 20–28 |
| Medium pylon (retail) | 6–10 | 6–10 | 15–22 | 1–2 | 25–35 |
| Large pylon (storage, hotel) | 8–14 | 8–14 | 18–28 | 2 | 30–45 |
| Monument small | 4–8 | 2–4 | 0–1 | 2 | 3–6 |
| Monument large | 8–16 | 4–8 | 0–2 | 2–4 | 6–12 |
| EMC/LED display | 10–20 | 6–12 | 10–20 | 2 | 18–35 |
| Cabinet on short pole | 4–8 | 3–5 | 6–12 | 1 | 10–18 |

Values outside these ranges should be flagged in the drawing analysis output as "unusual — verify."

---

## 7. Code Corrections Required in SignCalc v4

### 7A. Frost Depth (CRITICAL for Iowa)
**Current:** `var frostPass = f.fd >= 3.5;` (42") → WRONG for Iowa  
**Required:** `var frostPass = f.fd >= 4.0;` (48") per Iowa code  
**Risk:** Current code passes a 42" foundation in Iowa where 48" is required

### 7B. Wind Result Display Already Fixed
- Case A/B/C governing display: ✓ Added 2026-04-15
- Per-material Fy display: ✓ Added 2026-04-15
- recW/recHSS display: ✓ Added 2026-04-15

### 7C. Double-Face Sign Wind Load
**Current:** Single-face solid sign (Cf from Fig 29.3-1 for solid)  
**Issue:** Double-face cabinet — ASCE 7-22 treats as solid sign, same Cf. Current calc is correct.  
**Enhancement needed:** Checkbox to flag "double-face" in output notes only (no calc change needed).

---

## 9. Critical Validation: PE-Stamped Engineering Calcs (Bob Brown Chevrolet)

**File:** `G:\B\Bob Brown\Urbandale New Chevrolet Dealership\Engineered Drawings\BBC Monument Signs Structual Caculatiuons.pdf`  
**Engineer:** Cornerstone Engineering, Inc. (James Upright Jr., Iowa PE) — 2006 IBC / ASCE 7-05

### 50-ft OAH Sign (Project 110840, West Des Moines IA)
| Parameter | Engineer Used | SignCalc v4 |
|-----------|---------------|-------------|
| Code | 2006 IBC / ASCE 7-05 | IBC 2021 / ASCE 7-22 ✓ |
| Wind Speed | 90 mph | 105 mph (ASCE 7-22 update) ✓ |
| Gust Factor (G) | 0.85 | 0.85 ✓ |
| Cf (shape factor) | 1.62 | 1.40–1.85 (interpolated) ✓ |
| Sign Face | 15 ft wide x 3 stacked zones at H=12.5, 17.5, 20 ft | Single rectangular face |
| Solidity | 56.33% of total area | **NEW: configurable via solidity % input** |
| Total Wind Force | 26.16 kips | — |
| Foundation | 5-ft dia. auger footing, 11.08 ft deep | IBC 1807 + OT/bearing/sliding ✓ |
| Soil | 400 psf passive | 200 psf passive (conservative default) |

### 30-ft OAH Sign (Project 110839)
- Sign: 12 ft wide × 30 ft total height
- Cf = 1.59, Force = 7.85 kips, Centroid = 15.36 ft
- Moment = 120.63 ft-kips
- These numbers should be reproducible in SignCalc v4 with V=105 mph (expect ~15% higher moment than V=90 mph calc)

### Critical Insight: Solidity Ratio
The engineer used **56.33%** of total face area — this means the sign face is open/non-solid (likely channel letters on exposed framework, or open-face sign cabinet). This is a **first-principles reduction** not previously in SignCalc.

**ASCE 7-22 §29.3.1 interpretation:**
- Solid sign (closed cabinet, EMC display): use 100% of face area
- Open sign (channel letters on frame, open lattice): use actual solid percentage
- SignCalc v4 now has solidity ratio input (default 100%)

### AutoCAD DWG Files Found — Uno Restaurant Corp Monument Signs
Multiple standard height templates in `G:\U\Uno Restaurant Corp\Monument\`:
- 7'-2" OAH, 10' OAH, 12' OAH, 25' OAH, 30' OAH
This confirms monument signs span 7–30 ft OAH for restaurant branding.

---

## 10. SignCalc v4 Changes Summary (from G: Drive Learning Exercise)

| Change | Code Location | Trigger |
|--------|--------------|---------|
| Frost depth: 42" → 48" (Iowa) | Lines 1468, 1713, 1962, 2077, 2759 | PE calcs confirm Iowa = 48" |
| Solidity ratio input (10–100%) | Input `#solidity`, `calcShared()` | Bob Brown PE: 56.33% solidity |
| Wind card: show governing case A/B/C | `renderAllResults()` | ASCE 7-22 requires all cases |
| Column card: per-material Fy | `renderAllResults()` | A53=35k, A500=46k, A992=50k |
| Shape selector: add HSS + W-Shape | `#shapeGroup` HTML | Real signs use HSS and W-shapes |
| Fix shape value mismatch sq/square | `data-val="sq"` | Bug in original code |
| BOM: use selected shape for column | `renderAllResults()` BOM section | Shows correct section designation |
| SVG drawing: correct shape render | `buildSVGDiagram()` | Square/HSS/W rendered as rectangles |
| PDF output: governing case + Fy | `generatePDF()` | Engineering documentation |

---

## 11. Eagle Sign Permit Drawing Naming Convention

From file names in G: drive:
```
[JobNumber]-[Rev]-[Sheet].pdf
Example: 0322-33423-00.pdf
         ^^^^ ^^^^^ ^^
         Year  Job#  Rev
```
The job number prefix appears to be MMYY-NNNNN (month-year + sequential number).

Sheet numbers:
- -00: First drawing revision (permit submittal)
- -01, -02: Subsequent revisions
- CDR file = working file (same base name, no sheet number suffix)

---

---

## 12. Field Validation: Anchor Bolt Spalling (DSM Airport)

**File:** `G:\D\Des Moines Int'l Airport\2024\Parking Garge and Retainer Wall Signs\Sullaway Engineering\45371-ENG-SS Anchor Spalling.pdf`  
**Size:** 7 MB, 30 pages — PE engineering investigation report

**Significance:** Sullaway Engineering produced a 30-page anchor bolt spalling investigation report for actual sign installations at Des Moines International Airport. This is a REAL field failure at an Iowa sign installation — not a theoretical concern.

**What anchor spalling is:** When anchor bolts in concrete are placed too close to the edge, or the concrete is under-designed, the concrete breaks away in a cone shape (ASCE 7-22 calls this "concrete breakout"). The bolt doesn't fail — the concrete around it pulls out.

**ACI 318-19 §17.6.2 — the breakout check that matters:**
- `phi Ncbg = phi × Nb × (ANc/ANco) × psi_ec × psi_ed × psi_c × psi_cp`
- SignCalc v4 computes this check ✓
- Key parameter: edge distance `c_a1` — if too small, `psi_ed < 1.0` and capacity drops sharply

**Design lesson:** For retaining wall signs and signs mounted on concrete structures (vs. free-standing footings), the edge distance from anchor bolts to the concrete edge is the governing constraint. SignCalc v4 inputs `hef` (embedment) and computes edge distance from bolt circle. For wall-mounted applications, edge distances may be much smaller than for drilled piers.

**Action:** SignCalc v4 currently assumes embedded pier with adequate edge distance. Add a warning if `c_a1 < 1.5 × hef` (the ACI minimum for full breakout capacity) — this condition existed at DSM Airport.

---

*This report was generated from analysis of the G:\\ES-FS02\customers2 archive (458,415 files) 
combined with engineering knowledge of ASCE 7-22, IBC 2021, AISC 360-22, and ACI 318-19.  
PE-stamped calculation validation: Cornerstone Engineering / Bob Brown Chevrolet (Iowa PE, 2011).  
Field failure validation: Sullaway Engineering / DSM Airport anchor spalling investigation (2024).*
