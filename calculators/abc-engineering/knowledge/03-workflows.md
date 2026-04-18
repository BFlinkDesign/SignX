---
id: SC-03
title: Development Workflows
category: workflows
version: 1.0
last_updated: 2026-04-17
---

# Development Workflows

## How to Add a New Section Type

1. Add a row to the appropriate data table (`_WSEC_TABLE`, `_PIPE_TABLE`, or `_SQ_TABLE`) near line 880.
   - W-shapes: `{ d, bf, tf, tw, Ix, Sx, rx, ry, rts, ho, J, Cw, weight }` (all AISC 16th Ed. Table 1-1 values)
   - Pipe: `{ od, t, S, I, weight }` (AISC 16th Ed. Table 1-14)
   - Square HSS: `{ side, sm, Ix, weight }` (AISC 16th Ed. Table 1-11 — include Ix explicitly)
2. Source values from AISC 16th Edition tables only. Do NOT transcribe from memory.
3. Write a test in `SignCalc-tests.js` verifying the new section's capacity is greater than a smaller adjacent section (monotonicity invariant).
4. Update `knowledge/02-constants.md` with the source citation.
5. Commit with prefix: `AISC-T1-1:` or `AISC-T1-11:` etc.

## How to Update Wind Tables (Kz)

1. Open `_KZ_TABLE` near line 942.
2. Source values from the relevant ASCE 7 edition Table 26.10-1. Note the edition in a comment above the table.
3. If changing ASCE edition, increment CALC_VERSION minor (x.Y.0) — numeric output changes.
4. Update `knowledge/02-constants.md` source citation.
5. Add an entry to `knowledge/99-changelog.md`.

## How to Fix an Engineering Formula

**Protocol (mandatory):**
1. Write a failing test in `SignCalc-tests.js` that reproduces the wrong answer.
2. Run `node SignCalc-tests.js` — confirm the test fails.
3. Fix the formula in `SignCalc-v4.html`.
4. Run `node SignCalc-tests.js` — confirm the test now passes, all others still pass.
5. Increment CALC_VERSION minor (formula change = numeric output change).
6. Add entry to `knowledge/99-changelog.md` with: code ref, date, what changed, why, what was wrong before.
7. Commit with relevant code prefix (e.g. `ACI-17:`, `AISC-F2:`, `IBC-1806:`).

## Commit Message Prefixes

| Prefix | Meaning |
|--------|---------|
| `ACI-17:` | ACI 318-19 Chapter 17 anchor design |
| `AISC-F2:` | AISC 360-22 §F2 LTB |
| `AISC-J8:` | AISC 360-22 §J8 base plate bearing |
| `IBC-1806:` | IBC §1806.3 foundation lateral bearing |
| `IBC-1809:` | IBC §1809 frost depth |
| `ASCE7-26:` | ASCE 7-22 Chapter 26 wind |
| `ASCE7-29:` | ASCE 7-22 Chapter 29 signs/solid surfaces |
| `UI:` | UI/display only, no numeric change |
| `DATA:` | Section property data entry, no formula change |

## CALC_VERSION Semver Convention

- Major (`5.0.0`): New referenced standard adopted (e.g., ASCE 7-28, ACI 318-22)
- Minor (`4.2.0`): Formula correction, new calc module, any numeric output change
- Patch (`4.1.1`): UI/display changes, label fixes, data corrections that don't change results

## Running Tests

```
node SignCalc-tests.js
```

No installation required. Uses Node.js built-in `vm` module. All 9 active tests must pass before any commit that changes formulas or data tables.
