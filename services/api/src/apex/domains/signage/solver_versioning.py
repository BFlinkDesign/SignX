"""
APEX Signage Engineering - Solver Versioning

Track solver function versions for A/B testing and traceability.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

# Solver version registry
_SOLVER_VERSIONS: dict[str, str] = {
    "derive_loads": "1.2.0",
    "filter_poles": "1.1.0",
    "footing_solve": "1.3.0",
    "baseplate_checks": "1.2.0",
    "baseplate_auto_solve": "1.0.0",
    "pareto_optimize_poles": "1.0.0",
    "baseplate_optimize_ga": "1.0.0",
    "predict_initial_config": "1.0.0",
    "detect_unusual_config": "1.0.0",
    "dynamic_load_analysis": "1.0.0",
    "fatigue_analysis": "1.0.0",
    "connection_design": "1.0.0",
    "monte_carlo_reliability": "1.0.0",
    "sensitivity_analysis": "1.0.0",
}


def solver_version(version: str):
    """
    Decorator to tag solver functions with version.
    
    Usage:
        @solver_version("1.2.0")
        def my_solver(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        _SOLVER_VERSIONS[func.__name__] = version
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def get_solver_versions(called_functions: list[str] | None = None) -> dict[str, str]:
    """
    Get solver versions for traceability.
    
    Args:
        called_functions: Optional list of function names called in this request
    
    Returns:
        Dict of {function_name: version}
    """
    if called_functions:
        return {name: _SOLVER_VERSIONS.get(name, "unknown") for name in called_functions}
    return _SOLVER_VERSIONS.copy()


def get_solver_version(function_name: str) -> str:
    """Get version for a specific solver function."""
    return _SOLVER_VERSIONS.get(function_name, "unknown")

