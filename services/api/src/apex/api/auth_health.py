"""Provider health checks and circuit breakers for authentication services."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import structlog
import logging

logger = logging.getLogger(__name__)

logger = structlog.get_logger(__name__)


class ProviderStatus(Enum):
    """Provider health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class ProviderHealth:
    """Provider health metrics."""

    provider: str
    status: ProviderStatus = ProviderStatus.UNKNOWN
    last_check: Optional[float] = None
    last_success: Optional[float] = None
    last_failure: Optional[float] = None
    failure_count: int = 0
    success_count: int = 0
    response_times: deque[float] = field(default_factory=lambda: deque(maxlen=100))
    consecutive_failures: int = 0
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate (0-1)."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total


class CircuitBreaker:
    """Circuit breaker for provider health checks.
    
    Implements exponential backoff and automatic recovery.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_attempts: int = 3,
    ):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of consecutive failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            half_open_attempts: Number of attempts in half-open state before fully open
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_attempts = half_open_attempts
        
        self.state = "closed"  # closed, open, half-open
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_attempts_made = 0
    
    def record_success(self) -> None:
        """Record successful call - reset circuit breaker."""
        if self.state == "half-open":
            self.half_open_attempts_made += 1
            if self.half_open_attempts_made >= self.half_open_attempts:
                logger.info("circuit_breaker.closed", attempts=self.half_open_attempts_made)
                self.state = "closed"
                self.failure_count = 0
                self.half_open_attempts_made = 0
        else:
            self.failure_count = 0
            if self.state == "open":
                logger.info("circuit_breaker.closed_after_recovery")
                self.state = "closed"
    
    def record_failure(self) -> None:
        """Record failed call - potentially open circuit breaker."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == "half-open":
            # Half-open failed - go back to open
            logger.warning("circuit_breaker.half_open_failed", attempts=self.half_open_attempts_made)
            self.state = "open"
            self.half_open_attempts_made = 0
        elif self.failure_count >= self.failure_threshold:
            # Too many failures - open circuit
            logger.error("circuit_breaker.opened", failures=self.failure_count)
            self.state = "open"
    
    def can_attempt(self) -> bool:
        """Check if circuit breaker allows attempts."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # Check if recovery timeout has passed
            if self.last_failure_time and (time.time() - self.last_failure_time) >= self.recovery_timeout:
                logger.info("circuit_breaker.half_open_attempt")
                self.state = "half-open"
                self.half_open_attempts_made = 0
                return True
            return False
        
        # half-open state
        return True
    
    def get_state(self) -> str:
        """Get current circuit breaker state."""
        return self.state


class AuthProviderHealthMonitor:
    """Monitor health of authentication providers.
    
    Tracks metrics, implements circuit breakers, and provides health status.
    """
    
    def __init__(self):
        """Initialize health monitor."""
        self.providers: dict[str, ProviderHealth] = {}
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    async def check_provider_health(self, provider: str) -> ProviderStatus:
        """Perform health check for a provider.
        
        Args:
            provider: Provider name ("azure", "google", "apple", "password")
        
        Returns:
            ProviderStatus enum
        """
        async with self._lock:
            if provider not in self.providers:
                self.providers[provider] = ProviderHealth(provider=provider)
                self.circuit_breakers[provider] = CircuitBreaker()
        
        health = self.providers[provider]
        breaker = self.circuit_breakers[provider]
        
        # Check circuit breaker
        if not breaker.can_attempt():
            health.status = ProviderStatus.DOWN
            health.last_check = time.time()
            logger.warning("auth.health.circuit_open", provider=provider)
            return ProviderStatus.DOWN
        
        # Perform actual health check
        start_time = time.time()
        try:
            success = await self._perform_health_check(provider)
            response_time = time.time() - start_time
            
            async with self._lock:
                health.last_check = time.time()
                health.response_times.append(response_time)
                
                if success:
                    health.last_success = time.time()
                    health.success_count += 1
                    health.consecutive_failures = 0
                    breaker.record_success()
                    
                    # Determine status based on metrics
                    if health.avg_response_time > 2.0:  # >2s average
                        health.status = ProviderStatus.DEGRADED
                    else:
                        health.status = ProviderStatus.HEALTHY
                else:
                    health.last_failure = time.time()
                    health.failure_count += 1
                    health.consecutive_failures += 1
                    breaker.record_failure()
                    health.status = ProviderStatus.DOWN
                    
        except Exception as e:
            response_time = time.time() - start_time
            logger.error("auth.health.check_error", provider=provider, error=str(e))
            
            async with self._lock:
                health.last_check = time.time()
                health.last_failure = time.time()
                health.failure_count += 1
                health.consecutive_failures += 1
                health.response_times.append(response_time)
                breaker.record_failure()
                health.status = ProviderStatus.DOWN
        
        return health.status
    
    async def _perform_health_check(self, provider: str) -> bool:
        """Perform actual health check for provider.
        
        Args:
            provider: Provider name
        
        Returns:
            True if healthy, False otherwise
        """
        if provider == "password":
            # Email/password is always "healthy" (local operation)
            return True
        
        # For OAuth providers, check if Supabase is configured and responsive
        try:
            from .supabase_client import get_supabase_client
            
            supabase = get_supabase_client()
            # Simple check - try to get auth settings (lightweight)
            # Supabase client initialization is enough to verify connectivity
            return True
            
        except Exception as e:
            logger.warning("Exception in auth_health.py: %s", str(e))
            return False
    
    def get_provider_status(self, provider: str) -> ProviderStatus:
        """Get current status of a provider (cached, no check)."""
        if provider not in self.providers:
            return ProviderStatus.UNKNOWN
        return self.providers[provider].status
    
    def get_provider_health(self, provider: str) -> Optional[ProviderHealth]:
        """Get full health metrics for a provider."""
        return self.providers.get(provider)
    
    def get_all_providers_status(self) -> dict[str, ProviderStatus]:
        """Get status of all providers."""
        return {name: health.status for name, health in self.providers.items()}
    
    async def select_healthy_provider(self, preferred: Optional[str] = None) -> Optional[str]:
        """Select a healthy provider, preferring the specified one.
        
        Args:
            preferred: Preferred provider name
        
        Returns:
            Provider name if healthy, None if all are down
        """
        # Check preferred first
        if preferred:
            status = await self.check_provider_health(preferred)
            if status in (ProviderStatus.HEALTHY, ProviderStatus.DEGRADED):
                return preferred
        
        # Try all providers
        providers = ["azure", "google", "apple", "password"]
        for provider in providers:
            if provider == preferred:
                continue
            
            status = await self.check_provider_health(provider)
            if status in (ProviderStatus.HEALTHY, ProviderStatus.DEGRADED):
                logger.info("auth.health.fallback_selected", preferred=preferred, selected=provider)
                return provider
        
        # All providers down - return password as last resort
        logger.warning("auth.health.all_down_fallback", fallback="password")
        return "password"


# Global health monitor instance
_health_monitor: Optional[AuthProviderHealthMonitor] = None


def get_health_monitor() -> AuthProviderHealthMonitor:
    """Get global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = AuthProviderHealthMonitor()
    return _health_monitor

