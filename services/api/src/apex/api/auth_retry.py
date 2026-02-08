"""Retry utilities with exponential backoff for authentication operations."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, TypeVar

import structlog
from httpx import NetworkError
from httpx import TimeoutError as HTTPTimeoutError
from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)

T = TypeVar("T")

# Retry configuration for transient failures
RETRY_CONFIG = {
    "stop": stop_after_attempt(3),
    "wait": wait_exponential(multiplier=1, min=2, max=10),
    "retry": retry_if_exception_type((NetworkError, HTTPTimeoutError, asyncio.TimeoutError)),
    "before_sleep": before_sleep_log(logger, "WARNING"),
    "after": after_log(logger, "INFO"),
}


def retry_auth_operation(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator for retrying authentication operations.
    
    Automatically retries on transient failures with exponential backoff.
    
    Example:
        @retry_auth_operation
        async def oauth_sign_in(provider: str, ...):
            ...
    """
    return retry(**RETRY_CONFIG)(func)


async def retry_with_fallback(
    primary: Callable[[], T],
    fallbacks: list[Callable[[], T]],
    error_types: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Execute function with automatic fallback on failure.
    
    Tries primary function first, then falls back to alternatives.
    
    Args:
        primary: Primary function to try
        fallbacks: List of fallback functions
        error_types: Exception types that trigger fallback
    
    Returns:
        Result from successful function
    
    Raises:
        Last exception if all attempts fail
    """
    last_error: Exception | None = None
    
    # Try primary with retry
    try:
        decorated = retry_auth_operation(primary)
        return await decorated()
    except error_types as e:
        logger.warning("auth.retry.primary_failed", error=str(e))
        last_error = e
    
    # Try fallbacks
    for i, fallback in enumerate(fallbacks):
        try:
            logger.info("auth.retry.fallback_attempt", fallback_index=i)
            decorated = retry_auth_operation(fallback)
            result = await decorated()
            logger.info("auth.retry.fallback_success", fallback_index=i)
            return result
        except error_types as e:
            logger.warning("auth.retry.fallback_failed", fallback_index=i, error=str(e))
            last_error = e
    
    # All attempts failed
    if last_error:
        raise last_error
    raise Exception("All authentication attempts failed")


def log_retry_attempt(retry_state) -> None:
    """Log retry attempt for observability."""
    logger.warning(
        "auth.retry.attempt",
        attempt=retry_state.attempt_number,
        next_attempt_in=retry_state.next_action.sleep if retry_state.next_action else 0,
    )

