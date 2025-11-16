from __future__ import annotations

from typing import Any
from fastapi import APIRouter, status
from redis.asyncio import Redis
from .deps import settings, get_model_config, get_code_version
from .schemas import ResponseEnvelope, TraceDataModel, TraceModel


router = APIRouter()


# Use unified build_envelope from common.utils
from .common.utils import build_envelope
from ..schemas import TraceDataModel

def _envelope(result, assumptions, confidence, inputs, intermediates, outputs):
    """Wrapper for backward compatibility."""
    return build_envelope(
        result=result,
        assumptions=assumptions,
        confidence=confidence,
        inputs=inputs,
        intermediates=intermediates,
        outputs=outputs,
    )


@router.get("/ready", response_model=ResponseEnvelope, status_code=status.HTTP_200_OK)
async def ready():
    checks: dict[str, Any] = {}
    ok = True

    # Minimal dev readiness: Redis ping only (others are no-ops in dev)
    try:
        r = Redis.from_url(settings.redis_url)
        pong = await r.ping()
        await r.aclose()
        checks["redis"] = "ok" if pong else "fail"
        ok &= bool(pong)
    except Exception as e:  # noqa
        checks["redis"] = f"fail:{type(e).__name__}"
        ok = False

    result = {
        "service": settings.service_name,
        "env": settings.env,
        "status": "ok" if ok else "degraded",
        "schema_version": settings.schema_version,
        "deployment_id": settings.deployment_id,
        "checks": checks,
    }
    return _envelope(result, [], 1.0 if ok else 0.5, {"env": settings.env}, {}, {"ok": ok})


