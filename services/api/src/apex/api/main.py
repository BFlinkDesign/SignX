from __future__ import annotations

import os
import socket
import uuid
from typing import Any

import structlog
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, ORJSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .schemas import CodeVersionModel, ModelConfigModel, ResponseEnvelope  # Must import first for forward refs
from .common.models import make_envelope
from .common.redis_client import close_redis_client
from .common.idem import enforce_idempotency
from .deps import get_code_version, get_model_config, settings, get_rate_limit_default
from .error_handlers import unhandled_exception_handler, validation_exception_handler
from .metrics import ABSTAIN_TOTAL, setup_metrics
from .startup_checks import validate_prod_requirements
from .contract_lock import ensure_materials_contract
from .tracing import setup_tracing
from .middleware import BodySizeLimitMiddleware
from .ready import router as ready_router
from .routes.auth import router as auth_router
from .routes.materials import router as materials_router
from .routes.projects import router as projects_router
from .routes.site import router as site_router
from .routes.cabinets import router as cabinets_router
from .routes.poles import router as poles_router
from .routes.direct_burial import router as burial_router
from .routes.baseplate import router as baseplate_router
from .routes.cantilever import router as cantilever_router
from .routes.pricing import router as pricing_router
from .routes.submission import router as submission_router
from .routes.files import router as files_router
from .routes.payloads import router as payloads_router
from .routes.concrete import router as concrete_router
from .routes.bom import router as bom_router
from .routes.tasks import router as tasks_router
from .routes.signcalc import router as signcalc_router
from .routes.uploads import router as uploads_router
from .routes.compliance import router as compliance_router
from .routes.crm import router as crm_router
from .routes.audit import router as audit_router
from .routes.cad_export import router as cad_export_router
from .routes.ai import router as ai_router


logger = structlog.get_logger(__name__)


# Initialize Sentry for error tracking (if configured)
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    
    if settings.ENV == "prod":
        sentry_sdk.init(
            dsn=os.getenv("SENTRY_DSN"),
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
            environment=settings.ENV,
        )
        logger.info("sentry.initialized", env=settings.ENV)
except (ImportError, AttributeError):
    pass


# build_envelope removed - use make_envelope from common.models instead


app = FastAPI(title="APEX API", default_response_class=ORJSONResponse)
app.add_middleware(BodySizeLimitMiddleware)

# Idempotency middleware (early, before rate limiting)
app.middleware("http")(enforce_idempotency)

# CORS - default deny; allowlist via env
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)


# Rate limiting (per-user via JWT or per-IP fallback)
def rate_key_func(request: Request):  # type: ignore[no-untyped-def]
    """Rate limit key function: prefer user_id from JWT, fallback to IP."""
    # Try to extract user_id from JWT token (if auth middleware is active)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from ..auth import get_current_user
            # Would need to decode JWT here - simplified for now
            # In production, extract user_id from token payload
            pass
        except Exception as e:
            logger.warning("Exception in main.py: %s", str(e))
            pass
    
    # Fallback to IP or API key
    token = request.headers.get("x-apex-key")
    return token or get_remote_address(request)


# Default: 100 req/min per user (configurable)
limiter = Limiter(key_func=rate_key_func, default_limits=[get_rate_limit_default()])
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def ratelimit_handler(_request, _exc):  # type: ignore[no-untyped-def]
    return ORJSONResponse(status_code=429, content={"detail": "rate limit exceeded"})


@app.middleware("http")
async def add_request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
    trace_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["x-trace-id"] = trace_id
    return response


@app.get("/health", response_model=ResponseEnvelope, responses={
    200: {
        "content": {
            "application/json": {
                "example": {
                    "result": {"service": "api", "status": "ok", "version": "0.1.0", "host": "host", "schema_version": "v1", "deployment_id": "dev"},
                    "assumptions": [],
                    "confidence": 1.0,
                    "trace": {
                        "data": {"inputs": {"env": "dev"}, "intermediates": {}, "outputs": {"status": "ok"}},
                        "code_version": {"git_sha": "dev", "dirty": False},
                        "model_config": {"provider": "none", "model": "none", "temperature": 0.0, "max_tokens": 1024, "seed": None}
                    }
                }
            }
        }
    }
})
async def health(
    model_config=Depends(get_model_config),
    code_version=Depends(get_code_version),
):
    hostname = socket.gethostname()
    result = {
        "service": settings.SERVICE_NAME,
        "status": "ok",
        "version": settings.APP_VERSION,
        "host": hostname,
        "schema_version": settings.SCHEMA_VERSION,
        "deployment_id": settings.DEPLOYMENT_ID,
    }
    assumptions: list[str] = []
    env_inputs: dict[str, Any] = {"env": settings.ENV}
    intermediates: dict[str, Any] = {}
    outputs: dict[str, Any] = {"status": "ok"}
    logger.info("health", service=settings.SERVICE_NAME, env=settings.ENV)
    return make_envelope(
        result=result,
        assumptions=assumptions,
        confidence=1.0,
        inputs=env_inputs,
        intermediates=intermediates,
        outputs=outputs,
        code_version=code_version,
        model_config=model_config,
    )


@app.get("/version", response_model=ResponseEnvelope, responses={
    200: {
        "content": {
            "application/json": {
                "example": {
                    "result": {"version": "0.1.0"},
                    "assumptions": [],
                    "confidence": 1.0,
                    "trace": {
                        "data": {"inputs": {}, "intermediates": {}, "outputs": {"version": "0.1.0"}},
                        "code_version": {"git_sha": "dev", "dirty": False},
                        "model_config": {"provider": "none", "model": "none", "temperature": 0.0, "max_tokens": 1024, "seed": None}
                    }
                }
            }
        }
    }
})
async def version(
    model_config=Depends(get_model_config),
    code_version=Depends(get_code_version),
):
    result = {"version": settings.APP_VERSION}
    return make_envelope(
        result=result,
        assumptions=[],
        confidence=1.0,
        inputs={},
        intermediates={},
        outputs=result,
        code_version=code_version,
        model_config=model_config,
    )


# Register custom exception handlers
from fastapi.exceptions import RequestValidationError
import logging

logger = logging.getLogger(__name__)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


# Envelope JSON schema endpoint (versioned)
@app.get("/schemas/envelope.v1.json")
async def envelope_schema():  # type: ignore[no-untyped-def]
    from .schemas import ResponseEnvelope as _RE

    return ORJSONResponse(_RE.model_json_schema())


# Minimal Scalar docs at /docs (Redoc still at /redoc)
@app.get("/docs", include_in_schema=False)
async def scalar_docs():  # type: ignore[no-untyped-def]
    html = f"""
    <!doctype html>
    <html>
      <head><meta charset=\"utf-8\"><title>APEX API Docs</title></head>
      <body>
        <script id=\"api-reference\" data-url=\"/openapi.json\"></script>
        <script src=\"https://cdn.jsdelivr.net/npm/@scalar/api-reference/dist/browser/standalone.min.js\"></script>
      </body>
    </html>
    """
    return HTMLResponse(content=html)


# Metrics
setup_metrics(app)


# Include readiness router
app.include_router(ready_router)

# Include auth router
app.include_router(auth_router)

# Include materials gateway router
app.include_router(materials_router, tags=["materials"])

# Include projects router
app.include_router(projects_router, tags=["projects"])

# Include site router
app.include_router(site_router, tags=["site"])

# Include cabinets router
app.include_router(cabinets_router, tags=["cabinets"])

# Include poles router
app.include_router(poles_router, tags=["poles"])

# Include foundation routers
app.include_router(burial_router, tags=["foundation"])
app.include_router(baseplate_router, tags=["foundation"])

# Include cantilever router for cantilever sign analysis
app.include_router(cantilever_router, tags=["cantilever"])

# Include pricing and submission routers
app.include_router(pricing_router, tags=["pricing"])
app.include_router(submission_router, tags=["submission"])

# Include signcalc router
app.include_router(signcalc_router, tags=["signcalc"])

# Include new routers
app.include_router(uploads_router, tags=["uploads"])
app.include_router(compliance_router, tags=["compliance"])
app.include_router(crm_router, tags=["crm"])
app.include_router(audit_router, tags=["audit"])

# Include files router
app.include_router(files_router, tags=["files"])

# Include payloads and utilities routers
app.include_router(payloads_router, tags=["payloads"])
app.include_router(concrete_router, tags=["utilities"])

# Include BOM router
app.include_router(bom_router, tags=["bom"])

# Include tasks router
app.include_router(tasks_router, tags=["tasks"])

# Include CAD export router
app.include_router(cad_export_router, tags=["cad-export"])

# Include AI/ML prediction router
app.include_router(ai_router, tags=["ai-ml"])


# Tracing last to ensure provider in place
setup_tracing()
# Startup hooks
@app.on_event("startup")
async def _startup_checks():  # type: ignore[no-untyped-def]
    validate_prod_requirements()


@app.on_event("startup")
async def _startup_contract_lock():  # type: ignore[no-untyped-def]
    try:
        sha = ensure_materials_contract()
        app.state.materials_contract_sha = sha
    except Exception as e:  # pragma: no cover
        app.state.materials_contract_sha = f"error:{e}"


@app.on_event("startup")
async def _startup_metrics_background():  # type: ignore[no-untyped-def]
    """Start background metrics collection task."""
    import asyncio
    import asyncpg
    from redis.asyncio import Redis
    from .metrics import CELERY_QUEUE_DEPTH, PG_POOL_USED, CACHE_HIT_RATIO
    
    async def update_runtime_metrics():
        # Queue depth
        try:
            r = Redis.from_url(settings.REDIS_URL)
            depth = await r.llen("celery")
            await r.aclose()
            CELERY_QUEUE_DEPTH.set(depth)
        except Exception as e:
            logger.warning("Exception in main.py: %s", str(e))
            pass
        
        # PG pool usage
        pool = getattr(app.state, "pg_pool", None)
        if isinstance(pool, asyncpg.Pool):
            try:
                size = pool.get_size()
                idle = pool.get_idle_count()
                PG_POOL_USED.set(max(size - idle, 0))
            except Exception as e:
                logger.warning("Exception in main.py: %s", str(e))
                pass
        
        # Cache hit ratio
        try:
            CACHE_HIT_RATIO.set(-1)
        except Exception as e:
            logger.warning("Exception in main.py: %s", str(e))
            pass
    
    async def metrics_background_loop():
        while True:
            await update_runtime_metrics()
            await asyncio.sleep(10)
    
    app.state.metrics_task = asyncio.create_task(metrics_background_loop())


@app.on_event("shutdown")
async def _shutdown_cleanup():  # type: ignore[no-untyped-def]
    """Cleanup resources on shutdown."""
    await close_redis_client()
    logger.info("shutdown.complete")


