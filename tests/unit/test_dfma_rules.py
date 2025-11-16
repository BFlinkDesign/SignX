from __future__ import annotations

from contracts.dfma import DFMAEvaluateRequest
from svcs.agent_dfma.main import evaluate


def test_sheet_metal_rules_trigger_and_clear():
    req_bad = DFMAEvaluateRequest(task_id="t1", description="L bracket", process="sheet_metal", params={"r_over_t": 0.8, "hole_edge_multiple": 1.0, "quantity": 100})
    v1, s1, b1, c1 = evaluate(req_bad)
    assert "min_bend_radius_violation" in v1
    assert "hole_to_edge_violation" in v1

    req_good = DFMAEvaluateRequest(task_id="t2", description="L bracket", process="sheet_metal", params={"r_over_t": 1.0, "hole_edge_multiple": 1.5, "quantity": 100})
    v2, s2, b2, c2 = evaluate(req_good)
    assert v2 == []


def test_machining_deep_slot():
    req = DFMAEvaluateRequest(task_id="t3", description="slot part", process="machining", params={"slot_l_over_d": 7.0, "quantity": 10})
    v, s, b, c = evaluate(req)
    assert "deep_narrow_slot" in v


def test_3dp_wall_thickness():
    req = DFMAEvaluateRequest(task_id="t4", description="thin wall", process="3dp", params={"wall_thickness_mm": 0.5, "quantity": 1})
    v, s, b, c = evaluate(req)
    assert "wall_too_thin" in v


