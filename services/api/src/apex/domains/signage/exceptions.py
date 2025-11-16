"""
Custom Exception Hierarchy for Signage Engineering Domain

Provides structured error handling with engineering context and code references.
All exceptions include metadata for audit trails and debugging.

Author: Claude Code
Date: 2025-11-02
"""

from typing import Any


class SignageEngineeringError(Exception):
    """
    Base exception for all signage engineering errors.

    Includes engineering context and code references for PE compliance.
    """

    def __init__(
        self,
        message: str,
        code_ref: str | None = None,
        **context: Any,
    ):
        """
        Initialize engineering error with context.

        Args:
            message: Human-readable error description
            code_ref: Reference to code section (e.g., "ASCE 7-22 Section 26.10")
            **context: Additional context data (inputs, intermediate values, etc.)
        """
        self.message = message
        self.code_ref = code_ref
        self.context = context

        # Build full message with code reference
        full_message = message
        if code_ref:
            full_message = f"{message} (Ref: {code_ref})"

        super().__init__(full_message)

    def __str__(self) -> str:
        """String representation with context."""
        base = super().__str__()
        if self.context:
            ctx_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{base} [{ctx_str}]"
        return base


class ValidationError(SignageEngineeringError):
    """
    Input validation error.

    Raised when user inputs are outside valid engineering ranges
    or violate code requirements.

    Examples:
        - Negative dimensions
        - Wind speed outside ASCE 7 range
        - Soil bearing pressure <= 0
    """

    pass


class CalculationError(SignageEngineeringError):
    """
    Calculation failure or convergence error.

    Raised when numerical methods fail to converge, iterative
    solvers exceed max iterations, or calculations produce
    physically impossible results.

    Examples:
        - Solver fails to converge
        - Division by zero in intermediate step
        - Result exceeds physical limits
    """

    pass


class DatabaseError(SignageEngineeringError):
    """
    Database query or data integrity error.

    Raised when database operations fail or return unexpected data.

    Examples:
        - AISC section not found
        - Missing calibration constant
        - Data integrity violation
    """

    pass


class ConfigurationError(SignageEngineeringError):
    """
    System configuration error.

    Raised when required configuration is missing or invalid.

    Examples:
        - Missing environment variable
        - Invalid code version
        - Service dependency unavailable
    """

    pass


class EngineeringLimitError(SignageEngineeringError):
    """
    Engineering limit exceeded.

    Raised when design requirements cannot be met within code limits
    or practical engineering constraints. Typically requires engineering
    review or alternative design approach.

    Examples:
        - Load exceeds maximum foundation capacity
        - Required depth exceeds practical limits
        - No viable section meets all criteria
    """

    pass
