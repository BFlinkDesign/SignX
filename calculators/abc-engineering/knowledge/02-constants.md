---
id: SC-02
title: Constants and Table Sources
category: constants
version: 1.0
last_updated: 2026-04-17
---

# Constants and Table Sources

All numeric constants must be traceable to a published standard. If a constant has no citation here, add one before using it.

## Steel Yield Strengths (Fy)

| Material | Fy (psi) | Standard | Variable |
|----------|----------|----------|----------|
| Pipe (Schedule 40) | 35,000 | ASTM A53 Gr B | `FY.PIPE` |
| Square/Rect HSS | 46,000 | ASTM A500 Gr C | `FY.SQ` |
| W-shapes | 50,000 | ASTM A992 | `FY.W` |
| Plate / angle | 36,000 | ASTM A36 | `FY.PLATE` |

Source: AISC 16th Edition Table 2-4 (preferred materials for structural steel).

## ACI 318-19 Anchor Design Constants

| Constant | Value | Meaning | Code Ref |
|----------|-------|---------|----------|
| kc | 17 | Breakout factor, cracked NW concrete | §17.6.2.2b Eq.17.6.2.2b |
| phi_ct | 0.70 | Concrete tension phi factor | §17.5.3(a) |
| phi_st | 0.75 | Steel tension phi factor | §17.5.3 |
| lambda | 1.0 | NW concrete modification factor | §17.6.2.2b |

## Velocity Pressure Coefficients (Kz) — ASCE 7-22 Table 26.10-1

Source: ASCE 7-22 Table 26.10-1. Values interpolated linearly between table heights.
Exposure categories: B, C, D. Default = C.

Key values (Exposure C):
- h=15 ft → Kz=0.85, h=20→0.90, h=25→0.94, h=30→0.98, h=40→1.04, h=50→1.09

## Force Coefficient (Cf) — ASCE 7-22 Figure 29.3-1

Solid/total area ratio governs Cf. Values range 1.3 (low solidity) to 1.8 (solid flat surface).
Auto-Cf uses linear interpolation between ratio breakpoints.
Source: ASCE 7-22 Figure 29.3-1 (Signs, freestanding walls, solid signs).

## Iowa Frost Depth

- Minimum: 48 in (4.0 ft)
- Source: IBC 2021 Table 1809.7 (Iowa)
- Variable: `FROST_DEPTH_FT` (TODO: extract to named constant per Phase 1 backlog)

## AISC Section Properties Sources

- W-shapes: AISC 16th Edition Table 1-1 (Sx, Ix, ry, rts, ho, J, Cw)
- Pipe: AISC 16th Edition Table 1-14 (S, I, OD, t)
- Square HSS: AISC 16th Edition Table 1-11 (S, I — NOTE: Ix field currently absent from SQ table, using proxy; see BACKLOG.md)

## Wind Speed Map

Default Vmph=115 corresponds to ASCE 7-22 Risk Category II basic wind speed for central Iowa.
Verify project location against Figure 26.5-1D before using default.
