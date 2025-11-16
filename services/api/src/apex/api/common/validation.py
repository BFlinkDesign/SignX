"""Shared validation utilities for route handlers."""

from __future__ import annotations

from fastapi import HTTPException


def require_field(data: dict, field: str, field_type: type | None = None) -> any:
    """Require a field exists in data dict, raise 422 if missing.
    
    Args:
        data: Dict to check
        field: Field name to require
        field_type: Optional type to validate
    
    Returns:
        Field value
    
    Raises:
        HTTPException: 422 if field missing or invalid type
    """
    value = data.get(field)
    if value is None:
        raise HTTPException(status_code=422, detail=f"{field} is required")
    if field_type and not isinstance(value, field_type):
        raise HTTPException(status_code=422, detail=f"{field} must be {field_type.__name__}")
    return value


def validate_module(module: str) -> str:
    """Validate module name is in allowed list."""
    allowed = ["signage.single_pole", "signage.baseplate", "signage.direct_burial_2pole"]
    if module not in allowed:
        raise HTTPException(status_code=422, detail=f"Invalid module: {module}. Must be one of {allowed}")
    return module


def require_positive(value: float, name: str) -> float:
    """Require a positive numeric value."""
    if value <= 0:
        raise HTTPException(status_code=422, detail=f"{name} must be > 0")
    return value

