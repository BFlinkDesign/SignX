import pytest

from apex.domains.signage.cache import deterministic_cache


def test_deterministic_cache_normalises_float_inputs():
    call_count = {"count": 0}

    @deterministic_cache(maxsize=8)
    def expensive(x: float) -> float:
        call_count["count"] += 1
        return x * 2

    assert expensive(1.0000001) == pytest.approx(2.0)
    assert expensive(1.0000002) == pytest.approx(2.0)
    # Should have executed underlying function only once
    assert call_count["count"] == 1

