from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from celery.utils.log import get_task_logger

from ..app import app


logger = get_task_logger(__name__)


def _snapshot_sha(snapshot: dict[str, Any]) -> str:
    data = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    return sha256(data).hexdigest()


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=60, max_retries=5)
def generate_report(self, project_id: str, snapshot: dict[str, Any]) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    pdf_sha = _snapshot_sha(snapshot)
    key = f"reports/{project_id}/{pdf_sha}.pdf"
    # Rendering and storage are handled elsewhere; here we return a deterministic reference
    logger.info("report.generated", project_id=project_id, pdf_sha=pdf_sha, key=key)
    return {"project_id": project_id, "pdf_sha": pdf_sha, "key": key}


