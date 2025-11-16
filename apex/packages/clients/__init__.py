from __future__ import annotations

import httpx
from typing import Any, Optional

# Import worker client utilities
try:
    from .worker_client import (
        enqueue_cad_macro_generation,
        enqueue_dfma_analysis,
        enqueue_health_ping,
        enqueue_materials_score,
        enqueue_standards_check,
        enqueue_stackup_calculation,
        get_celery_client,
        get_task_result,
    )
except ImportError:
    # Graceful fallback if celery not available
    pass


class BaseServiceClient:
    """Base class for HTTP service clients."""
    
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: Optional[dict] = None) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(f"{self.base_url}{path}", params=params or {})
            r.raise_for_status()
            return r.json()

    def _post(self, path: str, payload: dict) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(f"{self.base_url}{path}", json=payload)
            r.raise_for_status()
            return r.json()

