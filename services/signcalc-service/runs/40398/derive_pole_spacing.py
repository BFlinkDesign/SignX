"""Derive St. Anthony 40398 pole spacing by scale-math from the .CDR proof.

Photo-scale sales proof => labeled dims are truth, shape coords are scaled
artwork. Method: establish pt->ft scale from an identifiable reference whose
REAL size is known from the drawing's own callouts, then measure the two
column-cover shapes' centerline separation. Prints ALL candidates + the
chosen reference + cross-checks so the result is auditable, not asserted.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

J = Path(__file__).parent / "cdr_geometry_raw.json"
data = json.loads(J.read_text(encoding="utf-8"))
shapes = [s for s in data["shapes"]
          if s.get("w_in") and s.get("h_in") and s["w_in"] > 1 and s["h_in"] > 1]

OAW_FT = 15 + 3 / 12.0      # 15'-3" overall width
OAH_FT = 14 + 8 / 12.0      # 14'-8" overall height
CAB_W_FT = 12 + 3 / 12.0    # 12'-3" cabinet width
CAB_H_FT = 7 + 5 / 12.0     # 7'-5"  cabinet height
COVER_W_FT = 18 / 12.0      # 18" column cover (transcript)


def cx(s):  # center x
    return s["x_in"] + s["w_in"] / 2.0


def cy(s):
    return s["y_in"] + s["h_in"] / 2.0


print("=== scale reference candidates (aspect ~ OAW/OAH = %.3f) ===" % (OAW_FT / OAH_FT))
ref_cands = []
for s in shapes:
    ar = s["w_in"] / s["h_in"]
    if 0.95 <= ar <= 1.15 and min(s["w_in"], s["h_in"]) > 40:
        scale = OAW_FT / s["w_in"]              # ft per pt
        h_check_ft = s["h_in"] * scale
        err = abs(h_check_ft - OAH_FT) / OAH_FT
        ref_cands.append((err, s, scale, h_check_ft))
ref_cands.sort(key=lambda r: r[0])
for err, s, scale, hck in ref_cands[:8]:
    print(f"  ar=%.3f w=%.1f h=%.1f -> scale=%.5f ft/pt  H_check=%.2fft "
          f"(OAH err %.1f%%)  @x=%.1f y=%.1f"
          % (s["w_in"] / s["h_in"], s["w_in"], s["h_in"], scale, hck,
             err * 100, s["x_in"], s["y_in"]))

print("\n=== cabinet reference candidates (aspect ~ %.3f) ===" % (CAB_W_FT / CAB_H_FT))
cab_cands = []
for s in shapes:
    ar = s["w_in"] / s["h_in"]
    if 1.55 <= ar <= 1.75 and min(s["w_in"], s["h_in"]) > 30:
        scale = CAB_W_FT / s["w_in"]
        cab_cands.append((s, scale))
for s, scale in sorted(cab_cands, key=lambda r: -r[0]["w_in"])[:8]:
    print(f"  w=%.1f h=%.1f -> scale=%.5f ft/pt  @x=%.1f y=%.1f"
          % (s["w_in"], s["h_in"], scale, s["x_in"], s["y_in"]))

if not ref_cands:
    print("NO overall-elevation reference found; aborting")
    raise SystemExit(1)

err, ref, scale, hck = ref_cands[0]
print(f"\nCHOSEN scale ref: w={ref['w_in']:.1f}pt = {OAW_FT:.3f}ft "
      f"-> scale={scale:.5f} ft/pt (OAH cross-check err {err*100:.1f}%)")

# Column covers: tall narrow rects within the chosen elevation's x-span,
# real width ~18" -> drawn ~ COVER_W_FT/scale pt; height a large fraction
# of the elevation. Aspect h/w large (>3).
cover_w_pt = COVER_W_FT / scale
lo_x, hi_x = ref["x_in"], ref["x_in"] + ref["w_in"]
lo_y, hi_y = ref["y_in"], ref["y_in"] + ref["h_in"]
print(f"\nexpected drawn cover width ~{cover_w_pt:.1f}pt; "
      f"elevation x[{lo_x:.0f},{hi_x:.0f}] y[{lo_y:.0f},{hi_y:.0f}]")

cover_cands = []
for s in shapes:
    if s is ref:
        continue
    ar = s["h_in"] / s["w_in"]
    inside = (lo_x - 20) <= cx(s) <= (hi_x + 20) and (lo_y - 20) <= cy(s) <= (hi_y + 40)
    if ar >= 3.0 and inside and 0.4 * cover_w_pt <= s["w_in"] <= 2.5 * cover_w_pt:
        cover_cands.append(s)

cover_cands.sort(key=lambda s: cx(s))
print(f"\n=== column-cover candidates ({len(cover_cands)}) ===")
for s in cover_cands:
    print(f"  cx=%.1f cy=%.1f w=%.1f(%.2fft) h=%.1f(%.2fft) p=%s"
          % (cx(s), cy(s), s["w_in"], s["w_in"] * scale,
             s["h_in"], s["h_in"] * scale, s["page"]))

# Pick the two outermost symmetric covers about the elevation centerline
if len(cover_cands) >= 2:
    elev_cx = ref["x_in"] + ref["w_in"] / 2.0
    left = min(cover_cands, key=lambda s: cx(s))
    right = max(cover_cands, key=lambda s: cx(s))
    spacing_pt = abs(cx(right) - cx(left))
    spacing_ft = spacing_pt * scale
    sym_off = abs((cx(left) + cx(right)) / 2.0 - elev_cx) * scale
    ft = int(spacing_ft)
    inch = round((spacing_ft - ft) * 12)
    print(f"\n>>> DERIVED pole centerline spacing = {spacing_ft:.2f} ft "
          f"= {ft}'-{inch}\"  (symmetry offset {sym_off:.2f} ft)")
    print(f"    left cx={cx(left):.1f} right cx={cx(right):.1f} "
          f"elev_cx={elev_cx:.1f} scale={scale:.5f} ft/pt")
else:
    print("\n>>> Could not isolate 2 column covers automatically; "
          "manual identification required (see candidates above).")
