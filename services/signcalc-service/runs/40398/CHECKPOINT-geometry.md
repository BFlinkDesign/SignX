# St. Anthony 40398 — Phase D Geometry Checkpoint

Source: `C:\Temp\AUTOBACKUP_OF_ST ANTHONY MON 7X12 6MM EMC 1125-40398 X.CDR`
Extractor: `extract_cdr_geometry.py` -> `cdr_geometry_raw.json` (1269 shapes, 95s)

## Verified envelope geometry (from the drawing's OWN dimension text)
| Item | Value | Source |
|---|---|---|
| Overall width | 15'-3" | CDR dim text (6 occurrences) |
| Overall height | 14'-8" | CDR dim text |
| Secondary height feature | 14'-5" | CDR dim text |
| Cabinet/EMC | 7'-5" H x 12'-3" W x 8" D | CDR spec text (verbatim) |
| Viewing area | 7' H x 12' W | CDR spec text |
| Structure/column-cover height | 12'-5" | CDR dim text |
| EMC | DF 6MM Full Color Watchfire | CDR spec text |
| Site | Carroll IA, E US Hwy 30, Risk Cat II (assumed) | CDR title text |

All envelope dims CORROBORATE the Cowork transcript. Cowork got the sign
envelope right; its errors were pole spacing + footing math.

## Key constraints discovered
1. Drawing is a SALES PROOF at photo scale 3/32" = 1' (stated on the drawing).
   Labeled dims = truth; raw shape coords = scaled artwork (NOT 1:1 inches).
2. **Pole spacing is NOT dimensioned** on this proof (internal structure).
   Must be DERIVED by scale-math from the 15'-3" reference + drawn
   column-cover shape separation. Not guessable, not customer-facing.

## Engine-grounding defects found in apex_signcalc (flag, not fix here)
- Kd applied twice: velocity_pressure() includes Kd (wind_asce7.py:273) AND
  wind_force_on_sign() multiplies F by Kd again (line 488). ~15% under-
  conservative wind force.
- Engine ignores real site wind speed: main.py:113 uses pack V_default_mph;
  SignDesignRequest has no V / risk-category->V mapping. Carroll IA design
  speed never enters the calc.
- Provenance mismatch: pack dir is "us.asce7-16" but wind_asce7.py is
  hardcoded ASCE 7-22 (Table 26.10-1 7-22 values). The standards_pack_sha256
  trace misrepresents the edition actually computed.

## Scale-math result (derive_pole_spacing.py)
- Cabinet outline scales CLEANLY and consistently: 147 pt = 12'-3" ->
  0.08333 ft/pt, exact aspect match (1.652). Envelope geometry VERIFIED.
- NO clean full-elevation reference shape; proof is a photo composite.
  Auto-detecting column-cover rects = inference -> REJECTED (that is the
  exact Cowork failure mode). Pole spacing NOT taken from the proof.

## REFINED SCOPE (Brady directive 2026-05-19)
"Use source of truth + industry/engineering best practice, grounded by
reality, NO guessing. There are NO shop drawings - we must CREATE them."

Therefore:
- Pole count / size / spacing / footing layout are DESIGNED OUTPUTS of the
  engine, governed by ASCE 7-22 + AISC 360 + ACI 318 + IBC + documented
  best-practice detailing rules (each rule evidence-tagged + cited).
- Creating the stamped-quality engineering drawing IS a deliverable.
- Sign loads / member sizing do NOT depend on pole spacing; foundation
  layout does. The combined two-pole footing (Cowork's failure) is
  designed correctly here incl. the kern / partial-bearing check.

## GROUNDED-DATA REQUIREMENTS (must be sourced, not assumed - no guessing)
| Input | Status | Source of truth |
|---|---|---|
| ASCE 7-22 basic wind speed V (Carroll IA site, exact lat/lon) | NEEDS SOURCING | ASCE 7 Hazard Tool / ASCE 7-22 maps by coordinates |
| Risk Category (freestanding sign on a HOSPITAL campus - sign itself typ. RC II, but verify) | NEEDS CONFIRM | ASCE 7-22 Table 1.5-1 + AHJ |
| Exposure Category (US Hwy 30 corridor - likely C, site judgment) | NEEDS CONFIRM | ASCE 7-22 26.7 + site recon |
| Ground elevation (for Ke, Carroll IA) | NEEDS SOURCING | USGS / geocode |
| Kzt topographic factor | likely 1.0 (flat) | confirm site |
| Component weights: Watchfire 6mm DF EMC, cabinet, poles | partial (EMC ~1,879 lb per transcript) | Watchfire spec sheet + Eagle fab |
| Allowable soil bearing / lateral (Carroll IA) | NEEDS SOURCING | geotech or IBC 1806 presumptive + cite |

## Next
1. Source the Carroll IA site wind parameters (geocode -> ASCE 7-22 V, Ke
   elevation; confirm exposure/risk). Flag any that need Brady/AHJ/geotech.
2. Build first-principles ASCE 7-22 oracle (wind -> member -> baseplate/
   anchors -> combined 2-pole footing w/ correct kern check) using the
   wind_asce7.py methodology (7-22, verified) but with SOURCED site inputs,
   NOT pack defaults. Best-practice pole-layout rule, cited.
3. Cross-check vs SignCalc-v4 (7-22) + ABCENG (old-edition ref) -> matrix.
4. Generate the engineering drawing (DXF) as the create-the-shop-drawing
   deliverable.
