"""Tests for PM dispatch task with idempotency validation."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_pm_dispatch_happy_path(mock_celery_app, sample_project_data, env_vars, tasks_module):
    """Test successful PM dispatch."""
    result = tasks_module.dispatch_to_pm_task.apply(
        args=("proj_test123", sample_project_data),
        kwargs={},
    )

    assert result.successful()
    output = result.result

    assert "project_number" in output
    assert output["project_number"].startswith("PRJ-")
    assert "pm_ref" in output
    assert output["status"] == "dispatched"


@pytest.mark.asyncio
async def test_pm_dispatch_idempotency(mock_celery_app, sample_project_data, env_vars, tasks_module):
    """Test that identical idempotency keys produce identical results."""
    idempotency_key = "idempotent_key_123"

    result1 = tasks_module.dispatch_to_pm_task.apply(
        args=("proj_test123", sample_project_data),
        kwargs={"idempotency_key": idempotency_key},
    )

    result2 = tasks_module.dispatch_to_pm_task.apply(
        args=("proj_test123", sample_project_data),
        kwargs={"idempotency_key": idempotency_key},
    )

    # Should return same project number (idempotent)
    assert result1.result["project_number"] == result2.result["project_number"]


@pytest.mark.asyncio
async def test_pm_dispatch_retry_on_failure(mock_celery_app, sample_project_data, env_vars, tasks_module):
    """Test task retry logic on PM API failure."""
    # Mock dispatch to fail once, then succeed
    import uuid

    original_uuid = uuid.uuid4
    call_count = 0

    def failing_uuid():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("PM API unavailable")
        return original_uuid()

    from unittest.mock import patch

    with patch("uuid.uuid4", failing_uuid):
        result = tasks_module.dispatch_to_pm_task.apply(
            args=("proj_retry_test", sample_project_data),
            kwargs={},
        )

    assert result.successful()
    assert "project_number" in result.result


@pytest.mark.asyncio
async def test_pm_dispatch_max_retries(mock_celery_app, sample_project_data, env_vars, tasks_module):
    """Test task failure after max retries (5 for PM dispatch)."""
    # Mock dispatch to always fail
    import uuid

    def always_fail():
        raise ConnectionError("PM API persistently unavailable")

    from unittest.mock import patch

    # Temporarily break uuid.uuid4 to cause persistent failures
    with patch("apex.worker.tasks.uuid.uuid4", always_fail):
        result = tasks_module.dispatch_to_pm_task.apply(
            args=("proj_fail_test", sample_project_data),
            kwargs={},
        )

    # Should fail after 5 retries
    assert result.failed()


@pytest.mark.parametrize("project_variant", [
    {"name": "Different Name"},
    {"customer": "Different Customer"},
    {"status": "accepted"},
])
@pytest.mark.asyncio
async def test_pm_dispatch_project_variants(
    mock_celery_app,
    sample_project_data,
    env_vars,
    tasks_module,
    project_variant,
):
    """Test PM dispatch with different project data variants."""
    modified_project = sample_project_data.copy()
    modified_project.update(project_variant)

    result = tasks_module.dispatch_to_pm_task.apply(
        args=("proj_variant_test", modified_project),
        kwargs={},
    )

    assert result.successful()
    assert "project_number" in result.result


@pytest.mark.asyncio
async def test_pm_dispatch_base_task_logging(mock_celery_app, sample_project_data, env_vars, tasks_module, caplog):
    """Test that BaseTask logs success and failure events."""
    import logging

    caplog.set_level(logging.INFO)

    result = tasks_module.dispatch_to_pm_task.apply(
        args=("proj_logging_test", sample_project_data),
        kwargs={},
    )

    assert result.successful()

    # Should have success log from BaseTask
    log_messages = [record.message for record in caplog.records]
    assert any("task.success" in msg for msg in log_messages)


@pytest.mark.asyncio
async def test_pm_dispatch_slow_performance(monkeypatch, mock_celery_app, sample_project_data, env_vars, tasks_module):
    """Test SLO requirement: dispatch completes <200ms."""
    import time

    start = time.time()

    result = tasks_module.dispatch_to_pm_task.apply(
        args=("proj_perf_test", sample_project_data),
        kwargs={},
    )

    elapsed_ms = (time.time() - start) * 1000

    assert result.successful()
    assert elapsed_ms < 200, f"Dispatch took {elapsed_ms:.2f}ms, exceeds 200ms SLO"

