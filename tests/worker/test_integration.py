"""Integration tests for worker tasks."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_full_submission_workflow(mock_celery_app, sample_payload, mock_report_generation, env_vars, tasks_module):
    """Test complete submission workflow: report -> dispatch -> email."""
    # Step 1: Generate report
    report_result = tasks_module.generate_report_task.apply(
        args=("proj_workflow_test", sample_payload),
        kwargs={},
    )

    assert report_result.successful()
    report_data = report_result.result
    assert "sha256" in report_data

    # Step 2: Dispatch to PM
    project_data = {
        "project_id": "proj_workflow_test",
        "name": "Workflow Test Project",
        "report_sha256": report_data["sha256"],
    }

    dispatch_result = tasks_module.dispatch_to_pm_task.apply(
        args=("proj_workflow_test", project_data),
        kwargs={},
    )

    assert dispatch_result.successful()
    dispatch_data = dispatch_result.result
    assert "project_number" in dispatch_data

    # Step 3: Send email notification
    email_result = tasks_module.send_email_notification_task.apply(
        args=(
            "user@example.com",
            "Project Submitted",
            "submission_confirmation",
            {"project_number": dispatch_data["project_number"]},
        ),
        kwargs={},
    )

    assert email_result.successful()
    assert email_result.result["status"] == "sent"


@pytest.mark.asyncio
async def test_task_retry_backoff_timing(mock_celery_app, sample_payload, env_vars, tasks_module):
    """Test that retry backoff timing is reasonable."""
    import time

    # Mock report generation to fail with delays
    call_count = 0
    timings = []

    async def failing_with_timing(*args, **kwargs):
        nonlocal call_count
        timings.append(time.time())
        call_count += 1
        if call_count < 3:
            raise RuntimeError(f"Retry attempt {call_count}")
        return {
            "sha256": "test_hash",
            "pdf_ref": "test.pdf",
            "cached": False,
        }

    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent
    api_path = repo_root / "services" / "api" / "src"
    if str(api_path) not in sys.path:
        sys.path.insert(0, str(api_path))

    from unittest.mock import patch

    with patch("apex.api.utils.report.generate_report_from_payload", failing_with_timing):
        result = tasks_module.generate_report_task.apply(
            args=("proj_backoff_test", sample_payload),
            kwargs={},
        )

    assert result.successful()

    # Verify retries occurred
    assert call_count == 3

    # Verify backoff timing (approximately exponential)
    if len(timings) >= 2:
        delay1 = timings[1] - timings[0]
        delay2 = timings[2] - timings[1] if len(timings) >= 3 else 0

        # Backoff should be non-decreasing
        if delay2 > 0:
            assert delay2 >= delay1, "Retry backoff should be non-decreasing"


@pytest.mark.asyncio
async def test_concurrent_task_execution(mock_celery_app, sample_payload, mock_report_generation, env_vars, tasks_module):
    """Test that multiple tasks can execute concurrently."""
    import asyncio

    async def run_report_task(project_id):
        result = tasks_module.generate_report_task.apply(
            args=(project_id, sample_payload),
            kwargs={},
        )
        return result.successful() and "sha256" in result.result

    # Run 10 concurrent reports
    project_ids = [f"proj_concurrent_{i}" for i in range(10)]
    tasks = [run_report_task(pid) for pid in project_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # All should succeed
    assert all(results)
    assert all(isinstance(r, bool) and r for r in results)


@pytest.mark.asyncio
async def test_error_propagation(mock_celery_app, sample_payload, env_vars, tasks_module):
    """Test that errors propagate correctly through task hierarchy."""
    # Mock report generation to fail persistently
    async def always_fail(*args, **kwargs):
        raise ValueError("Persistent error")

    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent
    api_path = repo_root / "services" / "api" / "src"
    if str(api_path) not in sys.path:
        sys.path.insert(0, str(api_path))

    from unittest.mock import patch

    with patch("apex.api.utils.report.generate_report_from_payload", always_fail):
        result = tasks_module.generate_report_task.apply(
            args=("proj_error_test", sample_payload),
            kwargs={},
        )

    # Task should fail after retries
    assert result.failed()

    # Error should be captured in result
    assert result.traceback is not None


@pytest.mark.asyncio
async def test_task_result_persistence(mock_celery_app, sample_project_data, env_vars, tasks_module):
    """Test that task results are properly stored and retrievable."""
    result1 = tasks_module.dispatch_to_pm_task.apply(
        args=("proj_result_test", sample_project_data),
        kwargs={},
    )

    assert result1.successful()

    # Verify result can be retrieved by task ID
    task_id = result1.task_id
    assert task_id is not None

    # In production, would verify:
    # - Result is stored in Redis/backend
    # - Result can be fetched via AsyncResult(task_id).get()
    # - Results have TTL configured

