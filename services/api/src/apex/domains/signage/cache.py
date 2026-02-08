"""Thread-safe caching utilities for deterministic solvers."""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Callable, Hashable
from functools import wraps
from typing import Any


def _normalize_value(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, (tuple, list)):
        return tuple(_normalize_value(v) for v in value)
    if isinstance(value, dict):
        return tuple(sorted((k, _normalize_value(v)) for k, v in value.items()))
    return value


def _make_cache_key(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Hashable:
    normalized_args = tuple(_normalize_value(arg) for arg in args)
    normalized_kwargs = tuple(sorted((k, _normalize_value(v)) for k, v in kwargs.items()))
    return normalized_args, normalized_kwargs


def deterministic_cache(maxsize: int = 256) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """LRU cache decorator that normalises inputs for deterministic solvers.

    Ensures cached values are:

    * **Thread-safe** – uses a re-entrant lock around cache mutation.
    * **Deterministic** – floating point inputs are rounded to reduce cache key
      explosion while keeping solver outputs stable.
    * **Bounded** – least recently used eviction with configurable ``maxsize``.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        cache: OrderedDict[Hashable, Any] = OrderedDict()
        lock = threading.RLock()

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = _make_cache_key(args, kwargs)
            with lock:
                if key in cache:
                    value = cache.pop(key)
                    cache[key] = value
                    return value

            result = func(*args, **kwargs)

            with lock:
                cache[key] = result
                if len(cache) > maxsize:
                    cache.popitem(last=False)

            return result

        def cache_clear() -> None:
            with lock:
                cache.clear()

        wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
        return wrapper

    return decorator

