"""Idempotency middleware for mutation endpoints."""

from __future__ import annotations

from hashlib import sha256

import orjson
import structlog
from fastapi import Request, Response, status
from fastapi.responses import ORJSONResponse

from .redis_client import get_redis_client

logger = structlog.get_logger(__name__)


async def enforce_idempotency(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
    """Middleware to enforce idempotency via Redis caching.
    
    Checks for Idempotency-Key header. If found, checks Redis cache.
    On cache hit: returns 200 with cached response.
    On cache miss: executes request and stores response in cache for 24h.
    """
    key = request.headers.get("Idempotency-Key")
    if not key:
        return await call_next(request)
    
    # Only apply to mutation methods
    if request.method not in ["POST", "PUT", "PATCH", "DELETE"]:
        return await call_next(request)
    
    # Create cache key from path + body hash + idempotency key
    body = await request.body()
    body_hash = sha256(body).hexdigest()[:16]
    cache_key = f"idem:{request.url.path}:{body_hash}:{key}"
    
    # Check Redis cache
    redis = await get_redis_client()
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                logger.info("idempotency.cache_hit", key=key, cache_key=cache_key)
                # Parse cached JSON bytes
                cached_data = orjson.loads(cached)
                return ORJSONResponse(content=cached_data, status_code=status.HTTP_200_OK)
            
            logger.debug("idempotency.cache_miss", key=key, cache_key=cache_key)
        except Exception as e:
            logger.warning("idempotency.redis_error", error=str(e))
    
    # Execute request
    response = await call_next(request)
    
    # Cache successful responses (2xx, 3xx) for 24 hours
    if redis and response.status_code < 400:
        try:
            # Get response body
            if hasattr(response, "body"):
                body_data = response.body
            else:
                body_data = await response.body()
            
            await redis.set(cache_key, body_data, ex=86400)
            logger.debug("idempotency.cached", key=key, ttl=86400)
        except Exception as e:
            logger.warning("idempotency.cache_failed", error=str(e))
    
    return response
