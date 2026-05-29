# runs/40398/ - St. Anthony Regional Hospital Monument Sign Footing

**Status: ???? DRAFT - PRE-PE - NOT FOR PERMIT OR FABRICATION**
See `STATUS.md` for governance and `VERIFICATION-LEDGER.md` for evidence chain.

## Purpose

Preliminary first-principles structural engineering for the WO 40398 monument
sign foundation (Carroll IA, US Hwy 30, D/F monument with Watchfire 6mm DF EMC).
Computational ground truth for a licensed PE to review, revise, and seal.
NOT a stamped design.

## Quick start (Windows, Git Bash or PowerShell)

```
C:\Python313\python.exe -m pip install -r requirements.txt
C:\Python313\python.exe calc_40398.py
C:\Python313\python.exe -m pytest test_calc_40398.py -v --timeout=30 --timeout-method=thread
C:\Python313\python.exe make_drawing_40398.py
```

## Files

| File                            | Role                                                           |
|---------------------------------|----------------------------------------------------------------|
| `calc_40398.py`                 | First-principles ASCE 7-22 wind, AISC member, ACI/AISC anchor, combined 2-pole footing |
| `test_calc_40398.py`            | pytest suite - first-principles re-derivation + regression locks + integrity labels |
| `make_drawing_40398.py`         | ezdxf DRAFT foundation plan + section + title block - emits `40398_FOUNDATION_DRAFT.dxf` |
| `extract_cdr_geometry.py`       | CorelDRAW 2026 COM geometry extractor (one-shot; caches to JSON) |
| `derive_pole_spacing.py`        | Engineered-prelim pole spacing helper                          |
| `wind_demo_40398.py`            | Standalone wind probe (sanity tool)                            |
| `cdr_geometry_raw.json`         | Cached .CDR geometry (do not re-extract unless source changes) |
| `40398_FOUNDATION_DRAFT.dxf`    | Output of `make_drawing_40398.py` - 46 entities, PRELIMINARY    |
| `STATUS.md`                     | Governance rules (no completion claims, no fake data)          |
| `VERIFICATION-LEDGER.md`        | Evidence chain: VERIFIED vs REASONED vs NOT DONE               |
| `SITE-INPUTS.md`                | Wind sourcing + code-edition determination + DL provenance     |
| `ORCHESTRATION-PLAN.md`         | Reference to the broader 8-phase plan                          |
| `CHECKPOINT-geometry.md`        | Geometry extraction checkpoint                                 |
| `FUTURE-FEATURES-BACKLOG.md`    | Out-of-scope items                                             |

## What the calc computes

Inputs (locked / reasoned in `SITE-INPUTS.md` and `VERIFICATION-LEDGER.md`):

- Site: Carroll IA, lat 42.06511, lon -94.86661, elev 1279 ft
- Geometry: 15'-3" W x 14'-8" H envelope; cabinet 7'-5" H x 12'-3" W x 8" D; Watchfire 6mm DF
- Wind: V at three editions (ASCE 7-22 / 7-16 / 7-10) sourced from ASCE Hazard Tool
- Code edition: Iowa 2024 IBC -> ASCE 7-22 (V=111 mph floor); design at 115 mph (envelopes 111)
- Soil: IBC 1806.2 presumptive (sand class 1500 psf vert) - matches UBC 18-I-A per ABCENG (see install `_dev/ABCENG-MAP-2026-05-20.md`)

Outputs at V=111/115/119 mph:

- qz, design wind force F, base moment M
- Per-pole rational 2-pole couple (P=M/s, T_uplift, V_pole)
- Member check (8" Sch40 post, ASD bending)
- Anchor sizing (F1554 Gr 36, AISC 0.375*Fu)
- Combined-footing search (kern/middle-third, FS_OT >= 1.5, FS_SL >= 1.5)
- Deflection check (cantilever H/100 serviceability)

## Honest open items (BEFORE PE STAMP)

1. AHJ phone call - Carroll Building Dept 712-792-1000 (code edition, wind speed, PE-stamp requirement)
2. Watchfire 6mm DF EMC submittal weight (calc placeholder 1879 lb - UNVERIFIED)
3. Eagle fab takeoff for cabinet + pole weights (calc placeholders are ENGINEERING ESTIMATES)
4. ACI 318-19 Ch.17.6 concrete anchor breakout - DEFERRED to fresh session
5. Footing width 6.0 ft is arbitrary; ABCENG-style 50% ratio (~4.85 ft for L=9.7 ft) is closer to install practice
6. Frost 48" is ASSERTED, not verified against current Carroll/Iowa code
7. PE seal - legal act, human only

## Test coverage

20 tests (15 `def test_` + 5 parameterized expansions over V=[111,115,119]):
- wind first-principles re-derivation vs printed values (<1%)
- monotonicity in V (qz, F, M, smax)
- defect-fix #1 lock (anchor 0.375 Fu, not 0.33)
- defect-fix #2 lock (footing middle-third, e <= 0.75 kern)
- rational 2-pole mechanics (P = M / pole_spacing)
- deflection within H/100 limit
- integrity self-declaration labels present in output

"Tests pass" here means computational correctness + self-honesty, NOT design complete/safe/stamped.

## Related artifacts (this session, durable)

- `~/Desktop/40398_St_Anthony_ACTION_LIST.txt` - printable action list
- `~/Desktop/ABCEstimate-Full-NoDongle-NoSerial/_dev/ABCENG-MAP-2026-05-20.md` - legacy oracle cross-check
- `~/.claude/projects/C--WINDOWS-System32/memory/abceng-map.md` - cross-session memory
