"""Circuit breaker pattern for resilient service calls."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

import structlog

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: int = 60  # Seconds before attempting recovery
    half_open_attempts: int = 3  # Successful attempts to fully close
    success_threshold: int = 2  # Successes in half-open to close


class CircuitBreaker:
    """Circuit breaker implementation with exponential backoff.
    
    Prevents cascading failures by temporarily blocking requests
    to failing services.
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """Initialize circuit breaker.
        
        Args:
            name: Service name for logging
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_attempts = 0
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable[[], Any]) -> Any:
        """Execute function with circuit breaker protection.
        
        Args:
            func: Async function to call
        
        Returns:
            Function result
        
        Raises:
            CircuitBreakerOpen: If circuit is open
        """
        async with self._lock:
            # Check if circuit is open
            if self.state == CircuitState.OPEN:
                if self._should_attempt_recovery():
                    logger.info("circuit_breaker.half_open", name=self.name)
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_attempts = 0
                    self.success_count = 0
                else:
                    remaining = int(self.config.recovery_timeout - (time.time() - (self.last_failure_time or 0)))
                    raise CircuitBreakerOpen(
                        f"Circuit breaker open for {self.name}. "
                        f"Retry in {remaining}s"
                    )
        
        # Execute function
        try:
            result = await func() if asyncio.iscoroutinefunction(func) else func()
            
            # Record success
            async with self._lock:
                await self._record_success()
            
            return result
            
        except Exception as e:
            # Record failure
            async with self._lock:
                await self._record_failure()
            
            raise
    
    async def _record_success(self) -> None:
        """Record successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            self.half_open_attempts += 1
            
            if self.success_count >= self.config.success_threshold:
                logger.info("circuit_breaker.closed", name=self.name, attempts=self.half_open_attempts)
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.half_open_attempts = 0
                self.success_count = 0
        else:
            # Normal operation - reset failure count
            self.failure_count = 0
    
    async def _record_failure(self) -> None:
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # Half-open failed - go back to open
            logger.warning("circuit_breaker.half_open_failed", name=self.name)
            self.state = CircuitState.OPEN
            self.half_open_attempts = 0
            self.success_count = 0
        elif self.failure_count >= self.config.failure_threshold:
            # Too many failures - open circuit
            logger.error("circuit_breaker.opened", name=self.name, failures=self.failure_count)
            self.state = CircuitState.OPEN
    
    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if not self.last_failure_time:
            return False
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.config.recovery_timeout
    
    def get_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return self.state
    
    def reset(self) -> None:
        """Manually reset circuit breaker (admin operation)."""
        logger.info("circuit_breaker.manual_reset", name=self.name)
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.half_open_attempts = 0


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    
    pass


# Global circuit breakers for different services
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Get or create circuit breaker for a service.
    
    Args:
        name: Service name
        config: Optional configuration
    
    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]

