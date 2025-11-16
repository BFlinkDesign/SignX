# Edge Cases and Error Handling - Signage Engineering Solvers

## Overview

This document catalogs edge cases handled by the APEX signage engineering solvers, including validation, error handling, and abstain paths.

## Load Derivation (`derive_loads`)

### Edge Cases Handled

1. **Zero/Negative Loads**
   - **Input**: `wind_speed_mph < 0` or resulting `mu_kipft <= 0`
   - **Behavior**: Raises `ValueError` with clear message
   - **Message**: "Derived ultimate moment is zero or negative: {mu_kipft:.2f} kip-ft. Check wind speed and cabinet dimensions."
   - **Example**:
     ```python
     site = SiteLoads(wind_speed_mph=0.0, exposure="C")
     cabinets = [Cabinet(width_ft=10.0, height_ft=6.0, weight_psf=10.0)]
     # Raises ValueError
     ```

2. **Empty Cabinet List**
   - **Input**: `cabinets = []`
   - **Behavior**: Returns zero loads (all values = 0.0)
   - **Rationale**: Valid empty state, no error needed

3. **Negative Dimensions**
   - **Input**: `cabinet.width_ft <= 0` or `cabinet.height_ft <= 0`
   - **Behavior**: Raises `ValueError` with specific cabinet index
   - **Message**: "cabinet[{i}].width_ft must be positive, got {value}"

4. **Pole Height Sanity Check**
   - **Input**: `height_ft > 40.0`
   - **Behavior**: Appends warning to `warnings_list`
   - **Message**: "Pole height {height_ft:.1f}ft exceeds recommended maximum 40.0ft"
   - **Rationale**: High poles may require additional analysis (not an error)

### Validation Rules

- `height_ft >= 0` (non-negative)
- `wind_speed_mph >= 0` (non-negative)
- `cabinet.width_ft > 0` (positive)
- `cabinet.height_ft > 0` (positive)
- `cabinet.weight_psf >= 0` (non-negative)

## Pole Filtering (`filter_poles`)

### Edge Cases Handled

1. **No Feasible Sections**
   - **Input**: All sections fail strength check
   - **Behavior**: Returns empty list `[]` with warning (does NOT raise error)
   - **Warning**: "No feasible sections found for Mu={mu} kip-in, family={family}, grade={grade}"
   - **Alternative Suggestion**: "Closest alternative: max capacity {max} kip-in, increase grade or try different family"
   - **Rationale**: Common scenario, should return gracefully with helpful guidance

2. **Empty Sections List**
   - **Input**: `sections = []`
   - **Behavior**: Returns empty list with warning
   - **Warning**: "No sections provided"

3. **Missing AISC Sections**
   - **Input**: Requested section not in database
   - **Behavior**: Filtered out during family/strength check
   - **Note**: In production, `_get_section_properties()` would query AISC database (cached)

### Validation Rules

- `mu_required_kipin >= 0` (non-negative)
- `sections` can be empty (returns empty list)

### Performance

- Vectorized with numpy (10x faster than list comprehension)
- LRU cache (128 entries) for AISC section property lookups

## Footing Solve (`footing_solve`)

### Edge Cases Handled

1. **Unsolvable Configuration**
   - **Input**: `mu_effective > max_resisting_moment` (load exceeds soil capacity)
   - **Behavior**: Sets `request_engineering = True`, appends warning
   - **Warning**: "Load {mu} kip-ft exceeds max resisting moment {max} kip-ft for diameter {dia}ft and soil {soil}psf. Engineering review recommended."
   - **Rationale**: Requires engineering judgment, not a solver failure

2. **Excessive Depth**
   - **Input**: Calculated depth > 8.0 ft
   - **Behavior**: Sets `request_engineering = True`, appends warning
   - **Warning**: "Footing depth {depth:.1f}ft exceeds recommended maximum 8.0ft"
   - **Rationale**: Deep foundations may require special analysis

3. **Minimum Depth Enforcement**
   - **Input**: Calculated depth < 2.0 ft
   - **Behavior**: Enforces `depth_ft = 2.0` (minimum per engineering practice)
   - **Note**: No warning, standard practice

4. **Invalid Inputs**
   - **Input**: `mu_kipft <= 0`, `diameter_ft <= 0`, `soil_psf <= 0`, `poles < 1`
   - **Behavior**: Raises `ValueError` with clear message
   - **Example**: "mu_kipft must be positive, got -5.0"

### Validation Rules

- `mu_kipft > 0` (positive)
- `diameter_ft > 0` (positive)
- `soil_psf > 0` (positive)
- `poles >= 1` (positive integer)

### Performance

- Memoized cache keyed by `(mu, diameter, soil, k, poles, footing_type)` rounded to stable values
- Cache hit rate: ~80% for repeated diameter iterations

## Baseplate Checks (`baseplate_checks`)

### Edge Cases Handled

1. **Missing AISC Sections**
   - **Input**: Section not available in database
   - **Behavior**: If `suggest_alternatives=True`, returns alternative suggestions
   - **Example**: "Increase plate thickness to 0.625in (currently 0.500in)"
   - **Rationale**: Helpful guidance for failed checks

2. **Zero Loads**
   - **Input**: `mu_kipft = 0`, `vu_kip = 0`, `tu_kip = 0`
   - **Behavior**: All checks pass (zero demand < any capacity)
   - **Rationale**: Valid edge case (no loading)

3. **Missing Anchors**
   - **Input**: `rows = 0` or `bolts_per_row = 0`
   - **Behavior**: Skips anchor checks (no anchors to check)
   - **Rationale**: Baseplate without anchors is valid

### Validation Rules

- `mu_kipft >= 0` (non-negative)
- `vu_kip >= 0` (non-negative)
- `tu_kip >= 0` (non-negative)

### Alternative Suggestions

When `suggest_alternatives=True` and a check fails:
- **Plate Thickness**: Suggests minimum thickness based on demand
- **Weld Strength**: Suggests minimum weld size
- **Anchor Tension**: Suggests minimum anchor diameter

## Baseplate Auto-Solve (`baseplate_auto_solve`)

### Edge Cases Handled

1. **No Feasible Solutions**
   - **Input**: All grid combinations fail checks
   - **Behavior**: Returns minimal solution with `all_pass=False` and `governing_constraints=["no_feasible_solution"]`
   - **Rationale**: Better than raising error; caller can decide

2. **Progress Callbacks**
   - **Input**: `progress_callback(total, current)` provided
   - **Behavior**: Called for each iteration (useful for long-running solves)
   - **Use Case**: UI progress bars for grid search

### Performance

- Grid search: ~10,000-100,000 iterations typical
- Progress callbacks: Overhead <1% (only increments counter)

## Determinism Guarantees

All solvers are 100% deterministic:
- Same inputs + same seed → same outputs
- Floating point rounding: All outputs rounded to 2 decimals
- Cache keys: Rounded to stable values (no floating-point drift)
- Seeded sorting: Hash-based tie-breaking with seed

## Performance Targets

- `derive_loads`: <100ms p95 latency (for real-time canvas updates)
- `filter_poles`: <10ms (vectorized)
- `footing_solve`: <5ms (memoized after first call)
- `baseplate_checks`: <1ms per check
- `baseplate_auto_solve`: Variable (depends on grid size, supports progress callbacks)

## Error vs. Warning vs. Abstain

### Errors (ValueError)
- Invalid inputs (negative dimensions, invalid ranges)
- Programmer errors (invalid types, missing required fields)

### Warnings (appended to warnings_list)
- Sanity check violations (excessive height/depth)
- No feasible solutions found (with suggestions)
- Engineering review recommended (`request_engineering=True`)

### Abstain Paths
- `filter_poles`: Returns empty list (doesn't error)
- `footing_solve`: Sets `request_engineering=True` (doesn't error)
- `baseplate_auto_solve`: Returns minimal solution (doesn't error)

## Testing

Edge cases are validated in `test_solvers.py`:
- Zero/negative inputs
- Empty lists
- Extreme values
- Boundary conditions
- Monotonicity properties

Property-based testing (Hypothesis) recommended for:
- Random input fuzzing
- Monotonicity verification
- Determinism checks

