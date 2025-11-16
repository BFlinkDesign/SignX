from __future__ import annotations

import json
import os
import time
from hashlib import sha256
from typing import Any, Optional

import redis
import logging

logger = logging.getLogger(__name__)


def _redis() -> redis.Redis:
    url = os.getenv("APEX_REDIS_URL") or os.getenv("REDIS_URL") or "redis://cache:6379/0"
    return redis.from_url(url)


def idem_cache_get(route: str, body: bytes, key: str) -> Optional[dict[str, Any]]:
    r = _redis()
    cache_key = f"idem:{route}:{sha256(body).hexdigest()}:{key}"
    val = r.get(cache_key)
    if not val:
        return None
    try:
        return json.loads(val)
    except Exception as e:
        logger.warning("Exception in utils.py: %s", str(e))
        return None


def idem_cache_set(route: str, body: bytes, key: str, payload: dict[str, Any], ttl_seconds: int = 86400) -> None:
    r = _redis()
    cache_key = f"idem:{route}:{sha256(body).hexdigest()}:{key}"
    r.set(cache_key, json.dumps(payload, separators=(",", ":")), ex=ttl_seconds)


def dlq_push(queue: str, item: dict[str, Any]) -> None:
    r = _redis()
    r.lpush(f"dlq:{queue}", json.dumps(item, separators=(",", ":")))


def breaker_allow(name: str, threshold: int = 3, cool_off_seconds: int = 60) -> bool:
    r = _redis()
    state_key = f"breaker:{name}:state"
    if r.get(state_key):
        return False
    return True


def breaker_record_failure(name: str, threshold: int = 3, cool_off_seconds: int = 60) -> None:
    r = _redis()
    count_key = f"breaker:{name}:fail_count"
    state_key = f"breaker:{name}:state"
    new_count = r.incr(count_key)
    r.expire(count_key, 300)
    if new_count >= threshold:
        r.set(state_key, "open", ex=cool_off_seconds)


def breaker_record_success(name: str) -> None:
    r = _redis()
    r.delete(f"breaker:{name}:fail_count")


def backoff_delay(retry_number: int, base: float = 0.5, cap: float = 30.0) -> float:
    delay = min(cap, base * (2 ** max(retry_number, 0)))
    jitter = 0.1 * delay
    return delay + jitter


