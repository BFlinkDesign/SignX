from __future__ import annotations

from contracts.cad import CADMacroRequest
from svcs.agent_cad.main import build_freecad_script


def test_script_contains_operations_in_order():
    req = CADMacroRequest(task_id="cad1", target="freecad", primitives=["pad", "pocket", "fillet"], constraints=[], dims={})
    text = build_freecad_script(req)
    pad_idx = text.find("extrude")
    pocket_idx = text.find("cut(")
    fillet_idx = text.find("makeFillet")
    assert 0 <= pad_idx < pocket_idx < fillet_idx


