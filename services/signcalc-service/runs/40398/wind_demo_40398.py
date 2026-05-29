"""40398 ASCE 7-22 wind demo - SMALLEST real increment (Case A only).

STATUS: ???? DRAFT - UNREVIEWED - NOT a design, NOT canonical.
Purpose: prove the deliverable is one transparent script, not a 20-agent
program. Every coefficient is printed with its source/flag. Member,
baseplate, anchors, footing, Case B/C eccentricity = DEFERRED to the full
build. V legally-binding edition UNCONFIRMED (W1/AHJ) -> both 111 & 115 shown.
"""
from __future__ import annotations
import math, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# --- Geometry (VERIFIED from .CDR callouts, see CHECKPOINT-geometry.md) ---
B = 15 + 3/12      # overall width ft  = 15'-3"
s = 14 + 8/12      # overall height ft = 14'-8" (solid monument, full face)
h_top = s          # monument at grade -> top of sign height = s
z_centroid = s/2   # 7.333 ft

# --- Coefficients (each tagged) ---
Kzt = 1.0          # ASSUMED flat terrain (ASCE 7-22 26.8) - confirm W4
Kd  = 0.85         # ASCE 7-22 Tbl 26.6-1, signs - standard
G   = 0.85         # ASCE 7-22 26.11, rigid structure - standard
elev_ft = 1279.0   # VERIFIED ASCE Hazard Tool
Ke  = math.exp(-0.0000362 * elev_ft)   # ASCE 7-22 Eq for Ke (Tbl 26.9-1 basis)
# Kz: z<15ft -> use 15ft floor (ASCE 7-22 Tbl 26.10-1 note). Exp C, 15ft.
Kz  = 0.85         # ASSERTED per ASCE 7-22 Tbl 26.10-1 Exp C @15ft - cross-check vs official (Phase F)
z_used = max(z_centroid, 15.0)
# Cf: ASCE 7-22 Fig 29.3-1 solid freestanding sign. B/s, s/h:
Bs = B/s; sh = s/h_top
Cf = 1.70          # ASSERTED per Fig 29.3-1 (B/s~1.0, s/h~1.0) - cross-check vs official (Phase F)
As = B * s         # solid sign area sf

print("="*64)
print("40398 ST ANTHONY MONUMENT - ASCE 7-22 WIND (Case A) - ???? DRAFT")
print("="*64)
print(f"Geometry (.CDR-verified): B={B:.3f} ft  s={s:.3f} ft  As={As:.1f} sf")
print(f"  B/s={Bs:.3f}  s/h={sh:.3f}  z_used={z_used:.1f} ft (15ft floor)")
print(f"Coeffs: Kz={Kz} [ASSERTED]  Kzt={Kzt} [assumed]  Kd={Kd}  "
      f"Ke={Ke:.4f} (elev {elev_ft:.0f} ft)  G={G}  Cf={Cf} [ASSERTED]")
print("-"*64)
for label, V in (("ASCE 7-22/7-16 RC II [VERIFIED]", 111.0),
                 ("ASCE 7-10/AHJ band [UNVERIFIED-legally]", 115.0)):
    qz = 0.00256 * Kz * Kzt * Kd * Ke * V**2     # ASCE 7-22 Eq 26.10-1
    F  = qz * G * Cf * As                          # ASCE 7-22 Eq 29.3-1 (Case A)
    M  = F * z_centroid                            # base overturning, Case A
    print(f"V = {V:.0f} mph  [{label}]")
    print(f"  qz = 0.00256*Kz*Kzt*Kd*Ke*V^2      = {qz:8.2f} psf")
    print(f"  F  = qz*G*Cf*As                    = {F:9.1f} lbf")
    print(f"  M  = F * {z_centroid:.2f} ft (centroid)      = {M:11.1f} ft-lbf")
    print("-"*64)
print("DEFERRED (full build): Case B/C eccentricity+torsion, member sizing,")
print("baseplate, anchors, combined 2-pole footing+kern, frost, DXF, cost.")
print("ASSERTED coeffs (Kz,Cf) need official ASCE 7-22 cross-check (Phase F).")
print("V legally-binding edition UNCONFIRMED -> W1 + Carroll AHJ 712-792-1000.")
