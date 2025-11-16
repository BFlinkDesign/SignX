from __future__ import annotations

import socket
from typing import Any
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, ORJSONResponse, JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .deps import settings, get_model_config, get_code_version
from .schemas import ResponseEnvelope, TraceDataModel, TraceModel
from .metrics import setup_metrics
from .metrics import REQUEST_LATENCY
from .middleware import RequestIDMiddleware, SecurityHeadersMiddleware, BodySizeLimitMiddleware, RequestTimingLoggingMiddleware, RequestValidationMiddleware
from .ready import router as ready_router
from .routes.projects import router as projects_router
from .routes.site import router as site_router
from .routes.cabinets import router as cabinets_router
from .routes.poles import router as poles_router
from .routes.direct_burial import router as direct_burial_router
from .routes.baseplate import router as baseplate_router
from .routes.pricing import router as pricing_router


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="APEX API",
    version=settings.version,
    docs_url="/docs",
    openapi_url="/openapi.json",
)
app.state.limiter = limiter

# API versioning via header or query param
from fastapi import Header
from typing import Optional as Opt

def get_api_version(x_api_version: Opt[str] = Header(None, alias="X-API-Version")) -> str:
    """Extract API version from header or default to v1."""
    return x_api_version or "v1"
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware, env=settings.env)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(RequestValidationMiddleware)
app.add_middleware(RequestTimingLoggingMiddleware, service_name=settings.service_name)
origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Use unified build_envelope
from .common.utils import build_envelope as envelope


@app.get("/health", response_model=ResponseEnvelope)
async def health():
    host = socket.gethostname()
    res = {
        "service": settings.service_name,
        "status": "ok",
        "version": settings.version,
        "host": host,
        "schema_version": settings.schema_version,
        "deployment_id": settings.deployment_id,
    }
    return envelope(res, [], 1.0, {"env": settings.env}, {}, {"status": "ok"})


@app.get("/schemas/envelope.v1.json")
async def envelope_schema():
    from .schemas import ResponseEnvelope as _RE

    return ORJSONResponse(_RE.model_json_schema())


@app.get("/docs", include_in_schema=False)
async def docs():
    html = (
        """<!doctype html><html><head><meta charset=\"utf-8\"><title>APEX API Docs</title></head>"""
        """<body><script id=\"api-reference\" data-url=\"/openapi.json\"></script>"""
        """<script src=\"https://cdn.jsdelivr.net/npm/@scalar/api-reference/dist/browser/standalone.min.js\"></script></body></html>"""
    )
    return HTMLResponse(content=html)


app.include_router(ready_router)
app.include_router(projects_router)
app.include_router(site_router)
app.include_router(cabinets_router)
app.include_router(poles_router)
app.include_router(direct_burial_router)
app.include_router(baseplate_router)
app.include_router(pricing_router)
setup_metrics(app)


@app.exception_handler(RateLimitExceeded)
async def ratelimit_handler(request: Request, exc: RateLimitExceeded):
    env = envelope(
        result={"error": "rate_limited", "detail": str(exc)},
        assumptions=["rate_limited"],
        confidence=0.2,
        inputs={"path": request.url.path},
        intermediates={},
        outputs={},
    )
    headers = {"Retry-After": str(getattr(exc, "retry_after", 60))}
    return JSONResponse(env.model_dump(), status_code=429, headers=headers)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    env = envelope(
        result={"error": "http_error", "status_code": exc.status_code, "detail": exc.detail},
        assumptions=["http_exception"],
        confidence=0.5,
        inputs={"path": request.url.path},
        intermediates={},
        outputs={},
    )
    return JSONResponse(env.model_dump(), status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    env = envelope(
        result={"error": "validation_error", "detail": exc.errors()},
        assumptions=["validation_failed"],
        confidence=0.3,
        inputs={"path": request.url.path, "body": str(exc.body) if hasattr(exc, "body") else None},
        intermediates={},
        outputs={},
    )
    return JSONResponse(env.model_dump(), status_code=422)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    env = envelope(
        result={"error": "internal_error", "type": type(exc).__name__},
        assumptions=["unhandled_exception"],
        confidence=0.1,
        inputs={"path": request.url.path},
        intermediates={},
        outputs={},
    )
    return JSONResponse(env.model_dump(), status_code=500)


