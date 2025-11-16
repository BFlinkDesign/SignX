"""Redis client singleton for caching and idempotency."""

from __future__ import annotations

import structlog
from typing import Optional

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None  # type: ignore

from ..deps import settings

logger = structlog.get_logger(__name__)

_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> Optional[aioredis.Redis]:
    """Get singleton Redis client.
    
    Returns None if Redis unavailable or not configured.
    """
    global _client
    
    if aioredis is None:
        logger.warning("redis.not_available", reason="redis package not installed")
        return None
    
    if _client is None:
        try:
            _client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False,  # Keep bytes for raw caching
                socket_connect_timeout=2,
                socket_keepalive=True,
            )
            logger.info("redis.client_initialized", url=settings.REDIS_URL)
        except Exception as e:
            logger.warning("redis.client_failed", error=str(e))
            return None
    
    return _client


async def close_redis_client() -> None:
    """Close Redis client connection."""
    global _client
    if _client:
        await _client.aclose()
        _client = None
        logger.info("redis.client_closed")

