# 40398 / SignCalc — Orchestration Plan (run in a FRESH session)

STATUS: ???? DRAFT. Governance rule (runs/40398/STATUS.md) binds all agents:
no output is "source of truth / canonical / validated" until Brady approves;
NO GUESSING — every number cited to an authoritative source.

## Why a fresh session
Subagents fail to spawn in the current session (context overflow — proven
repeatedly). Start a new Claude Code session; it inherits a small context
and can fan out. ALL state is durable on disk (see "Resume inputs").

## Control roles (4)
- ORCHESTRATOR/ROUTER (1): owns the DAG below, assigns workers, enforces
  gates, does NO engineering itself.
- WATCHER (1): monitors for drift / rabbit-holes / scope-creep (the failure
  mode that consumed the prior session); enforces ???? DRAFT + no-guessing.
- ADVISOR (1): stronger-model review BEFORE the wind-oracle approach is
  committed and BEFORE the report ships.
- REVIEWER (1): independent verification of each deliverable vs acceptance
  criteria; nothing marked done without a reviewer pass.

## Workers (<=16; total agents <=20)
W1 researcher — AHJ/code edition: Iowa State Bldg Code = 2015 IBC (Iowa Admin
   Rule 661-201/301); 2015 IBC references ASCE 7-10 -> THAT is the 115 mph
   origin and likely the LEGALLY BINDING basis for Carroll. Confirm Carroll
   adoption + get ASCE 7-10 RC II V for site. AHJ: Carroll Bldg Dept
   712-792-1000.
W2 researcher — Watchfire 6mm DF EMC weight/EPA/power (verify ~1,879 lb) +
   cabinet/pole weights, cited.
W3 researcher — IBC 1806.2 presumptive soil bearing/lateral (2015 + 2018/21),
   transcribed + cited.
W4 vision/browser — Exposure Category confirm via Google Maps satellite of
   the exact site (terrain roughness 1500 ft upwind).
W5 explore — Prior-work brief: Trail Ridge / caisson / Donut JSONs + hatch
   .pat + draw_om -> docs/PRIOR-WORK-BRIEF.md (note SketchUp-MCP gap).
W6 python-expert — FIRST-PRINCIPLES wind oracle (ASCE 7-22 AND 7-10 paths;
   V=111/115/119). CRITICAL PATH. Advisor-gated before commit.
W7 executor-high — Member sizing (pipe/HSS, AISC 360-22, sectionproperties).
W8 executor-high — Baseplate + anchors (AISC DG1 + ACI 318-19 Ch.17).
W9 executor-high — Combined 2-pole footing: kern/partial-bearing + Broms
   lateral + frost (THE Cowork failure — get this right).
W10 executor — Pole-layout best-practice rule (equal-moment overhang within
    the 18" cover envelope), cited; NOT read off the proof.
W11 executor — handcalcs report -> ???? DRAFT PDF incl. V=111/115/119
    sensitivity + material/cost table.
W12 executor — Engineering DXF (ezdxf) -> draft shop drawing.
W13 build-fixer — Fix apex_signcalc dead wind path (velocity_pressure()
    TypeError: missing Ke) once W6 defines correct form.
W14 executor — Embedded eval-harness skeleton (Phase B) + golden schema.
W15 researcher/executor — ASCE 7-22 pack (Phase B.5) grounded vs official.
W16 explore — Standards corpus grounding (Phase F) from on-disk docs.

## DAG / routing
- Parallel now: W1 W2 W3 W4 W5 W16.
- W6 (advisor-gated) -> then W7 W8 W9 W14 W15 in parallel; W10 -> W9.
- W11 <- {W6 W7 W8 W9 W10 + W1/W2/W3 inputs}. W12 <- {W9 W10}.
- W13 <- W6. Reviewer gates each Wn. Advisor before W6 commit + before W11 ship.

## Acceptance (Phase E)
pytest green incl evals; determinism; oracle = first-principles ASCE 7-22
(engines = evidence under own edition, cross-engine = diagnostic only);
no cross-edition number compares; DFM/equipment gate non-empty;
V-sensitivity table present; ???? DRAFT banner on every output.

## Resume inputs (durable, read these first in the fresh session)
- Plan: C:\Users\Brady.EAGLE\.claude\plans\source-all-the-data-jiggly-kitten.md
- runs/40398/: SITE-INPUTS.md (grounded V=111 7-22&7-16, 115=7-10 origin,
  design rec V=115, RC II rationale), CHECKPOINT-geometry.md,
  cdr_geometry_raw.json, STATUS.md (governance), extract_cdr_geometry.py
- docs/TOOLCHAIN.md, apex_signcalc/standards/* , ON-DISK-SCAN.md
- Tasks #1-8 already created. Engine: apex_signcalc wind path is DEAD
  (velocity_pressure TypeError) — base machine = clean first principles.
- Key grounded fact: 2015 IBC -> ASCE 7-10; if Carroll is on the Iowa
  state code, ~115 mph (ASCE 7-10) is likely LEGALLY BINDING, not 111.
  W1 must confirm. Design base case V=115 (envelopes 111).
