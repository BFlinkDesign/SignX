from __future__ import annotations

import logging
from typing import Any

import aiohttp
import anyio
import asyncpg
from celery import Celery
from fastapi import APIRouter, Depends, Request, status
from redis.asyncio import Redis

from .common.models import make_envelope
from .deps import get_code_version, get_model_config, settings
from .schemas import CodeVersionModel, ModelConfigModel, ResponseEnvelope

logger = logging.getLogger(__name__)


router = APIRouter()


def _get_celery() -> Celery:
    return Celery("apex-client", broker=settings.REDIS_URL, backend=settings.REDIS_URL)


@router.get("/ready", response_model=ResponseEnvelope, status_code=status.HTTP_200_OK)
async def ready(
    model_config: ModelConfigModel = Depends(get_model_config),
    code_version: CodeVersionModel = Depends(get_code_version),
    request: Request = None,  # type: ignore[assignment]
):
    checks: dict[str, Any] = {}
    assumptions: list[str] = []
    ok = True

    # Redis
    try:
        r = Redis.from_url(settings.REDIS_URL)
        pong = await r.ping()
        await r.aclose()
        checks["redis"] = "ok" if pong else "fail"
        ok = ok and bool(pong)
    except Exception as e:  # pragma: no cover
        checks["redis"] = f"fail:{e}"
        ok = False

    # Celery
    try:
        def sync_ping():
            app = _get_celery()
            res = app.send_task("health.ping")
            return res.get(timeout=5)

        celery_res = await anyio.to_thread.run_sync(sync_ping)
        checks["celery"] = "ok" if celery_res.get("status") == "ok" else f"fail:{celery_res}"
        ok = ok and (checks["celery"] == "ok")
    except Exception as e:  # pragma: no cover
        checks["celery"] = f"fail:{e}"
        ok = False

    # Postgres
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL)
        await conn.fetchval("select 1")
        await conn.close()
        checks["postgres"] = "ok"
    except Exception as e:  # pragma: no cover
        checks["postgres"] = f"fail:{e}"
        ok = False

    # OpenSearch cluster health (require green for prod; allow yellow in dev)
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{settings.OPENSEARCH_URL}/_cluster/health") as resp:
                status_code = resp.status
                data = await resp.json(content_type=None)
                state = data.get("status") if isinstance(data, dict) else "unknown"
                allowed = ["green"] if settings.ENV == "prod" else ["green", "yellow"]
                ok_state = state in allowed
                checks["opensearch"] = state if status_code == 200 else f"fail:{status_code}"
                ok = ok and ok_state and status_code == 200
    except Exception as e:  # pragma: no cover
        checks["opensearch"] = f"fail:{e}"
        ok = False

    # MinIO health (optionally bucket exists)
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{settings.MINIO_URL}/minio/health/ready") as resp:
                checks["minio"] = "ok" if resp.status == 200 else f"fail:{resp.status}"
                ok = ok and resp.status == 200
    except Exception as e:  # pragma: no cover
        checks["minio"] = f"fail:{e}"
        ok = False

    # Queue depth watchdog
    try:
        r = Redis.from_url(settings.REDIS_URL)
        depth = await r.llen("celery")
        await r.aclose()
        checks["queue_depth"] = depth
        if depth > settings.QUEUE_MAX_DEPTH:
            ok = False
    except Exception as e:
        logger.warning("Exception in ready.py: %s", str(e))
        pass

    # signcalc-service
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("http://signcalc:8002/healthz") as resp:
                checks["signcalc"] = "ok" if resp.status == 200 else f"fail:{resp.status}"
                ok = ok and resp.status == 200
    except Exception as e:  # pragma: no cover
        checks["signcalc"] = f"fail:{e}"
        ok = False
    
    # Authentication providers health
    try:
        from .auth_health import get_health_monitor
        
        health_monitor = get_health_monitor()
        auth_providers = {}
        
        for provider in ["azure", "google", "apple", "password"]:
            status = await health_monitor.check_provider_health(provider)
            auth_providers[provider] = status.value
        
        checks["auth_providers"] = auth_providers
        # Don't fail health check if providers are degraded (graceful degradation)
    except Exception as e:  # pragma: no cover
        checks["auth_providers"] = f"fail:{e}"
    
    # Supabase connectivity
    try:
        from .supabase_client import get_supabase_client
        
        supabase = get_supabase_client()
        # Just verify client can be created (connection test)
        checks["supabase"] = "ok"
    except Exception as e:  # pragma: no cover
        checks["supabase"] = f"fail:{e}"
        # Don't fail if Supabase not configured (optional in some setups)
    
    # Duo 2FA (optional)
    try:
        from .duo_client import get_duo_service
        
        duo_service = get_duo_service()
        checks["duo_2fa"] = "configured" if duo_service and duo_service.is_configured else "disabled"
    except Exception:  # pragma: no cover
        checks["duo_2fa"] = "disabled"

    contracts: dict[str, Any] = {}
    try:
        app = request.app  # type: ignore[union-attr]
        sha = getattr(app.state, "materials_contract_sha", None)
        if sha:
            contracts["materials"] = {"sha": sha}
    except Exception as e:
        logger.warning("Exception in ready.py: %s", str(e))
        pass

    result = {
        "service": settings.SERVICE_NAME,
        "status": "ok" if ok else "degraded",
        "checks": checks,
        "schema_version": settings.SCHEMA_VERSION,
        "deployment_id": settings.DEPLOYMENT_ID,
        "contracts": contracts,
    }
    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=1.0 if ok else 0.5,
        inputs={},
        intermediates=checks,
        outputs={"status": result["status"]},
        code_version=code_version,
        model_config=model_config,
    )


