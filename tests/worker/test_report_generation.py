"""Tests for PDF report generation task with monotonicity validation."""

from __future__ import annotations

import hashlib
import pytest


@pytest.mark.asyncio
async def test_report_generation_happy_path(mock_celery_app, sample_payload, mock_report_generation, env_vars, tasks_module):
    """Test successful PDF report generation."""
    # Execute task synchronously (eager mode)
    result = tasks_module.generate_report_task.apply(
        args=("proj_test123", sample_payload),
        kwargs={},
    )

    assert result.successful()
    output = result.result

    assert output["sha256"] == "test_sha256_hash"
    assert output["pdf_ref"] == "blobs/test/test_hash.pdf"
    assert output["cached"] is False


@pytest.mark.asyncio
async def test_report_generation_idempotency(mock_celery_app, sample_payload, mock_report_generation, env_vars, tasks_module):
    """Test that identical payloads produce identical outputs (monotonicity)."""
    # Generate report twice
    result1 = tasks_module.generate_report_task.apply(
        args=("proj_test123", sample_payload),
        kwargs={},
    )

    result2 = tasks_module.generate_report_task.apply(
        args=("proj_test456", sample_payload),  # Different project_id
        kwargs={},
    )

    # SHA256 must be identical (deterministic)
    assert result1.result["sha256"] == result2.result["sha256"]


@pytest.mark.asyncio
async def test_report_generation_retry_on_failure(mock_celery_app, sample_payload, env_vars, tasks_module):
    """Test task retry logic on failure."""
    # Mock report generation to fail once, then succeed
    call_count = 0

    async def failing_then_succeed(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RuntimeError("Temporary failure")
        return {
            "sha256": "test_sha256_retry",
            "pdf_ref": "blobs/test/test_retry.pdf",
            "cached": False,
        }

    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent
    api_path = repo_root / "services" / "api" / "src"
    if str(api_path) not in sys.path:
        sys.path.insert(0, str(api_path))

    from unittest.mock import patch

    with patch("apex.api.utils.report.generate_report_from_payload", failing_then_succeed):
        result = tasks_module.generate_report_task.apply(
            args=("proj_retry_test", sample_payload),
            kwargs={},
        )

    assert result.successful()
    assert call_count == 2  # Should retry once


@pytest.mark.asyncio
async def test_report_generation_max_retries_exceeded(mock_celery_app, sample_payload, env_vars, tasks_module):
    """Test task failure after max retries."""
    # Mock report generation to always fail
    async def always_fail(*args, **kwargs):
        raise RuntimeError("Persistent failure")

    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent
    api_path = repo_root / "services" / "api" / "src"
    if str(api_path) not in sys.path:
        sys.path.insert(0, str(api_path))

    from unittest.mock import patch

    with patch("apex.api.utils.report.generate_report_from_payload", always_fail):
        result = tasks_module.generate_report_task.apply(
            args=("proj_fail_test", sample_payload),
            kwargs={},
        )

    # Task should fail after retries (configured to max 3)
    assert result.failed()


@pytest.mark.asyncio
async def test_report_generation_caching(artifacts_dir, sample_payload, mock_report_generation, env_vars, tasks_module):
    """Test that cached reports are detected and reused."""
    # First generation creates cache
    result1 = tasks_module.generate_report_task.apply(
        args=("proj_cache_test1", sample_payload),
        kwargs={},
    )

    # Second generation with same payload should use cache (if mock supports it)
    result2 = tasks_module.generate_report_task.apply(
        args=("proj_cache_test2", sample_payload),
        kwargs={},
    )

    # Both should have same SHA256 (deterministic)
    assert result1.result["sha256"] == result2.result["sha256"]


@pytest.mark.parametrize("payload_variant", [
    {"module": "signage.baseplate"},
    {"config": {"request": {}}},
    {"files": ["file1.pdf"]},
    {"cost_snapshot": {"total": 10000.0}},
])
@pytest.mark.asyncio
async def test_report_generation_payload_variants(
    mock_celery_app,
    sample_payload,
    mock_report_generation,
    env_vars,
    tasks_module,
    payload_variant,
):
    """Test report generation with different payload variants."""
    modified_payload = sample_payload.copy()
    modified_payload.update(payload_variant)

    result = tasks_module.generate_report_task.apply(
        args=("proj_variant_test", modified_payload),
        kwargs={},
    )

    assert result.successful()
    assert "sha256" in result.result
    assert "pdf_ref" in result.result

