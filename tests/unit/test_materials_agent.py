from __future__ import annotations

from contracts.materials import MaterialPickRequest, WeightVector
from svcs.agent_materials.main import score_candidates, Candidate


def test_monotonicity_yield_weight():
    req = MaterialPickRequest(
        task_id="t1",
        application="test",
        key_requirements=[],
        min_yield_mpa=None,
        weights=WeightVector(cost=0.0, strength=1.0, corrosion=0.0),
    )
    cands = [
        Candidate("low", yield_mpa=200.0, cost_index=1.0, corrosion_ordinal=3, source="s"),
        Candidate("high", yield_mpa=300.0, cost_index=1.0, corrosion_ordinal=3, source="s"),
    ]
    recs, _, _, _, _ = score_candidates(req, cands)
    assert recs[0].material == "high"


