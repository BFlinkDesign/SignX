# 40398 — Grounded Basis-of-Design Site Inputs

STATUS: ???? DRAFT — UNREVIEWED — PENDING BRADY APPROVAL.
Not a source of truth / not canonical. Inputs are SOURCED (cited), the
engineering conclusions built on them are not yet reviewed.

## Wind / site — SOURCE: official ASCE 7 Hazard Tool (ascehazardtool.org)
Retrieved 2026-05-19 via Brady-authorized headed Chrome session.

| Parameter | Value | Source |
|---|---|---|
| Site | St. Anthony Regional Hospital vicinity, US Hwy 30, Carroll IA | job drawing 1125-40398 |
| Latitude | 42.06511 | geopy/Nominatim "Carroll, Iowa" city |
| Longitude | -94.86661 | geopy/Nominatim |
| Standard | ASCE/SEI 7-22 | ASCE Hazard Tool (selected) |
| Risk Category | II | engineering judgment — freestanding commercial sign, not the hospital occupancy (ASCE 7-22 Tbl 1.5-1); CONFIRM with Brady/AHJ |
| Basic wind speed V | **111 mph** | ASCE Hazard Tool (authoritative) |
| Ground elevation | 1279 ft NAVD 88 | ASCE Hazard Tool (USGS earlier gave ~1254 ft county centroid; use 1279 ft at exact coord) |
| Exposure Category | NOT YET SET — likely C (US-30 open corridor) | NEEDS site-terrain confirm (Google Maps satellite) — do NOT assume |
| Kzt (topographic) | likely 1.0 (flat) | NEEDS site confirm |
| Ke (ground elev factor) | from 1279 ft -> ASCE 7-22 Tbl 26.9-1 (~0.96) | computed in calc, cited |

## Wind Details — full MRI table (ASCE Hazard Tool, ASCE 7-22 Fig 26.5-1B)
3-sec gust at 33 ft, Exposure C basis, non-hurricane region, linear contour interp.
| MRI | Vmph | Level | Risk Cat mapping |
|---|---|---|---|
| 10-yr | 76 | Service | - |
| 25-yr | 84 | Service | - |
| 50-yr | 89 | Service | - |
| 100-yr | 95 | Service | - |
| 300-yr | 104 | Ultimate | ~ RC I |
| **700-yr** | **111** | Ultimate | **RC II <- THIS SIGN** |
| 1,700-yr | 119 | Ultimate | RC III / IV |
| 3,000-yr | 123 | Ultimate | - |
Data source: ASCE/SEI 7-22 Fig 26.5-1B + Figs CC.2-1..4, Sec 26.5.2.

## 111 vs 115 — RESOLVED via code-edition history (Brady asked twice)
- ASCE 7-22 RC II at this exact site = **111 mph** (authoritative, verified).
- "115 mph" = the ASCE 7-16 / 7-10 era value (IBC 2015/2018). ASCE 7-22
  re-gridded the wind maps; central Iowa RC II dropped 115 -> 111.
- WHICH governs is the ADOPTED edition of the Carroll IA AHJ. If on IBC
  2018 (ASCE 7-16) -> 115 mph is legally required despite 7-22 saying 111.
  ACTION: verify Carroll/Iowa adopted code edition with AHJ. UNVERIFIED.
- AUTHORITATIVE, VERIFIED (ASCE Hazard Tool, this exact site, RC II):
  | Edition | V (RC II) | Data Source cited | Fig |
  |---|---|---|---|
  | ASCE 7-22 | 111 mph | ASCE/SEI 7-22 | 26.5-1B |
  | ASCE 7-16 | 111 mph | ASCE/SEI 7-16 | 26.5-1B |
  | **ASCE 7-10** | **115 mph** | ASCE/SEI 7-10 + errata 2014-03-12 | 26.5-1A |
  7-10 uses a DIFFERENT figure (26.5-1A) + distinct MRI (50-yr 90 vs 89;
  100-yr 96 vs 95) -> proven genuine 7-10 data, not stale.
- "115 mph" is DEFINITIVELY the ASCE 7-10 RC II value for this site
  (no longer reasoned — authoritatively grounded 2026-05-19).
- RETRACTED 2026-05-19: earlier "Iowa = 2015 IBC -> ASCE 7-10 -> 115
  legally binding" was from a WebSearch SUMMARY, NOT primary source.
  Brady (field experience) flagged metro = 2021->2024, not 2015. WRONG; corrected below.
- SOURCED (authoritative-domain search, URLs recorded):
  * Iowa adopted **2024 IBC** statewide (Iowa Admin Rule 481-280/301;
    Iowa Code 103A mandatory, >15k-pop may go stricter).
    src: dial.iowa.gov/contacts/state-building-code ;
    iccsafe.org/advocacy/adoptions-map/iowa/ ;
    legis.iowa.gov/docs/ico/chapter/103A.pdf
  * IBC->ASCE7: 2024 IBC -> ASCE 7-22; 2021 IBC -> ASCE 7-16;
    2015 IBC -> ASCE 7-10.
    src: iccsafe.org "Overview of Structural Changes to the 2024 IBC";
    codes.iccsafe.org/content/IBC2024P1/chapter-35-referenced-standards ;
    amplify.asce.org/ibc
- IMPLICATION: Iowa 2024 IBC -> ASCE 7-22 -> code-mandated V at this site
  RC II = **111 mph**. 115 mph = LEGACY ASCE 7-10 / 2012-2015-IBC value
  (why old permit forms/habit say 115; NOT the current Iowa requirement).
- Carroll-specific permit requirement + local amendments STILL = AHJ
  confirm (Carroll bldg official 712-792-1000). Only fully authoritative
  answer for this exact job. Iowa-2024 is state-level sourced, not the
  Carroll permit doc itself.

## ITEM #1 — DESIGN WIND SPEED
- Code-mandated floor (Iowa 2024 IBC / ASCE 7-22) = **111 mph**.
- Legacy / conservative carry value = **115 mph** (ASCE 7-10 era).
- RECOMMENDATION: design to **V = 115 mph** — it ENVELOPES the 111 code
  floor and any lingering 115-mph permit-form expectation; +7% wind load
  vs 111 ((115/111)^2). Run/report BOTH 111 and 115 (calc already does).
- Final V to lock = whatever the Carroll AHJ states on the permit;
  designing at 115 cannot be wrong (>= every edition's value).
Inputs: Exposure C, RC II, Kzt=1.0, ground elev 1279 ft.
- STANDARD-OF-CARE: design to conservative V = 115 mph until AHJ edition
  confirmed; document both 111 (7-22) and 115 (7-16) paths (code-edition-
  aware, exactly the engine discipline).

## DESIGN WIND SPEED DECISION (Brady Q: AHJ 115? move to RC III/119?)
- 111 and 115 are SAME basis (3-sec gust @33ft) - different map vintage.
  AHJ-adopted value is legally binding. Most AHJs cite 115 -> if Carroll
  AHJ cites 115, 115 governs, period. 115 >= 111 so it envelopes the ASCE
  point value too. Cost premium 115 vs 111 ~ (115/111)^2 = +7% wind load.
- RECOMMENDATION: design base case to **V = 115 mph**. ACTION: confirm
  Carroll IA AHJ stated design wind speed (city building dept / adopted
  code) - flagged, do not guess.
- RC III / V=119 is NOT code-required for this sign (RC II per Tbl 1.5-1).
  Voluntary RC III = (119/111)^2 = +15% wind load -> materially more
  steel/concrete/install. Only if owner wants robustness or AHJ requires.
  DECISION NEEDS COST ANALYSIS.
- BASE-MACHINE REQUIREMENT (added): engine must auto-output a V-sensitivity
  + material/cost table at V = 111 / 115 / 119 (and the governing RC each)
  so the design wind speed is an owner decision grounded in data, not a
  guess. This is a deliverable of the calc, not an afterthought.

## Soil Class "Default" (Brady asked)
ASCE tool "Soil Class" = seismic Site Class (ASCE 7 Ch.20). Default =
Site Class D (no geotech). IRRELEVANT to wind/footing — seismic does not
govern a small Iowa sign. Footing needs geotech bearing/lateral (IBC Tbl
1806.2 presumptive OR soils report) — separate outstanding grounded input.

## Why Risk Category II (Brady asked)
ASCE 7-22 Tbl 1.5-1: RC by consequence of THE SIGN's failure. Freestanding
commercial monument = RC II ("all other structures"). NOT RC IV from
hospital proximity (hospital bldg is RC IV; sign is independent, its
failure doesn't impair hospital function). RC I (ag/low life hazard) too
low for a sign over a public ROW w/ traffic. RC II defensible default;
CONFIRM AHJ. RC III would raise 7-22 V 111 -> 119.

## Cowork error grounded
Cowork used V = 105 mph (~ RC I value 104). Correct RC II = 111 mph.
qz proportional to V^2 -> (111/105)^2 = 1.117 -> Cowork ~12% LOW on
velocity pressure before its other (pole-spacing, footing) errors.

## Exposure C — partially grounded
ASCE Hazard Tool states its V basis is Exposure C. US-30 open corridor is
consistent with Exp C. Still confirm via Google Maps satellite (terrain
roughness within 1500 ft upwind), but C is the corroborated working value.

## Still-needed grounded inputs (no guessing)
- Exposure Category + Kzt: Google Maps satellite of the exact site (terrain
  roughness); user directed use of Maps/GIS/assessor.
- Component weights: Watchfire 6mm DF EMC + cabinet + poles (Watchfire
  submittal + Eagle fab) — for DL / overturning resistance / uplift.
- Soil bearing & lateral: geotech report OR cited IBC 1806 presumptive.
- Sign frontal area for wind: full monument envelope vs cabinet — set per
  ASCE 7-22 29.3 (solid sign area) in the calc, documented.

## Next
Confirm Exposure (Maps) -> build first-principles ASCE 7-22 base-machine
calc (wind -> member -> baseplate/anchors -> combined 2-pole footing w/
kern check) with handcalcs -> ???? DRAFT PDF. Pole layout = DESIGNED per
cited structural best practice (symmetric 2-post, equal-moment overhang,
within 18" cover envelope), not read/guessed.
