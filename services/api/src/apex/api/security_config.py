"""Central security configuration helpers (rate limits, throttling, etc.)."""

from functools import lru_cache
from typing import Dict

import structlog
from slowapi import Limiter
from slowapi.util import get_remote_address

from .deps import get_rate_limit_default

logger = structlog.get_logger(__name__)

# Per-endpoint overrides keyed by a stable identifier.
_RATE_LIMIT_OVERRIDES: Dict[str, str] = {
    "signcalc": "100/minute",
}


@lru_cache(maxsize=1)
def get_global_limiter() -> Limiter:
    """Lazily instantiate the SlowAPI limiter with default limits."""

    default_limit = get_rate_limit_default()
    logger.info("security.limiter.init", default_limit=default_limit)
    return Limiter(key_func=get_remote_address, default_limits=[default_limit])


def get_rate_limit(endpoint_key: str) -> str:
    """Resolve the rate limit string for a named endpoint."""

    limit = _RATE_LIMIT_OVERRIDES.get(endpoint_key, get_rate_limit_default())
    logger.debug("security.limiter.override", endpoint=endpoint_key, limit=limit)
    return limit

