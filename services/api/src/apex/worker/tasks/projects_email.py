from __future__ import annotations

import os
from typing import Any

import httpx
from celery import states
from celery.exceptions import Ignore
from celery.utils.log import get_task_logger

from ..app import app
from ..utils import breaker_allow, breaker_record_failure, breaker_record_success, dlq_push


logger = get_task_logger(__name__)


@app.task(bind=True, max_retries=5, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60)
async def send_email(self, to: str, subject: str, body: str, meta: dict[str, Any] | None = None) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    breaker_name = "email"
    if not breaker_allow(breaker_name):
        logger.warning("email.breaker_open", to=to)
        dlq_push("email", {"to": to, "subject": subject, "reason": "breaker_open", "meta": meta or {}})
        self.update_state(state=states.FAILURE, meta={"reason": "breaker_open"})
        raise Ignore()

    url = os.getenv("APEX_EMAIL_URL", "http://mailer.local/send")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(url, json={"to": to, "subject": subject, "body": body, "meta": meta or {}})
        if r.status_code >= 500:
            raise RuntimeError(f"mailer 5xx: {r.status_code}")
        if r.status_code >= 400:
            dlq_push("email", {"to": to, "subject": subject, "status": r.status_code, "body": r.text})
            self.update_state(state=states.FAILURE, meta={"status": r.status_code})
            raise Ignore()
        breaker_record_success(breaker_name)
        logger.info("email.sent", to=to)
        return {"to": to, "status": r.status_code}
    except Ignore:
        raise
    except Exception as e:
        breaker_record_failure(breaker_name)
        logger.warning("email.send_retry", to=to, error=str(e), retries=self.request.retries)
        raise


