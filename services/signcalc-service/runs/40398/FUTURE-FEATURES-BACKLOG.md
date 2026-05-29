# 40398 / SignCalc — Future / Optional Backlog (PARKED)

STATUS: ???? DRAFT. These are brain-dump items, deliberately PARKED so they
do not block the focused path. None are started. Pull into the plan only
after the base machine exists and Brady prioritizes.

## >>> FOCUSED CRITICAL PATH (do this; everything below is NOT this) <<<
1. W1: confirm LEGALLY-BINDING wind speed — Carroll AHJ adopted code edition
   (Iowa 2015 IBC -> ASCE 7-10 ~115? unverified) + AHJ call 712-792-1000.
2. First-principles ASCE 7-22 (and 7-10) base-machine calc for 40398:
   wind -> member -> baseplate/anchors -> combined 2-pole footing WITH
   kern/partial-bearing + frost; V-sensitivity 111/115/119.
3. Output as ???? DRAFT (handcalcs PDF). Nothing else gates this.

---

## PARKED — Verification oracles (after base machine)
- SkyCiv Load Generator + API — primary AUTOMATED oracle (ASCE 7-22 incl.
  freestanding signs). PAID (Pro or standalone Load Gen module). Brady-authed
  Chrome login OK. Cost gate before use.
- ClearCalcs / Calcs.com — manual second-opinion oracle, 14-day trial, no API.
- Hilti PROFIS Engineering — anchor-specific oracle, ties to ESR-3814
  (HIT-RE 500 V3). API access UNCONFIRMED.
- ABCENG (AbcEng.exe, owned) — legacy differential oracle; reverse-engineer
  its embedded tables AFTER base machine for cross-check (Phase F.5).

## PARKED — Independent physics / analysis
- PyNiteFEA 3D frame cross-check of the closed-form oracle (installed).
- anastruct 2D quick cross-check (installed).
- Autodesk Fusion FEA — manual spot-check only (not CI-able).
- sectionproperties — exact Ix/Sx vs table values (installed).

## PARKED — DFM / constructability (deepen Phase C.5)
- Auger max dia 24" hard constraint; excavator 2-3.5T / 4-6T site access;
  ready-mix truck + pump access; spoil/haul-off; US-30 traffic control.
- Collision / clash detection (pole vs cabinet frame vs footing vs utilities).
- Fab + install sequence modeling.

## PARKED — SOTA research spike
- State-of-the-art structural + AI libs / models / hybrids; "high-impact
  novelty" — explicitly AFTER the base machine per Brady.

## PARKED — Drawing / CAD automation
- ezdxf -> AutoCAD 2026 finish/PE stamp; Bluebeam permit-set assembly;
  CorelDRAW hatch (.pat) + draw_om OM integration for shop drawings.

## PARKED — Platform / agent infrastructure
- Custom agent + dashboard to replace Cowork.
- 20-agent orchestration topology (see ORCHESTRATION-PLAN.md).
- Embedded eval harness (Phase B), golden corpus (Phase C), standards
  corpus grounding (Phase F), code-edition-aware engine (Phase B.5),
  prior-work brief (Phase A: Trail Ridge / caisson / Donut).

## Misfires (ignore)
- Vercel MCP commands (explain_vercel_concept, optimize_deployment) fired
  empty/irrelevant to this project — noise, no action.
