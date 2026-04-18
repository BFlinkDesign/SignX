---
id: SC-00
title: Charter
category: charter
version: 1.0
last_updated: 2026-04-17
---

# SignCalc Charter

## Scope

SignCalc-v4.html is an internal engineering estimate-prep tool for Eagle Sign & Design Inc. It is NOT a licensed PE-stamped engineering calculation tool and must NEVER be used as the sole basis for a permit submittal.

**Structural codes in scope:**
- Wind: ASCE 7-22 (default), ASCE 7-16, UBC 97 (legacy)
- Concrete anchors: ACI 318-19 Chapter 17
- Steel sections: AISC 360-22 (W-shapes, pipe, square HSS)
- Foundation sizing: IBC 2021 §1806.3.2 (lateral bearing, triangular pressure)

**Geographic scope:** Iowa sign structures. Iowa minimum frost depth = 48 in (4.0 ft). IBC Table 1809.7.

**Sign types in scope:**
- Freestanding monument and pole signs
- Single-column and multi-column configurations
- Foundation types: circular drilled pier, square pier, rectangular footing

## Non-Goals

- Stamped engineering calculations for permit
- Multi-story or building structures
- Seismic design (wind governs for Iowa signs)
- Retaining walls, spread footings for buildings
- Any structure outside Iowa without explicit code review

## Deployment Constraint

Single-file `file://` deployment. No ES modules, no build step, no npm. Portability IS the feature.
