"""
APEX Signage Engineering - Solver API Optimizations

Request coalescing, progressive enhancement, caching.
"""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

# Request coalescing cache (content_sha256 -> result)
_COALESCING_CACHE: OrderedDict[str, tuple[Any, float]] = OrderedDict()
_CACHE_MAX_SIZE = 1000
_COALESCING_WINDOW_MS = 100  # 100ms window


def compute_content_sha256(content: dict[str, Any]) -> str:
    """
    Compute SHA256 hash of request content for deduplication.
    
    Args:
        content: Request content dict
    
    Returns:
        SHA256 hex digest
    """
    # Serialize content deterministically
    import json
    
    content_str = json.dumps(content, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content_str.encode()).hexdigest()


def coalesce_request(
    content_sha256: str,
    solver_func: Callable,
    solver_args: tuple,
    solver_kwargs: dict[str, Any],
) -> Any:
    """
    Coalesce identical requests within 100ms window.
    
    Args:
        content_sha256: SHA256 of request content
        solver_func: Solver function to call
        solver_args: Positional arguments
        solver_kwargs: Keyword arguments
    
    Returns:
        Solver result (cached or computed)
    """
    current_time = time.perf_counter() * 1000  # ms
    
    # Check cache
    if content_sha256 in _COALESCING_CACHE:
        result, cached_time = _COALESCING_CACHE[content_sha256]
        age_ms = current_time - cached_time
        
        if age_ms < _COALESCING_WINDOW_MS:
            # Return cached result
            return result
        else:
            # Expired, remove
            del _COALESCING_CACHE[content_sha256]
    
    # Compute result
    result = solver_func(*solver_args, **solver_kwargs)
    
    # Cache result
    _COALESCING_CACHE[content_sha256] = (result, current_time)
    
    # Limit cache size (LRU)
    while len(_COALESCING_CACHE) > _CACHE_MAX_SIZE:
        _COALESCING_CACHE.popitem(last=False)
    
    return result


# ========== Progressive Enhancement ==========


class ProgressiveResult:
    """Result container for progressive enhancement."""
    
    def __init__(self, quick_estimate: Any, full_result: Any | None = None):
        self.quick_estimate = quick_estimate
        self.full_result = full_result
        self.is_complete = full_result is not None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for API response."""
        return {
            "quick_estimate": self.quick_estimate,
            "full_result": self.full_result,
            "is_complete": self.is_complete,
        }


def derive_loads_progressive(
    site: Any,
    cabinets: list[Any],
    height_ft: float,
    quick_only: bool = False,
) -> ProgressiveResult:
    """
    Progressive enhancement: Quick estimate + full analysis.
    
    Args:
        site: Site loads
        cabinets: Cabinet list
        height_ft: Height
        quick_only: If True, return only quick estimate (<50ms)
    
    Returns:
        ProgressiveResult with quick_estimate and optional full_result
    """
    from .solvers import derive_loads
    
    # Quick estimate: Simple area calculation
    area_ft2 = sum(c.width_ft * c.height_ft for c in cabinets)
    weight_lb = sum(c.width_ft * c.height_ft * c.weight_psf for c in cabinets)
    
    # Simplified moment estimate
    q_psf = 0.00256 * site.wind_speed_mph**2
    mu_estimate = (q_psf * area_ft2 * height_ft / 2.0) * 1.6 / 1000.0
    
    quick_estimate = {
        "a_ft2": round(area_ft2, 2),
        "weight_estimate_lb": round(weight_lb, 1),
        "mu_kipft_estimate": round(mu_estimate, 2),
    }
    
    if quick_only:
        return ProgressiveResult(quick_estimate)
    
    # Full analysis (slower, more accurate)
    full_result = derive_loads(site, cabinets, height_ft, seed=0)
    
    return ProgressiveResult(
        quick_estimate,
        full_result={
            "a_ft2": full_result.a_ft2,
            "z_cg_ft": full_result.z_cg_ft,
            "weight_estimate_lb": full_result.weight_estimate_lb,
            "mu_kipft": full_result.mu_kipft,
        },
    )

