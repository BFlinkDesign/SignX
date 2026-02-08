"""
APEX Signage Engineering - Failure Mode Analysis

Detect and handle solver failures with diagnostics.
"""

from __future__ import annotations

import math
from typing import Any


class SolverError(Exception):
    """Base exception for solver errors."""
    pass


class ConvergenceError(SolverError):
    """Raised when optimization fails to converge."""
    pass


class ConstraintError(SolverError):
    """Raised when constraints are contradictory."""
    pass


class SolverFailureDetector:
    """Detects various failure modes in solver outputs."""
    
    def detect_nan_inf(self, outputs: dict[str, Any]) -> list[str]:
        """
        Detect NaN/Inf in outputs.
        
        Args:
            outputs: Output dictionary
        
        Returns:
            List of field names containing NaN/Inf
        """
        failures = []
        
        def check_value(value: Any, path: str) -> None:
            if isinstance(value, (int, float)):
                if math.isnan(value) or math.isinf(value):
                    failures.append(path)
            elif isinstance(value, dict):
                for k, v in value.items():
                    check_value(v, f"{path}.{k}")
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    check_value(item, f"{path}[{i}]")
        
        for key, value in outputs.items():
            check_value(value, key)
        
        return failures
    
    def detect_non_converged(self, optimization_result: dict[str, Any]) -> bool:
        """
        Detect non-converged optimization.
        
        Args:
            optimization_result: Result from optimization
        
        Returns:
            True if non-converged
        """
        # Check for convergence flags
        if "converged" in optimization_result:
            return not optimization_result["converged"]
        
        # Check for excessive iterations
        if "iterations" in optimization_result and "max_iterations" in optimization_result:
            if optimization_result["iterations"] >= optimization_result["max_iterations"]:
                return True
        
        # Check for high final fitness (may indicate non-convergence)
        if "final_fitness" in optimization_result:
            if optimization_result["final_fitness"] > 1000.0:  # Threshold
                return True
        
        return False
    
    def detect_contradictory_constraints(
        self,
        constraints: dict[str, Any],
        variable_bounds: dict[str, tuple[float, float]],
    ) -> list[str]:
        """
        Detect contradictory constraints.
        
        Args:
            constraints: Constraint dict
            variable_bounds: Variable bounds {name: (min, max)}
        
        Returns:
            List of contradictory constraint descriptions
        """
        contradictions = []
        
        # Example: min_plate_size > max_plate_size
        if "min_plate_size_in" in constraints and "max_plate_size_in" in constraints:
            if constraints["min_plate_size_in"] > constraints["max_plate_size_in"]:
                contradictions.append(
                    f"min_plate_size ({constraints['min_plate_size_in']}) > "
                    f"max_plate_size ({constraints['max_plate_size_in']})"
                )
        
        # Check variable bounds
        for var_name, (min_val, max_val) in variable_bounds.items():
            if min_val > max_val:
                contradictions.append(f"{var_name}: min ({min_val}) > max ({max_val})")
        
        return contradictions
    
    def generate_diagnostics(
        self,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        solver_name: str,
        error: Exception | None = None,
    ) -> dict[str, Any]:
        """
        Generate diagnostics for troubleshooting.
        
        Args:
            inputs: Input parameters
            outputs: Output values
            solver_name: Name of solver function
            error: Optional exception that occurred
        
        Returns:
            Diagnostics dict
        """
        diagnostics = {
            "solver": solver_name,
            "inputs_summary": {k: str(v)[:50] for k, v in inputs.items()},
            "outputs_summary": {k: str(v)[:50] for k, v in outputs.items()},
            "nan_inf_fields": self.detect_nan_inf(outputs),
            "error": str(error) if error else None,
        }
        
        # Add solver-specific diagnostics
        if solver_name == "filter_poles":
            diagnostics["feasible_count"] = len(outputs.get("options", []))
        
        if solver_name == "footing_solve":
            diagnostics["depth_ft"] = outputs.get("depth_ft", None)
            diagnostics["request_engineering"] = outputs.get("request_engineering", False)
        
        return diagnostics


# ========== Troubleshooting Guide ==========


TROUBLESHOOTING_GUIDE = {
    "derive_failed": {
        "symptoms": ["ValueError raised", "Zero or negative loads"],
        "checks": [
            "Verify input ranges: wind_speed_mph >= 0, cabinet dimensions > 0",
            "Check warnings in assumptions list",
            "Review input validation errors in trace.data.inputs",
        ],
        "resolution": "Fix input values and retry. Check edge case handling in assumptions.",
    },
    "no_feasible_poles": {
        "symptoms": ["Empty options list", "Warnings about no feasible sections"],
        "checks": [
            "Verify mu_required_kipin is reasonable for available sections",
            "Check steel grade and family filters",
            "Review section database completeness",
        ],
        "resolution": [
            "Increase available sections in database",
            "Relax constraints (family, grade)",
            "Consider custom pole design",
        ],
    },
    "optimization_timeout": {
        "symptoms": ["Optimization exceeds max_generations", "Non-converged result"],
        "checks": [
            "Reduce search space (tighter constraints)",
            "Increase improvement threshold",
            "Check for contradictory constraints",
        ],
        "resolution": [
            "Use grid search fallback for small search spaces",
            "Increase max_generations for complex problems",
            "Simplify design variables",
        ],
    },
    "nan_in_outputs": {
        "symptoms": ["NaN or Inf in output values", "SolverError raised"],
        "checks": [
            "Review input ranges for extreme values",
            "Check intermediate calculations for division by zero",
            "Verify unit conversions",
        ],
        "resolution": [
            "Add input validation",
            "Add intermediate checks",
            "Report diagnostics to engineering team",
        ],
    },
}


def get_troubleshooting_advice(failure_type: str) -> dict[str, Any]:
    """
    Get troubleshooting advice for failure type.
    
    Args:
        failure_type: Type of failure
    
    Returns:
        Troubleshooting guide entry
    """
    return TROUBLESHOOTING_GUIDE.get(failure_type, {
        "symptoms": [],
        "checks": ["Review solver diagnostics"],
        "resolution": "Contact engineering support",
    })

