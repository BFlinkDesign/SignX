from __future__ import annotations

from contracts.signs import SignRequest


def build_freecad_macro(req: SignRequest) -> str:
    return f"""# FreeCAD macro scaffold
import FreeCAD, Part
# panel
w,h,d = {req.dimensions.w_mm},{req.dimensions.h_mm},{req.dimensions.d_mm}
# ... create cabinet solid, returns, access panel, label callouts ...
"""


