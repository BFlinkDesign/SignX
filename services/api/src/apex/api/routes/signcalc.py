from __future__ import annotations

from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, Request

from ..common.models import make_envelope
from ..deps import get_code_version, get_model_config
from ..security_config import get_global_limiter, get_rate_limit
from ..metrics import ABSTAIN_TOTAL
from ..schemas import ResponseEnvelope
import logging

logger = logging.getLogger(__name__)

# Initialize rate limiter (shared instance across the API service)
limiter = get_global_limiter()
SIGNCALC_RATE_LIMIT = get_rate_limit("signcalc")

router = APIRouter(prefix="/v1/signcalc")


async def _proxy(
    method: str, path: str, body: Optional[dict[str, Any]]
) -> tuple[int, dict[str, Any] | str]:
    base = "http://signcalc:8002"
    url = f"{base}/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=15) as cx:
        resp = await cx.request(method, url, json=body)
        content_type = resp.headers.get("content-type", "application/json")
        try:
            return resp.status_code, resp.json()
        except Exception as e:
            logger.warning("Exception in signcalc.py: %s", str(e))
            return resp.status_code, resp.text


@router.api_route("/{path:path}", methods=["GET", "POST"], response_model=ResponseEnvelope)
@limiter.limit(SIGNCALC_RATE_LIMIT)  # enforce configured rate limit
async def gateway(
    request: Request,
    path: str,
    model_config=Depends(get_model_config),
    code_version=Depends(get_code_version),
):  # type: ignore[no-untyped-def]
    """
    Gateway proxy to signcalc service with rate limiting.
    
    Rate limit: 100 requests per minute per IP address.
    This helps prevent DoS attacks and resource exhaustion from expensive calculations.
    """
    body = None
    if request.method == "POST":
        body = await request.json()
    status_code, proxied = await _proxy(request.method, path, body)

    assumptions: list[str] = ["proxied:signcalc-service"]
    ok = 200 <= status_code < 300
    if not ok:
        ABSTAIN_TOTAL.inc()
    return make_envelope(
        result={"upstream": proxied},
        assumptions=assumptions,
        confidence=1.0 if ok else 0.4,
        inputs={"method": request.method, "path": path},
        intermediates={"upstream_status": status_code},
        outputs={"ok": ok},
        code_version=code_version,
        model_config=model_config,
    )


