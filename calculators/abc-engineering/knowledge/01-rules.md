---
id: SC-01
title: Engineering Rules
category: rules
version: 1.0
last_updated: 2026-04-17
---

# Engineering Rules — MUST / NEVER

These rules are invariants. Any code change that violates them is a regression.

## MUST

- **kc = 17 (cracked concrete):** ACI 318-19 Eq. 17.6.2.2b uses kc=17 for cracked normal-weight concrete (lambda=1.0). kc=24 applies only to uncracked concrete. Sign base plates are always in the cracked condition. Code ref: `_aci_conc_breakout_T()` line ~1533.

- **K = 2.0 (cantilever column):** Effective length factor for all freestanding sign columns. AISC 360-22 Table C-C2.2. Never use K=1.0 (pinned-pinned) or K=0.7 (fixed-pinned) for sign structures.

- **Iowa frost depth = 48 in (4.0 ft) minimum:** IBC Table 1809.7 frost protection depth for Iowa. Any foundation with fd < 4.0 ft must flag as FAIL regardless of soil capacity. Code ref: `checkFrostLine()`.

- **Passive resistance = triangular pressure:** IBC 2021 §1806.3.2. Soil lateral pressure is triangular (zero at surface, Sl×z at depth z). Total passive force = 0.5×Sl×fw×fd^2. Moment arm from base = fd/3. Never use rectangular pressure distribution for lateral bearing capacity.

- **W-shape LTB = AISC 360-22 §F2:** Lateral-torsional buckling uses full §F2 tri-linear curve: (1) plastic range Lb≤Lp: Fb=0.9Fy, (2) inelastic LTB Lp<Lb≤Lr: linear interpolation, (3) elastic LTB Lb>Lr: Fcr formula. Never use flat 0.66Fy for all Lb values.

- **Base plate bearing demand = uplift + DL (vertical):** AISC 360-22 §J8-2. The vertical compression demand on the base plate is the sum of uplift force and dead load. Never use wind shear (horizontal force) as the bearing demand.

- **CALC_VERSION in every PDF:** Every generated PDF must display the current CALC_VERSION constant. Hard-coding a version string in the PDF is prohibited.

## NEVER

- NEVER use kc=24 for sign foundation anchor design (uncracked assumption is non-conservative).
- NEVER use rectangular passive pressure distribution (triangular is correct per IBC 1806.3.2).
- NEVER flatten LTB to 0.66Fy for all unbraced lengths.
- NEVER compare base plate bearing capacity against horizontal wind shear.
- NEVER accept fd < 4.0 ft as passing in Iowa.
- NEVER hard-code 'v4.0' or any version string; always use CALC_VERSION.
- NEVER stamp or represent SignCalc output as a licensed PE calculation.
