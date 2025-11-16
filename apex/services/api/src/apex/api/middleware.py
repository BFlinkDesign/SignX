from __future__ import annotations

import os
import uuid
from typing import Callable
import time
import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from .metrics import REQUEST_LATENCY

# Context for correlating within a request
from contextvars import ContextVar

REQUEST_ID_VAR: ContextVar[str | None] = ContextVar("apex_request_id", default=None)


class RequestIDMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, header_name: str = "X-Request-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable):
        rid = request.headers.get(self.header_name) or str(uuid.uuid4())
        REQUEST_ID_VAR.set(rid)
        response: Response = await call_next(request)
        response.headers[self.header_name] = rid
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, env: str):
        super().__init__(app)
        self.env = env

    async def dispatch(self, request: Request, call_next: Callable):
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if self.env != "dev":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int = 5 * 1024 * 1024):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: Callable):
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > self.max_bytes:
            return Response(status_code=413)
        return await call_next(request)


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate JSON body size and basic structure before parsing."""
    
    def __init__(self, app, max_json_size: int = 2 * 1024 * 1024):
        super().__init__(app)
        self.max_json_size = max_json_size
    
    async def dispatch(self, request: Request, call_next: Callable):
        if request.method in ("POST", "PUT", "PATCH"):
            cl = request.headers.get("content-length")
            if cl and cl.isdigit() and int(cl) > self.max_json_size:
                return Response(status_code=413, content="JSON body too large")
        return await call_next(request)


class RequestTimingLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name
        self.logger = logging.getLogger("apex.api")

    async def dispatch(self, request: Request, call_next: Callable):
        t0 = time.perf_counter()
        response: Response = await call_next(request)
        dt = (time.perf_counter() - t0) * 1000.0
        rid = REQUEST_ID_VAR.get()
        route_obj = request.scope.get("route")
        route = route_obj.path if route_obj else request.url.path
        # record histogram in seconds
        try:
            REQUEST_LATENCY.labels(route=route, status=str(response.status_code)).observe(dt / 1000.0)
        except Exception as e:
            self.logger.debug("Failed to record request latency metric: %s", str(e))
        log = {
            "ts": int(time.time() * 1000),
            "level": "INFO",
            "service": self.service_name,
            "request_id": rid,
            "method": request.method,
            "route": route,
            "status": response.status_code,
            "latency_ms": round(dt, 2),
        }
        try:
            self.logger.info(json.dumps(log))
        except Exception as e:
            # Fallback if JSON serialization fails - log without JSON encoding
            self.logger.info("Request completed: %s %s -> %s (%s ms)",
                           request.method, route, response.status_code, round(dt, 2))
        return response
