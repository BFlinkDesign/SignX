"""Shared utilities for importing signcalc-service modules with fallbacks."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")


def get_signcalc_import(module_name: str, function_name: str, fallback: Callable[..., T]) -> Callable[..., T]:
    """Import function from signcalc-service with fallback.
    
    Args:
        module_name: Module name (e.g., "apex_signcalc.anchors_baseplate")
        function_name: Function name (e.g., "design_anchors")
        fallback: Fallback function to use if import fails
    
    Returns:
        Imported function or fallback
    """
    # Add signcalc-service to path
    _signcalc_path = Path(__file__).parent.parent.parent.parent.parent / "signcalc-service"
    if str(_signcalc_path) not in sys.path:
        sys.path.insert(0, str(_signcalc_path))
    
    try:
        module = __import__(module_name, fromlist=[function_name])
        return getattr(module, function_name)
    except ImportError:
        return fallback

