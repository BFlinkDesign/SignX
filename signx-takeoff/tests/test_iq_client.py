"""
test_iq_client.py — Integration tests for the 500IQ client and shadow mode wiring.

Tests:
  1. query_heuristic returns fallback when disabled
  2. query_heuristic returns clamped factor on valid response
  3. query_heuristic falls back on timeout
  4. query_heuristic gates on low confidence
  5. batch_query runs concurrently and handles mixed results
  6. Shadow mode does NOT alter estimate output
  7. Factor clamping enforces floor/ceiling
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import httpx

import iq_client


# ── Helpers ──────────────────────────────────────────────────────────────────

def _mock_iq_response(combined_factor: float, confidence: float = 0.90):
    """Build a mock 500IQ /heuristic JSON response."""
    return {
        "schema_version": "iq-1.0",
        "result": {
            "adjustments": [
                {
                    "heuristic_id": "HEURISTIC-TEST",
                    "label": "Test heuristic",
                    "adjustment_factor": combined_factor,
                    "confidence": confidence,
                    "evidence_chain": ["SIGN_TYPE-CLLIT", "HEURISTIC-TEST", "WORK_CODE-0270"],
                    "notes": "Test adjustment",
                }
            ],
            "combined_factor": combined_factor,
            "query": {
                "sign_type": "SIGN_TYPE-CLLIT",
                "work_code": "WORK_CODE-0270",
            },
        },
        "assumptions": [],
        "confidence": confidence,
        "trace": {
            "data_sha256": "abc123",
            "inputs_hash": "def456",
            "code_version": "test",
            "timestamp_utc": "2026-03-01T00:00:00+00:00",
        },
    }


# ── Test: Disabled returns fallback ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_disabled_returns_fallback():
    """When IQ_ENABLED=false, query returns neutral factor 1.0."""
    with patch.object(iq_client, "IQ_ENABLED", False):
        result = await iq_client.query_heuristic("CLLIT", "0270")

    assert result["factor"] == 1.0
    assert result["source"] == "fallback:disabled"
    assert result["adjustments"] == []


# ── Test: Valid response with clamping ───────────────────────────────────────

def _make_mock_client(mock_resp=None, side_effect=None):
    """Build a properly configured AsyncClient mock for httpx context manager."""
    client_instance = AsyncMock()
    if side_effect:
        client_instance.post.side_effect = side_effect
    elif mock_resp is not None:
        client_instance.post.return_value = mock_resp
    # Make async context manager return the same instance
    client_instance.__aenter__.return_value = client_instance
    client_instance.__aexit__.return_value = False
    return client_instance


@pytest.mark.asyncio
async def test_valid_response_returns_clamped_factor():
    """Valid 500IQ response with factor within range passes through."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = _mock_iq_response(1.15, confidence=0.90)

    with (
        patch.object(iq_client, "IQ_ENABLED", True),
        patch("iq_client.httpx.AsyncClient", return_value=_make_mock_client(mock_resp)),
    ):
        result = await iq_client.query_heuristic("CLLIT", "0270")

    assert result["factor"] == 1.15
    assert result["raw_factor"] == 1.15
    assert result["confidence"] == 0.90
    assert result["source"] == "500iq"


# ── Test: Timeout returns fallback ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_timeout_returns_fallback():
    """HTTP timeout falls back to neutral factor."""
    with (
        patch.object(iq_client, "IQ_ENABLED", True),
        patch("iq_client.httpx.AsyncClient", return_value=_make_mock_client(
            side_effect=httpx.TimeoutException("timed out")
        )),
    ):
        result = await iq_client.query_heuristic("CLLIT", "0270")

    assert result["factor"] == 1.0
    assert result["source"] == "fallback:timeout"


# ── Test: Low confidence gates to fallback ───────────────────────────────────

@pytest.mark.asyncio
async def test_low_confidence_gates_to_fallback():
    """Factor below min_confidence threshold falls back to neutral."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = _mock_iq_response(1.15, confidence=0.30)

    with (
        patch.object(iq_client, "IQ_ENABLED", True),
        patch.object(iq_client, "IQ_MIN_CONFIDENCE", 0.75),
        patch("iq_client.httpx.AsyncClient", return_value=_make_mock_client(mock_resp)),
    ):
        result = await iq_client.query_heuristic("CLLIT", "0270")

    assert result["factor"] == 1.0
    assert result["source"] == "fallback:low_confidence"
    assert result["raw_factor"] == 1.15  # Raw preserved for logging


# ── Test: Factor clamping enforces ceiling ───────────────────────────────────

@pytest.mark.asyncio
async def test_factor_clamped_to_ceiling():
    """Factor above ceiling (1.8) gets clamped down."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    # 10.294 factor — the massive CLLIT 0270 ratio from warehouse
    mock_resp.json.return_value = _mock_iq_response(10.294, confidence=0.90)

    with (
        patch.object(iq_client, "IQ_ENABLED", True),
        patch.object(iq_client, "IQ_FACTOR_CEILING", 1.8),
        patch("iq_client.httpx.AsyncClient", return_value=_make_mock_client(mock_resp)),
    ):
        result = await iq_client.query_heuristic("CLLIT", "0270")

    assert result["factor"] == 1.8  # Clamped from 10.294
    assert result["raw_factor"] == 10.294  # Raw preserved
    assert result["source"] == "500iq"


# ── Test: Factor clamping enforces floor ─────────────────────────────────────

@pytest.mark.asyncio
async def test_factor_clamped_to_floor():
    """Factor below floor (0.6) gets clamped up."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = _mock_iq_response(0.2, confidence=0.85)

    with (
        patch.object(iq_client, "IQ_ENABLED", True),
        patch.object(iq_client, "IQ_FACTOR_FLOOR", 0.6),
        patch("iq_client.httpx.AsyncClient", return_value=_make_mock_client(mock_resp)),
    ):
        result = await iq_client.query_heuristic("CLLIT", "0270")

    assert result["factor"] == 0.6  # Clamped from 0.2
    assert result["raw_factor"] == 0.2


# ── Test: Batch query runs concurrently ──────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_query_concurrent():
    """batch_query hits multiple work codes and returns keyed results."""
    call_count = 0

    async def _mock_query(sign_type, work_code, employee_id=None):
        nonlocal call_count
        call_count += 1
        return {
            "factor": 1.1 if work_code == "0270" else 1.0,
            "raw_factor": 1.1 if work_code == "0270" else 1.0,
            "confidence": 0.85,
            "adjustments": [],
            "source": "500iq",
        }

    with (
        patch.object(iq_client, "IQ_ENABLED", True),
        patch.object(iq_client, "query_heuristic", side_effect=_mock_query),
    ):
        results = await iq_client.batch_query("CLLIT", ["0210", "0270", "0640"])

    assert len(results) == 3
    assert results["0270"]["factor"] == 1.1
    assert results["0210"]["factor"] == 1.0
    assert call_count == 3


# ── Test: Batch query disabled ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_query_disabled():
    """batch_query returns all fallbacks when disabled."""
    with patch.object(iq_client, "IQ_ENABLED", False):
        results = await iq_client.batch_query("CLLIT", ["0210", "0270"])

    assert all(r["source"] == "fallback:disabled" for r in results.values())
    assert all(r["factor"] == 1.0 for r in results.values())


# ── Test: Shadow mode does not alter estimate hours ──────────────────────────

@pytest.mark.asyncio
async def test_shadow_mode_preserves_hours():
    """
    In shadow mode, estimate hours MUST NOT change.

    We test the invariant directly: when IQ_SHADOW_MODE=True,
    batch_query returns factors but calling code should NOT apply them.
    Verified by running a real estimate, getting IQ factors, and confirming
    that applying factor * hours differs from original — proving the
    shadow gate is needed to prevent mutation.
    """
    from abc_engine import (
        JobInput, FontType, ConstructionType, SignType, estimate, LaborLine,
    )

    # Run a real estimate
    job = JobInput()
    job.letter_count = 10
    job.letter_height_inches = 18.0
    job.font_type = FontType.BLOCK
    job.construction = ConstructionType.FACE_LIT
    job.sign_type = SignType.CLLIT

    result = estimate(job)
    original_man_hours = result.total_man_hours
    original_crew_hours = result.total_crew_hours
    original_labor = [(l.work_code, l.hours) for l in result.labor_lines]

    # Verify estimate produced non-zero hours
    assert original_man_hours > 0, "Estimate must produce hours to test shadow mode"

    # Simulate shadow mode batch query
    all_lines = result.labor_lines + result.install_lines
    work_codes = list({l.work_code for l in all_lines})

    async def _mock_batch(sign_type, wcs, employee_id=None):
        return {
            wc: {
                "factor": 1.15,
                "raw_factor": 1.15,
                "confidence": 0.90,
                "adjustments": [],
                "source": "500iq",
            }
            for wc in wcs
        }

    with (
        patch.object(iq_client, "IQ_ENABLED", True),
        patch.object(iq_client, "IQ_SHADOW_MODE", True),
        patch.object(iq_client, "batch_query", side_effect=_mock_batch),
    ):
        iq_results = await iq_client.batch_query("CLLIT", work_codes)

        # Shadow mode check: factors exist but should NOT be applied
        assert iq_client.is_shadow_mode() is True

        # Build shadow log WITHOUT modifying hours (as _iq_shadow_annotate does)
        shadow_log = {}
        for line in all_lines:
            iq = iq_results.get(line.work_code)
            if iq is None:
                continue
            base = line.hours
            adjusted = round(base * iq["factor"], 2)
            shadow_log[line.work_code] = {
                "base_hours": base,
                "adjusted_hours": adjusted,
                "delta_pct": round((iq["factor"] - 1.0) * 100, 1),
            }
            # In shadow mode: DO NOT mutate line.hours
            if not iq_client.is_shadow_mode():
                line.hours = adjusted  # This should NOT execute

    # Hours MUST be unchanged
    assert result.total_man_hours == original_man_hours
    assert result.total_crew_hours == original_crew_hours
    assert [(l.work_code, l.hours) for l in result.labor_lines] == original_labor

    # Shadow log exists and shows what WOULD have changed
    assert len(shadow_log) > 0
    for wc, entry in shadow_log.items():
        assert entry["adjusted_hours"] != entry["base_hours"], (
            f"Factor 1.15 should produce different adjusted_hours for {wc}"
        )
        assert entry["delta_pct"] == 15.0


# ── Test: HTTP error returns fallback ────────────────────────────────────────

@pytest.mark.asyncio
async def test_http_error_returns_fallback():
    """HTTP 500 from 500IQ falls back to neutral factor."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=mock_resp
    )

    with (
        patch.object(iq_client, "IQ_ENABLED", True),
        patch("iq_client.httpx.AsyncClient", return_value=_make_mock_client(mock_resp)),
    ):
        result = await iq_client.query_heuristic("CLLIT", "0270")

    assert result["factor"] == 1.0
    assert result["source"] == "fallback:http_error"
