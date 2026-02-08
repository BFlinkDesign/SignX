from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import Any


def emit_event(event_type: str, **kwargs: Any) -> None:
    # Placeholder: in production, emit to structured logging / event store
    import structlog

    structlog.get_logger(__name__).info(f"event.{event_type}", **kwargs)


def instrument(event_name: str) -> Callable[[Callable], Callable]:
    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
            emit_event(event_name + ".started", **kwargs)
            t0 = time.perf_counter()
            try:
                res = await fn(*args, **kwargs)
                emit_event(
                    event_name + ".finished",
                    took_ms=int((time.perf_counter() - t0) * 1000),
                )
                return res
            except Exception as e:
                emit_event(event_name + ".failed", error=str(e))
                raise

        return wrapper  # type: ignore[return-value]

    return deco
