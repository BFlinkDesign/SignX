from __future__ import annotations

from contracts.stackup import StackupAnalyzeRequest, Feature
from svcs.agent_stackup.main import simulate_stackup, cp_cpk


def test_cp_cpk_basic():
    cp, cpk = cp_cpk(mean=10.0, sigma=1.0, lower=7.0, upper=13.0)
    assert round(cp, 3) == round((13.0 - 7.0) / 6.0, 3)
    assert round(cpk, 3) == round(min((10.0 - 7.0) / 3.0, (13.0 - 10.0) / 3.0), 3)


def test_simulate_stackup_mean_close():
    req = StackupAnalyzeRequest(
        task_id="seed-mean-1",
        description="test",
        features=[
            Feature(name="a", nominal=10.0, tol_plus=0.1, tol_minus=0.1, distribution="normal"),
            Feature(name="b", nominal=5.0, tol_plus=0.1, tol_minus=0.1, distribution="normal"),
        ],
        sample_size=10000,
        lower_spec=None,
        upper_spec=None,
    )
    _, mean, sigma, cp, cpk, pass_prob, hist, assumptions = simulate_stackup(req)
    assert abs(mean - 15.0) < 0.05
    assert sigma > 0
    assert hist and len(hist) == 20


