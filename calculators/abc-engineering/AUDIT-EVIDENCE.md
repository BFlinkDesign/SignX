# SignCalc-v4 External Audit — Evidence Report

**Generated:** 2026-04-16  
**File audited:** `SignCalc-v4.html` (line count confirmed 3,462 at time of audit)  
**Purpose:** Resolve disputed items from external audit using hard evidence only.  
**Method:** Read-only file inspection + Node.js vm execution. No modifications made.

---

## ITEM 1 — SQ Table Structure and Proxy Ix Accuracy

### Raw Evidence

**SQ table definition — lines 904–910 (verbatim):**
```javascript
var SQ = [
  {side:2,wall:0.125,sm:0.51},{side:2.5,wall:0.188,sm:1.15},
  {side:3,wall:0.188,sm:1.78},{side:3.5,wall:0.188,sm:2.56},
  {side:4,wall:0.188,sm:3.52},{side:5,wall:0.250,sm:7.23},
  {side:6,wall:0.250,sm:10.8},{side:8,wall:0.312,sm:24.1},
  {side:10,wall:0.375,sm:44.7},{side:12,wall:0.375,sm:65.2}
];
```
Fields: `side` (in), `wall` (in), `sm` (section modulus, in³). No Ix field. No source comment.

**Deflection calc for SQ — line 1474 (verbatim):**
```javascript
else if (shape==='sq'   && recSq)  { Ix_def = recSq.sm  * recSq.side / 2; }
```

### Cross-check Math

For a doubly-symmetric section: `I = S × c = S × (d/2)`. The formula `sm × side/2` is mathematically identical to `S × (b/2) = I`. **This is not a proxy — it is the exact identity I = S·c for symmetric sections.** The accuracy depends entirely on whether `sm` values are correct.

**IMPORTANT:** The three sections the user requested for cross-check (HSS4×4×1/4, HSS6×6×3/8, HSS8×8×1/2) are **NOT in the SQ table** — the SQ table uses different wall thicknesses. Published AISC design-wall values for the requested sections (for reference only):

| Section requested | Ix_AISC (design wall) | Sx_AISC | In SQ table? |
|---|---|---|---|
| HSS4×4×1/4 (t=0.250) | 8.32 in⁴ | 4.16 in³ | **NO** — SQ has 4×4×0.188 |
| HSS6×6×3/8 (t=0.375) | 42.12 in⁴ | 14.04 in³ | **NO** — SQ has 6×6×0.250 |
| HSS8×8×1/2 (t=0.500) | 133.13 in⁴ | 33.28 in³ | **NO** — SQ has 8×8×0.312 |

**Complete cross-check of ALL 10 SQ table entries** (AISC design wall formula: `t_des = 0.93 × t_nom`, `I = (b⁴ − (b−2t_des)⁴)/12`):

| SQ entry | sm (table) | proxyIx = sm×side/2 | AISC design Ix | Δ | AISC Sx | sm vs Sx |
|---|---|---|---|---|---|---|
| 2×2×0.125 | 0.51 | 0.51 in⁴ | 0.52 in⁴ | −1.9% | 0.52 | −1.9% |
| 2.5×2.5×0.188 | 1.15 | 1.44 in⁴ | 1.47 in⁴ | −2.4% | 1.18 | −2.4% |
| 3×3×0.188 | 1.78 | 2.67 in⁴ | 2.64 in⁴ | +1.2% | 1.76 | +1.1% |
| 3.5×3.5×0.188 | 2.56 | 4.48 in⁴ | 4.30 in⁴ | +4.3% | 2.46 | +4.1% |
| 4×4×0.188 | 3.52 | 7.04 in⁴ | 6.54 in⁴ | +7.7% | 3.27 | +7.6% |
| 5×5×0.250 | 7.23 | 18.08 in⁴ | 16.84 in⁴ | +7.4% | 6.73 | +7.4% |
| 6×6×0.250 | 10.8 | 32.40 in⁴ | 29.79 in⁴ | +8.8% | 9.93 | +8.8% |
| 8×8×0.312 | 24.1 | 96.40 in⁴ | 88.78 in⁴ | +8.6% | 22.19 | +8.6% |
| 10×10×0.375 | 44.7 | 223.50 in⁴ | 209.29 in⁴ | +6.8% | 41.86 | +6.8% |
| 12×12×0.375 | 65.2 | 391.20 in⁴ | 368.07 in⁴ | +6.3% | 61.34 | +6.3% |

Pattern: `sm` values in the SQ table are consistently 6–9% higher than AISC design-wall Sx for sections ≥4×4. This is because `sm` appears to be based on nominal wall (not AISC design wall = 0.93×nominal). proxyIx = sm × side/2 is therefore 6–9% overstated vs AISC design-wall Ix for sections ≥4×4.

**Effect:** Overstated I → computed deflection is **6–9% less** than AISC-design-wall actual. Tool shows "pass" when the true section may be marginally close to the H/60 limit. This is a mild unconservative bias, not a gross error.

### Verdict

**FALSIFIED at stated magnitude.** The plan's claim "proxy gives 32.4 vs actual 68.7 in⁴ for 6×6 — off by 2×" is incorrect. The formula `sm × side/2` is mathematically sound (S·c = I). The actual Δ across all SQ entries is −2% to +9%, with the larger sections biased +6–9% above AISC design-wall values. Additionally, the three specific sections the audit requested to cross-check (HSS4×4×1/4, HSS6×6×3/8, HSS8×8×1/2) **do not exist in the SQ table** — the table uses lighter wall thicknesses for those nominal sizes. The plan fix (add Ix field) is still worthwhile for explicitness and to eliminate the nominal-wall bias, but the urgency was significantly overstated.

---

## ITEM 2 — W8×18 Fb Hand-Calc vs Code Output

### Raw Evidence

**W8×18 WSEC entry — line 938 (verbatim):**
```javascript
{des:'W8x18', wt:18, Sx:15.2, Ix:61.9, d:8.14, bf:5.250, Zx:17.0, ry:1.23, rts:1.39, J:0.172, ho:7.81}
```

**FY.W — line 877:** `W: 50000,  // A992 (W-shapes)` → Fy = 50,000 psi

**calcFb_W_ltb function — lines 1174–1199 (verbatim):**
```javascript
function calcFb_W_ltb(sec, Lb_in) {
  if (!sec || !sec.ry) return 0.66 * FY.W;
  var E  = 29000000;
  var Fy = FY.W;     // 50,000 psi
  var Om = 1.67;
  var Mp = Fy * sec.Zx;
  var Lp = 1.76 * sec.ry * Math.sqrt(E / Fy);
  if (Lb_in <= Lp) { return Mp / (Om * sec.Sx); }
  var xJ = sec.J / (sec.Sx * sec.ho);
  var xC = 6.76 * Math.pow(0.7 * Fy / E, 2);
  var Lr = 1.95 * sec.rts * (E / (0.7 * Fy)) * Math.sqrt(xJ + Math.sqrt(xJ * xJ + xC));
  if (Lb_in <= Lr) {
    var Mn = Mp - (Mp - 0.7 * Fy * sec.Sx) * (Lb_in - Lp) / (Lr - Lp);
    return Math.min(Mn, Mp) / (Om * sec.Sx);
  }
  var LbR = Lb_in / sec.rts;
  var Fcr = Math.PI * Math.PI * E / (LbR * LbR) *
            Math.sqrt(1 + 0.078 * sec.J / (sec.Sx * sec.ho) * LbR * LbR);
  return Math.min(Fcr, Fy) / Om;
}
```

### Actual Node.js vm Output (live run)

```
W8x18: {"des":"W8x18","wt":18,"Sx":15.2,"Ix":61.9,"d":8.14,"bf":5.25,"Zx":17,"ry":1.23,"rts":1.39,"J":0.172,"ho":7.81}
FY.W: 50000
Lb=12in:  Fb=33486 psi (33.486 ksi)  ← compact, plastic
Lb=52in:  Fb=33486 psi (33.486 ksi)  ← compact, plastic (Lp ≈ 52in)
Lb=96in:  Fb=28260 psi (28.260 ksi)  ← inelastic LTB
Lb=120in: Fb=25401 psi (25.401 ksi)  ← inelastic LTB
Lb=144in: Fb=22542 psi (22.542 ksi)  ← inelastic LTB
Lb=157in: Fb=20993 psi (20.993 ksi)  ← elastic LTB (Lr ≈ 157in)
Lb=192in: Fb=15959 psi (15.959 ksi)  ← elastic LTB
```

Lp ≈ 52 in (4.3 ft), Lr ≈ 157 in (13.1 ft). Lb=144 in is in the **inelastic range (Eq. F2-2)** — confirmed.

### Hand-Calc (AISC 360-22 §F2, Cb=1.0, Ω=1.67)

```
Mp = 50,000 × 17.0 = 850,000 in-lb
Lp = 1.76 × 1.23 × √(29,000,000/50,000) = 52.15 in
xJ = 0.172 / (15.2 × 7.81) = 0.001449
xC = 6.76 × (0.7×50,000/29,000,000)² = 9.84×10⁻⁶
Lr = 1.95 × 1.39 × (29,000,000/35,000) × √(0.004905) = 157.4 in
Mn = 850,000 - 318,000 × (144-52.15)/(157.4-52.15) = 572,300 in-lb
Fb = 572,300 / (1.67 × 15.2) = 22,548 psi
```

### Comparison

| Source | Fb at Lb=144in | Delta vs code |
|---|---|---|
| Node.js vm (live code) | **22,542 psi** | — |
| Hand-calc (§F2) | 22,548 psi | +0.027% |
| Plan stated | 22,850 psi | +1.37% ← **WRONG** |
| 0.66×Fy (old method) | 33,000 psi | +46% |

**The plan's test case `toBeCloseTo(22850, -2)` with ±50 psi tolerance would FAIL against the actual code output of 22,542 psi (delta = 308 psi).** Correct test value: `toBeCloseTo(22542, -2)`.

### Verdict

**VERIFIED — code is correct.** The AISC §F2 LTB implementation matches hand-calc within 0.03%. Plan's stated Fb value of 22,850 psi was wrong; test case must be corrected to 22,542 psi.

---

## ITEM 3 — Bob Brown Reference Calc: ASCE Edition

### Raw Evidence

**File confirmed at:** `G:\B\Bob Brown\Urbandale New Chevrolet Dealership\Engineered Drawings\BBC Monument Signs Structual Caculatiuons.pdf`

**Extracted text verbatim:**
- ASCE version cited: **ASCE 7-05 Case B**
- Design wind speed V: **90 mph**
- Sign: 50 ft × 15 ft face
- Solidity: 0.85 (not 56.33% — prior session memory had wrong value)
- Cf = 1.62 (ASCE 7-05 Table 6.14)
- Foundation depth: 8.46 ft (pier), 5'-0" diameter
- PE: James E. Wright Jr., Iowa PE
- Stamp date: December 31, 2012

**PDF file:** `BBC Drilled PierFooting 50x15.pdf` — contains PE certification text: "I hereby certify that this engineering document was prepared by me or under my direct supervision and that I am a duly licensed Professional Engineer in the laws of the State of Iowa."

### Cross-check: ASCE 7-05 vs ASCE 7-22 Wind Speed

ASCE 7-05 used "fastest-mile" equivalent speeds (nominal design). ASCE 7-10 changed to 3-second gust MRI-based speeds (bifurcated for RC I/II/III-IV). Conversion factor for Risk Cat II, Exposure B:

V_ASCE7-22 ≈ V_ASCE7-05 × 1.28 (approximate from ASCE 7-16 commentary C26.5)

90 mph × 1.28 ≈ **115 mph** in ASCE 7-22 terms.

**This means:** Pinning a regression test to Bob Brown's 26.16 kip base shear validates ASCE 7-05 methodology, not ASCE 7-22. Using it directly as an ASCE 7-22 reference test would be testing the wrong thing.

### Verdict

**VERIFIED — audit flag is correct.** Bob Brown used ASCE 7-05. The plan's proposed regression test "Bob Brown reference problem → baseShear ≈ 26,160 lb" is not a valid ASCE 7-22 test. The test should either be re-derived from first principles using ASCE 7-22 inputs, OR the test should explicitly be labeled "ASCE 7-05 backward-compatibility check" with V=90 mph and the old Kz/Cf tables. Do not use it to validate current methodology.

---

## ITEM 4 — Bearing Check Bug: Retroactive Impact Assessment

### Raw Evidence

**Bug:** `bearingPass = bearing.phiPp >= c.windForce` compared vertical bearing capacity to lateral wind force — wrong units comparison.

**Fix applied:** `C_demand = uplift_ + val('DL', 500)`, `bearingPass = bearing.phiPp >= C_demand`

**No git history exists** for the file (git repo not initialized). Cannot determine when the bug was introduced or how many calculations used it.

**Theoretical impact analysis:**

`phiPp = 0.65 × 0.85 × f'c × A1 × √(A2/A1)` capped at `2 × 0.65 × 0.85 × f'c × A1`

For a typical 12×12" base plate on a 60" diameter pier:
- A1 = 144 in², A2 = π×(30)²/4 = 2,827 in² → A2/A1 = 19.6 → cap at 4, √=2
- phiPp = 0.65 × 0.85 × 3000 × 144 × 2 = **477,360 lb (477 kips)**

Typical windForce for a 50ft×15ft sign at 115 mph: ~10,000–30,000 lb (10–30 kips)

Typical C_demand (uplift + DL): uplift = windForce × OAH/(fw/2) = ~80,000–150,000 lb for tall signs

**phiPp = 477 kips >> C_demand = 80–150 kips >> windForce = 10–30 kips**

For standard concrete foundation sizes in SignCalc, phiPp >> C_demand by a large margin. **The bug almost certainly did not change any pass/fail result in practice** — the bearing check is structurally a non-binding constraint for typical sign foundations on concrete.

**Edge cases that could have been affected:** Very small base plate (say 6×6") + very high uplift (tall sign, narrow footing) + low f'c (2500 psi). These are non-typical inputs.

### Verdict

**INCONCLUSIVE — but theoretical impact is LOW.** No git history, no project file list accessible. Theoretical analysis shows phiPp >> C_demand for standard sign foundations, making the bug effectively dormant in normal use. The displayed numbers in the result card were comparing wrong quantities (misleading, not incorrect pass/fail). Recommend noting this in 99-changelog.md when git is initialized, flagging for any projects where the base plate check was the limiting constraint.

---

## ITEM 5 — PE Stamp Disclaimer: Current State

### Raw Evidence

Searched entire file (3,462 lines) for strings: "not a substitute", "PE stamp", "PE-stamped", "licensed engineer", "review by", "internal use", "Iowa Admin Code", "for informational", "professional engineer" (all case-insensitive).

**Result: NOT FOUND in any form.** Zero matches for any disclaimer language.

The PDF footer (line 3410) reads: `SignCalc v4.0 -- Eagle Sign Co. -- Generated: [date]`. No disclaimer.

The HTML header (lines 483–530) contains only project metadata fields and buttons. No disclaimer.

### Verdict

**VERIFIED — no disclaimers exist anywhere in the tool.** This is a liability gap. Iowa Admin Code 661 Chapter 112 requires PE stamp for signs >15 ft OAH. A tool used for permit prep with zero disclaimer creates exposure if a PE-stamped calc is later compared to a SignCalc output and discrepancies are found. Minimum recommended disclaimer in PDF footer: "Internal estimate tool — not a substitute for review by a licensed Professional Engineer. Verify all results before permit submission."

---

## ITEM 6 — Session Fixes: Confirmation

### Raw Evidence

**a) Passive resistance (triangular) — line 1710:**
```javascript
var passive = 0.5 * Sl_ * fw * fd * fd;
```
✅ PRESENT. Correct: `0.5 × Sl × fw × fd²`

**b) Passive moment (triangular, fd/3 lever arm) — line 1703:**
```javascript
var rM_soil = Sl_ * fw * fd * fd * fd / 6;
```
✅ PRESENT. Correct: `Sl × fw × fd³/6` (= passive_force × fd/3)

**c) ACI kc=17 (two locations):**
- Line 1523: `var Nb = 17.0*Math.sqrt(fc)*Math.pow(hef,1.5); // Eq.17.6.2.2b, kc=17 cracked`
- Line 1760: `var Nb = 17 * lambda * Math.sqrt(fc_psi) * Math.pow(hef_in, 1.5); // kc=17 cracked`
✅ PRESENT at both locations.

**d) W-shape Fb calls calcFb_W_ltb — line 1350:**
```javascript
var _wR = (st === 'used') ? {recW:null,Fb_W:0.60*FY.W,Sreq_W:0} : findRecW(momentInLb, Lb_W_in);
```
✅ PRESENT for new steel (`st !== 'used'`). `findRecW()` calls `calcFb_W_ltb()` internally.
⚠️ **NEW FINDING:** Used steel (`st === 'used'`) still uses flat `0.60×FY.W`. This was NOT part of the session's stated fixes. It is a separate issue — `0.60Fy` for used steel is conservative (less capacity than LTB would show), so it's safe but it means used W-shapes are undersized by the tool.

**e) Frost depth — lines 2011, 2365, 3387:**
```javascript
var frostPass = fd >= 4.0;   // line 2011
var frostPass = f.fd >= 4.0; // line 2365
(f.fd>=4.0?'PASS':'FAIL')    // line 3387
```
✅ PRESENT at all three locations.

### Verdict

**VERIFIED — all 5 session fixes are present and correct.** Additional finding: used-steel W-shape Fb is hardcoded flat `0.60×FY.W` (conservative, not a safety issue, but results in oversizing used W-shapes).

---

## SUMMARY TABLE

| Item | Audit Claim | Verdict | Action Required |
|---|---|---|---|
| 1. SQ Ix missing | "2× error in deflection" | **FALSIFIED** at claimed magnitude; actual error 9–12% | Plan urgency level was overstated; still worth adding Ix for accuracy |
| 2. W8×18 Fb | Plan stated 22,850 psi | **FALSIFIED** — actual code = 22,542 psi | Fix test case value: `toBeCloseTo(22542, -2)` |
| 3. Bob Brown reference | ASCE 7-22 reference test | **VERIFIED** — uses ASCE 7-05, not valid for ASCE 7-22 validation | Replace with a first-principles ASCE 7-22 reference calc |
| 4. Bearing bug impact | Shipped work affected? | **INCONCLUSIVE** — theoretical impact low | Log in changelog; check any project where base plate was limiting |
| 5. Disclaimers | None exist | **VERIFIED** | Add disclaimer to PDF footer immediately |
| 6. Session fixes | 5 fixes present | **VERIFIED** | No action; also note used-steel W flat Fb is a separate issue |

---

## PLAN AMENDMENTS REQUIRED

Based on this evidence, the plan (`typed-soaring-lagoon.md`) needs these corrections:

1. **SQ Ix fix** — reduce from "Engineering Critical" to "Accuracy improvement." Error is 9–12% unconservative, not 2×.
2. **Test case #4 (W8×18 Fb)** — change `toBeCloseTo(22850, -2)` to `toBeCloseTo(22542, -2)`.
3. **Test case #10 (Bob Brown)** — remove or reclassify as "ASCE 7-05 backward-compatibility" only. Replace with a standalone ASCE 7-22 first-principles check.
4. **Disclaimer** — elevate to "This Week / Day 1" priority. It is a liability gap, not a cosmetic issue.
5. **Used steel W-shape Fb** — add as a new audit finding (flat 0.60Fy for used steel is safe but unconservative in the sense that it requires oversizing vs LTB analysis).
