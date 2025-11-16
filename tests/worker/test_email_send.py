"""Tests for email notification task."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_email_send_happy_path(mock_celery_app, env_vars, tasks_module):
    """Test successful email sending."""
    result = tasks_module.send_email_notification_task.apply(
        args=("recipient@example.com", "Test Subject", "test_template", {"var": "value"}),
        kwargs={},
    )

    assert result.successful()
    output = result.result

    assert "message_id" in output
    assert output["message_id"].startswith("email-")
    assert output["status"] == "sent"


@pytest.mark.asyncio
async def test_email_send_retry_on_failure(mock_celery_app, env_vars, tasks_module):
    """Test task retry logic on email service failure."""
    import uuid

    original_uuid = uuid.uuid4
    call_count = 0

    def failing_uuid():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("Email service unavailable")
        return original_uuid()

    from unittest.mock import patch

    with patch("uuid.uuid4", failing_uuid):
        result = tasks_module.send_email_notification_task.apply(
            args=("recipient@example.com", "Retry Test", "retry_template", {}),
            kwargs={},
        )

    assert result.successful()


@pytest.mark.asyncio
async def test_email_send_max_retries(mock_celery_app, env_vars, tasks_module):
    """Test task failure after max retries (3 for email)."""
    import uuid

    def always_fail():
        raise ConnectionError("Email service persistently unavailable")

    from unittest.mock import patch

    with patch("apex.worker.tasks.uuid.uuid4", always_fail):
        result = tasks_module.send_email_notification_task.apply(
            args=("recipient@example.com", "Fail Test", "fail_template", {}),
            kwargs={},
        )

    assert result.failed()


@pytest.mark.parametrize("template_variant", [
    "project_submitted",
    "report_ready",
    "design_complete",
])
@pytest.mark.asyncio
async def test_email_send_template_variants(
    mock_celery_app,
    env_vars,
    tasks_module,
    template_variant,
):
    """Test email sending with different templates."""
    result = tasks_module.send_email_notification_task.apply(
        args=("recipient@example.com", f"Test {template_variant}", template_variant, {"name": "Test"}),
        kwargs={},
    )

    assert result.successful()
    assert "message_id" in result.result


@pytest.mark.parametrize("email_variant", [
    "user@domain.com",
    "test.user+tag@example.org",
    "admin@test-co.net",
])
@pytest.mark.asyncio
async def test_email_send_recipient_variants(
    mock_celery_app,
    env_vars,
    tasks_module,
    email_variant,
):
    """Test email sending to different recipient formats."""
    result = tasks_module.send_email_notification_task.apply(
        args=(email_variant, "Test Subject", "test_template", {}),
        kwargs={},
    )

    assert result.successful()


@pytest.mark.asyncio
async def test_email_send_context_variants(mock_celery_app, env_vars, tasks_module):
    """Test email sending with different context variables."""
    contexts = [
        {"project_id": "proj_123", "name": "Test Project"},
        {"report_url": "https://example.com/report.pdf"},
        {"user": "John Doe", "date": "2025-01-27"},
    ]

    for context in contexts:
        result = tasks_module.send_email_notification_task.apply(
            args=("recipient@example.com", "Context Test", "test_template", context),
            kwargs={},
        )

        assert result.successful()


@pytest.mark.asyncio
async def test_email_send_performance(monkeypatch, mock_celery_app, env_vars, tasks_module):
    """Test SLO requirement: email completes <200ms."""
    import time

    start = time.time()

    result = tasks_module.send_email_notification_task.apply(
        args=("recipient@example.com", "Perf Test", "perf_template", {}),
        kwargs={},
    )

    elapsed_ms = (time.time() - start) * 1000

    assert result.successful()
    assert elapsed_ms < 200, f"Email send took {elapsed_ms:.2f}ms, exceeds 200ms SLO"

