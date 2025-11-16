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
async def submit_to_pm(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    breaker_name = "pm"
    if not breaker_allow(breaker_name):
        logger.warning("pm.breaker_open", project_id=project_id)
        # Drop to DLQ rather than retrying until cool-off passes
        dlq_push("pm", {"project_id": project_id, "payload": payload, "reason": "breaker_open"})
        self.update_state(state=states.FAILURE, meta={"reason": "breaker_open"})
        raise Ignore()

    url = os.getenv("APEX_PM_URL", "http://pm.local/submit")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(url, json={"project_id": project_id, **payload})
        if r.status_code >= 500:
            raise RuntimeError(f"pm 5xx: {r.status_code}")
        if r.status_code >= 400:
            # Permanent failure → DLQ
            dlq_push("pm", {"project_id": project_id, "payload": payload, "status": r.status_code, "body": r.text})
            self.update_state(state=states.FAILURE, meta={"status": r.status_code})
            raise Ignore()
        breaker_record_success(breaker_name)
        result = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"status": r.status_code}
        logger.info("pm.submitted", project_id=project_id, status=r.status_code)
        return {"project_id": project_id, "result": result}
    except Ignore:
        raise
    except Exception as e:
        breaker_record_failure(breaker_name)
        logger.warning("pm.submit_retry", project_id=project_id, error=str(e), retries=self.request.retries)
        raise


