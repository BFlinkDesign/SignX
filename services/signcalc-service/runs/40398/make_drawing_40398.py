"""40398 St. Anthony monument foundation — DRAFT drawing generator (ezdxf).

STATUS: ???? DRAFT - PRELIMINARY - FOR PE REVIEW - NOT FOR CONSTRUCTION.
Geometry from grounded calc_40398.py @ V=115 mph (envelopes 111 code floor).
Pole spacing shown ENGINEERED-PRELIM (NOT read off the sales proof; not the
Cowork guess). Title block PE seal left BLANK for a licensed PE. Open items
listed as drawing notes. Units: inches. Output: 40398_FOUNDATION_DRAFT.dxf
"""
from __future__ import annotations
import ezdxf, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = Path(__file__).parent / "40398_FOUNDATION_DRAFT.dxf"

# --- grounded design @ V=115 (from calc_40398.py, Cf=1.45 ASCE7-22) ---
L_ft, B_ft, D_ft = 9.7, 6.0, 4.0          # footing L x W x depth
L, Bf, D = L_ft*12, B_ft*12, D_ft*12      # inches
pole_OD = 8.625                            # 8" Sch40
pole_spacing_ft = 7.0                      # ENGINEERED-PRELIM (symmetric 2-post)
ps = pole_spacing_ft*12
bp = 14.0                                  # baseplate ~14"x14" (prelim)
bolt_g = 9.0                               # anchor gauge (prelim)
frost = 48.0

doc = ezdxf.new("R2010"); msp = doc.modelspace()
doc.layers.add("OUTLINE", color=7); doc.layers.add("DIM", color=3)
doc.layers.add("TEXT", color=2); doc.layers.add("HID", color=1)
doc.layers.add("BANNER", color=1)


def rect(x, y, w, h, layer):
    msp.add_lwpolyline([(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)],
                        dxfattribs={"layer": layer})

def txt(s, x, y, hgt=2.0, layer="TEXT"):
    msp.add_text(s, dxfattribs={"layer": layer, "height": hgt}
                 ).set_placement((x, y))

# ---------- PLAN VIEW ----------
ox, oy = 0, 0
rect(ox, oy, L, Bf, "OUTLINE")                       # footing plan
txt("FOUNDATION PLAN", ox, oy+Bf+8, 4.0)
cx, cy = ox+L/2, oy+Bf/2
for sgn in (-1, 1):                                  # 2 poles + baseplates + bolts
    px = cx + sgn*ps/2
    msp.add_circle((px, cy), pole_OD/2, dxfattribs={"layer":"OUTLINE"})
    rect(px-bp/2, cy-bp/2, bp, bp, "HID")
    for dx in (-bolt_g/2, bolt_g/2):
        for dy in (-bolt_g/2, bolt_g/2):
            msp.add_circle((px+dx, cy+dy), 0.75,
                           dxfattribs={"layer":"OUTLINE"})
txt(f"2 POLES @ {pole_spacing_ft:.1f}' O.C. (ENGINEERED-PRELIM)",
    ox, oy-10, 2.2)
txt(f'FOOTING {L_ft:.1f}\' x {B_ft:.1f}\'  (PRELIM)', ox, oy-16, 2.2)

# ---------- SECTION ----------
sx, sy = 0, -160
msp.add_line((sx-20, sy+D), (sx+L+20, sy+D),
             dxfattribs={"layer":"HID"})              # grade line
txt("GRADE", sx+L+22, sy+D, 2.0)
rect(sx, sy, L, D, "OUTLINE")                         # footing section
msp.add_line((sx-20, sy+D-frost), (sx+L+20, sy+D-frost),
             dxfattribs={"layer":"HID"})
txt(f"FROST LINE ~{frost:.0f}\" (IOWA - VERIFY)", sx+L+22, sy+D-frost, 2.0)
for sgn in (-1, 1):                                   # pole stubs up
    px = sx+L/2 + sgn*ps/2
    rect(px-pole_OD/2, sy+D, pole_OD, 40, "OUTLINE")
txt("SECTION A-A", sx, sy+D+50, 4.0)
txt(f'DEPTH {D_ft:.1f}\'  f\'c=3000psi (PRELIM)  REBAR PER PE',
    sx, sy-12, 2.2)

# ---------- TITLE BLOCK ----------
tx, ty = 0, -260
rect(tx, ty, 260, 70, "OUTLINE")
txt("EAGLE SIGN CO  -  ST. ANTHONY REGIONAL HOSPITAL", tx+4, ty+60, 3.0)
txt("MONUMENT SIGN FOUNDATION - WO 40398 - CARROLL, IA (US HWY 30)",
    tx+4, ty+52, 2.2)
txt("DESIGN BASIS: ASCE 7-22, V=115 mph (envelopes 111 code floor),",
    tx+4, ty+44, 2.0)
txt("Exp C, RC II, Kzt=1.0; ACI/AISC; combined 2-pole spread footing.",
    tx+4, ty+38, 2.0)
txt("DRAWN: auto (calc_40398.py grounded)   DATE: 2026-05-19", tx+4,
    ty+30, 2.0)
rect(tx+185, ty+4, 70, 60, "OUTLINE")                 # BLANK PE SEAL
txt("P.E. SEAL", tx+205, ty+34, 3.0)
txt("(BLANK - licensed PE", tx+188, ty+20, 1.8)
txt(" to review + seal)", tx+190, ty+14, 1.8)

# ---------- PRELIMINARY BANNER + NOTES ----------
txt("P R E L I M I N A R Y   -   F O R   P E   R E V I E W   -   "
    "N O T   F O R   C O N S T R U C T I O N", -10, 120, 6.0, "BANNER")
notes = [
 "GENERAL NOTES (PRELIMINARY - NOT FOR CONSTRUCTION):",
 "1. Wind: ASCE 7-22 Fig 29.3-1, Cf=1.45 (s/h=1,B/s~1.04) GROUNDED.",
 "2. Iowa adopted 2024 IBC -> ASCE 7-22; V floor 111 mph; 115 used (cons).",
 "3. Soil: IBC 1806.2 presumptive 1500 psf (industry std, no geotech).",
 "4. OPEN / FOR PE: pole load-path (T/C couple) simplified; Case B",
 "   torsion not yet in footing/anchor design; ACI 318-17 concrete",
 "   breakout NOT done; deflection (AASHTO LTS) NOT done; Kz/DL/EMC",
 "   weights ASSERTED; pole spacing ENGINEERED-PRELIM.",
 "5. Verify code edition + wind w/ Carroll AHJ (712-792-1000).",
 "6. Licensed PE shall independently review, revise as required, seal.",
]
for i, n in enumerate(notes):
    txt(n, 300, 60 - i*7, 2.2)

doc.saveas(OUT)
print(f"OK wrote {OUT}  entities={len(msp)}")
