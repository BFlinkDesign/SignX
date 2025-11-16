# APEX Signage Engineering Solvers - Failure Modes

## Overview

This document catalogs all known failure modes, their detection, and resolution strategies.

## Categories

### 1. Input Validation Failures

**Mode**: Invalid input parameters  
**Detection**: `ValueError` raised during validation  
**Examples**:
- Negative dimensions (width_ft < 0)
- Invalid wind speed (wind_speed_mph < 0)
- Zero or empty cabinet list (with non-zero height)

**Resolution**:
- Fix input values per error message
- Check input validation in `trace.data.inputs`
- Review edge case assumptions

### 2. Solver Convergence Failures

**Mode**: Optimization fails to converge  
**Detection**: `ConvergenceError` exception or `converged=False` in result  
**Examples**:
- GA exceeds max_generations without improvement
- Pareto optimization stalls

**Resolution**:
- Increase max_generations
- Reduce search space (tighter constraints)
- Use grid search fallback for small spaces
- Check for contradictory constraints

### 3. Edge Case Failures

**Mode**: Edge case detected requiring engineering review  
**Detection**: `abstain_with_recommendation()` returns confidence=0.0  
**Examples**:
- Eccentric loading > 0.5ft
- Combined wind + seismic exceeds limits
- Frost depth concerns
- Groundwater effects

**Resolution**:
- Follow recommendation in `assumptions` or `recommendation`
- Obtain geotechnical report if recommended
- Modify design to eliminate edge case
- Request engineering review

### 4. External Dependency Failures

**Mode**: Missing data or configuration  
**Detection**: Empty results or fallback to defaults  
**Examples**:
- AISC section database missing
- Training data unavailable (ML fallback to heuristics)
- Calibration constants not loaded

**Resolution**:
- Verify database connectivity
- Check data files exist
- Load required data
- Verify configuration

### 5. Numerical Failures

**Mode**: NaN/Inf in outputs  
**Detection**: `SolverError` raised, `detect_nan_inf()` returns fields  
**Examples**:
- Division by zero (empty cabinets, zero soil bearing)
- Extreme input values causing overflow
- Numerical instability in optimization

**Resolution**:
- Add input validation
- Check intermediate calculations
- Review unit conversions
- Report diagnostics to engineering team

### 6. Constraint Contradiction Failures

**Mode**: Contradictory constraints  
**Detection**: `ConstraintError` raised, `detect_contradictory_constraints()` returns issues  
**Examples**:
- min_plate_size > max_plate_size
- Variable bounds: min > max

**Resolution**:
- Fix constraint values
- Remove contradictory constraints
- Verify constraint logic

## Detection Functions

### `detect_nan_inf(outputs)`
Scans output dictionary recursively for NaN/Inf values.

### `detect_non_converged(optimization_result)`
Checks convergence flags, iteration counts, final fitness.

### `detect_contradictory_constraints(constraints, bounds)`
Validates constraint consistency.

### `generate_diagnostics(inputs, outputs, solver_name, error)`
Generates comprehensive diagnostics for troubleshooting.

## Troubleshooting Guide

### "Derive failed"
**Checks:**
1. Verify input ranges: wind_speed_mph >= 0, dimensions > 0
2. Check warnings in assumptions
3. Review input validation errors

**Resolution**: Fix input values per error message

### "No feasible poles"
**Checks:**
1. Verify mu_required_kipin is reasonable
2. Check steel grade/family filters
3. Review section database completeness

**Resolution**: 
- Increase available sections
- Relax constraints
- Consider custom pole design

### "Optimization timeout"
**Checks:**
1. Reduce search space
2. Increase improvement threshold
3. Check for contradictory constraints

**Resolution**:
- Use grid search fallback
- Increase max_generations
- Simplify design variables

### "NaN in outputs"
**Checks:**
1. Review input ranges for extremes
2. Check intermediate calculations
3. Verify unit conversions

**Resolution**:
- Add input validation
- Add intermediate checks
- Report to engineering team

## Diagnostic Mode

Set `APEX_SOLVER_DEBUG=1` to enable:

- Verbose logging of all intermediate steps
- Input/output snapshots
- Convergence plots (for optimization)
- Performance profiling data

Debug artifacts saved to:
- `/tmp/apex_solver_debug/`

## Monitoring

**Metrics:**
- Error rate by failure mode
- Convergence rate (optimization)
- NaN/Inf detection frequency
- Edge case frequency

**Alerts:**
- Error rate > 1%
- Convergence failures > 5%
- Frequent NaN/Inf detection

## Prevention

1. **Input Validation**: Validate all inputs before solver calls
2. **Edge Case Detection**: Run edge case checks early
3. **Constraint Validation**: Verify constraints before optimization
4. **Numerical Stability**: Use stable algorithms, avoid division by zero
5. **Testing**: Comprehensive test coverage for edge cases

