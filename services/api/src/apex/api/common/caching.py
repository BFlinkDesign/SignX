"""Query result caching utilities."""

from __future__ import annotations

import json
from collections.abc import Callable
from functools import wraps
from hashlib import sha256
from typing import Any, TypeVar

import structlog

from .redis_client import get_redis_client

logger = structlog.get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def cache_result(ttl_seconds: int = 3600, key_prefix: str = "cache"):
    """Decorator to cache function results in Redis.
    
    Args:
        ttl_seconds: Cache TTL in seconds
        key_prefix: Prefix for cache keys
        
    Example:
        @cache_result(ttl_seconds=3600, key_prefix="poles")
        async def get_pole_options(...):
            ...
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Build cache key from function name + args
            key_parts = [key_prefix, func.__name__]
            
            # Add keyword arguments to key
            for k, v in sorted(kwargs.items()):
                if v is not None:
                    key_parts.append(f"{k}:{v}")
            
            # Add positional args
            for i, arg in enumerate(args):
                if arg is not None:
                    key_parts.append(f"arg{i}:{arg}")
            
            cache_key = ":".join(str(p) for p in key_parts)
            cache_key_hash = sha256(cache_key.encode()).hexdigest()[:16]
            final_key = f"{key_prefix}:{cache_key_hash}"
            
            # Try to get from cache
            redis = await get_redis_client()
            if redis:
                try:
                    cached = await redis.get(final_key)
                    if cached:
                        logger.debug("cache.hit", key=final_key, ttl=ttl_seconds)
                        # Parse cached JSON
                        return json.loads(cached.decode("utf-8"))
                except Exception as e:
                    logger.warning("cache.get_failed", key=final_key, error=str(e))
            
            # Cache miss - execute function
            logger.debug("cache.miss", key=final_key)
            result = await func(*args, **kwargs)
            
            # Store in cache
            if redis:
                try:
                    # Serialize result to JSON
                    result_json = json.dumps(result, default=str)
                    await redis.set(final_key, result_json.encode("utf-8"), ex=ttl_seconds)
                    logger.debug("cache.stored", key=final_key, ttl=ttl_seconds)
                except Exception as e:
                    logger.warning("cache.set_failed", key=final_key, error=str(e))
            
            return result
        
        return wrapper  # type: ignore
    
    return decorator

