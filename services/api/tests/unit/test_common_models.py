from apex.api.common.models import (
    compute_confidence,
    add_assumption,
    make_envelope,
    build_response_envelope,
)
from apex.api.deps import get_code_version, get_model_config


def test_compute_confidence_penalties():
    assert compute_confidence(1.0, [0.1, 0.2]) == 0.7
    assert compute_confidence(0.5, [0.6]) == 0.0
    assert 0.0 <= compute_confidence(0.0) <= 1.0


def test_add_assumption():
    base = []
    out = add_assumption(base, "note")
    assert base == [] and out == ["note"]


def test_make_envelope_shape():
    env = make_envelope(
        result={"ok": True},
        assumptions=["a"],
        confidence=1.0,
        inputs={"x": 1},
        intermediates={},
        outputs={"y": 2},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )
    data = env.model_dump()
    assert set(data.keys()) == {"result", "assumptions", "confidence", "trace"}


def test_build_response_envelope_normalizes_trace_keys():
    env = build_response_envelope(
        result={"ok": True},
        assumptions=["a"],
        confidence=0.5,
        trace_inputs={"x": 1},
        trace_intermediates={"mid": "val"},
        trace_outputs={"y": 2},
    )

    payload = env.model_dump()
    assert payload["confidence"] == 0.5
    assert payload["trace"]["data"]["inputs"]["x"] == 1
    assert payload["trace"]["data"]["outputs"]["y"] == 2

