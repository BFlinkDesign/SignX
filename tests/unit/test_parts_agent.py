from __future__ import annotations

from contracts.parts import PartsQueryRequest
from svcs.agent_parts.main import load_catalogs, rank


def test_hard_constraints_filter_and_soft_tiebreak():
    rows = load_catalogs()
    req = PartsQueryRequest(
        task_id="p1",
        query="M6 20",
        hard_constraints={"thread": "M6", "length_mm": "20"},
        soft_constraints={"material": "304SS"},
    )
    top = rank(req, rows)
    assert all(m.specs.get("thread") == "M6" and m.specs.get("length_mm") == "20" for m in top)
    # If 304SS exists in fallback, it should win over same price zinc-coated steel
    assert top[0].part_id.endswith("ss304")


