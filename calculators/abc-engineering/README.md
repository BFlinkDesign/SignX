# SignCalc

Structural engineering calculator for sign permits at Eagle Sign Co.
(subsidiary of Nagle Sign Co.).

**Status:** v4.1.0-wip (Phase 1 - trust foundation in progress)

## Usage

Open `SignCalc-v4.html` in a modern browser. No installation, no build
step, no network dependencies for the calculation engine. Drawing
analysis feature requires an Anthropic API key.

## Scope

Internal estimate-prep and PE-prep tool. **Not a stamped engineering
calculation.** Structures requiring a Professional Engineer stamp
under Iowa Administrative Code 661 Chapter 112 require independent
review and stamp by a licensed Professional Engineer prior to
fabrication or installation.

## Reference codes

- ASCE 7-22 (wind loads)
- IBC 2024 (foundation design)
- AISC 360-22 (steel design, 16th Edition section properties)
- ACI 318-19 (concrete anchor design, Chapter 17)
- Iowa IBC Table 1809.7 (48-inch frost depth minimum)

## Materials (default)

Steel:
- A500 Gr C (HSS round / square tube): Fy = 46 ksi
- A53 Gr B (Sch 40 pipe): Fy = 35 ksi
- A992 (W-shapes): Fy = 50 ksi
- A36 (plates, general): Fy = 36 ksi

Concrete: f'c = 3000 psi (default), cracked concrete design per ACI 17.6

Anchors: F1554 Gr 36 (default)

## Repository structure
.
├── SignCalc-v4.html              # The application (canonical)
├── AUDIT-EVIDENCE.md             # Engineering corrections audit trail
├── knowledge/                    # Phase 1 scaffolding (project-guardian pattern)
├── docs/                         # Development docs, roadmap, formulas
│   └── audits/                   # Prior audit reports (historical)
├── legacy/                       # Archived artifacts
│   ├── sign-engineering-calculator-v3.html  # v3 snapshot
│   ├── chm_help/                 # AbcENG CHM help (Phase 2 reference)
│   ├── database/                 # AbcENG schema exports (structure only)
│   └── signcalc.nsi              # v2.0 NSIS installer (historical)
└── README.md                     # This file

## Roadmap

See `docs/roadmap.md` for phase planning. Current work is Phase 1
(trust foundation - disclaimers, version control, regression tests).
Phase 2 (AbcENG-replacement UX) and Phase 3 (PE-ready output +
drawing analysis) queued in `knowledge/BACKLOG.md`.

## Engineering changes

All engineering changes logged in `knowledge/99-changelog.md` with
code section, reason, and verification. `AUDIT-EVIDENCE.md` is the
authoritative record of corrections made during the v3->v4 transition.

## License / ownership

Internal tool. Ownership / governance between Eagle Sign Co. and Nagle
Sign Co. TBD - see `knowledge/BACKLOG.md` governance section.
