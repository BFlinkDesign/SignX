# APEX Signage Engineering - Advanced Features (Iteration 3)

## Overview

Advanced solvers with multi-objective optimization, AI recommendations, structural analysis, calibration, documentation, and batch processing.

## Module Structure

```
services/api/src/apex/domains/signage/
├── solvers.py              # Core deterministic solvers (Iteration 1-2)
├── optimization.py          # Multi-objective optimization, GA
├── ml_models.py            # AI recommendations, anomaly detection
├── structural_analysis.py  # Dynamic loads, fatigue, connections
├── calibration.py          # Monte Carlo, sensitivity analysis
├── engineering_docs.py     # Calculation sheets, load diagrams
└── batch.py                # Batch processing
```

## 1. Multi-Objective Optimization (`optimization.py`)

### `pareto_optimize_poles()`

Multi-objective Pareto optimization using NSGA-II algorithm.

**Objectives:**
1. Minimize cost (weight × cost_per_lb × height)
2. Minimize weight (total pole weight)
3. Maximize safety_factor (capacity / demand)

**Usage:**
```python
from apex.domains.signage.optimization import pareto_optimize_poles

solutions = pareto_optimize_poles(
    mu_required_kipin=50.0,
    sections=sections,
    prefs={"family": "HSS", "steel_grade": "A500B"},
    height_ft=25.0,
    max_solutions=10,
    seed=42,
)

# Returns List[ParetoSolution] with:
# - pole: PoleOption
# - cost, weight, safety_factor
# - is_dominated: bool
```

**Integration:**
- Agent 2: Add `?optimize=pareto` query param to `POST /poles/options`
- Return `trace.pareto_frontier=[...]` in Envelope

### `baseplate_optimize_ga()`

Genetic algorithm for baseplate optimization (replaces grid search).

**Performance:**
- Grid search: O(n³), ~10-30s
- GA: Converges in <5s, 50%+ faster

**Constraints:**
- safety_factor >= 2.0
- anchor_spacing >= 6"

**Usage:**
```python
from apex.domains.signage.optimization import baseplate_optimize_ga

def progress_cb(generation, fitness):
    print(f"Generation {generation}: best fitness = {fitness:.2f}")

plate, cost = baseplate_optimize_ga(
    loads={"mu_kipft": 5.0, "vu_kip": 2.0, "tu_kip": 3.0},
    seed=42,
    max_generations=30,
    progress_callback=progress_cb,
)
```

## 2. AI-Powered Recommendations (`ml_models.py`)

### `predict_initial_config()`

Predicts initial design configuration from project parameters.

**Features:**
- cabinet_area_ft2
- height_ft
- wind_speed_mph
- soil_bearing_psf

**Output:**
```python
{
    "suggested_pole": "HSS 6x6x1/4",
    "suggested_footing": {"diameter_ft": 3.0, "depth_ft": 4.0},
    "confidence": 0.75,
    "method": "ml_model" | "heuristic"
}
```

**Training:**
- If `data/projects.csv` exists, trains XGBoost/DecisionTree
- Falls back to rule-based heuristics if no training data

**Integration:**
- Agent 2: Add `trace.ai_suggestion={...}` to `POST /cabinets/derive` response

### `detect_unusual_config()`

Anomaly detection using Isolation Forest or Z-score rules.

**Features:**
- cabinet_area_ft2
- height_ft
- wind_speed_mph
- pole_sx_in3

**Output:**
```python
{
    "is_anomaly": bool,
    "anomaly_score": float,  # 0.0-1.0
    "reason": str  # e.g., "Tiny cabinet relative to height"
}
```

**Integration:**
- Add to Envelope: `assumptions += ["Unusual configuration detected"]`
- Lower confidence by 0.1 if anomalous

## 3. Advanced Structural Analysis (`structural_analysis.py`)

### `dynamic_load_analysis()`

ASCE 7-22 response spectrum analysis for dynamic amplification.

**Output:**
```python
{
    "peak_load": float,  # Amplified load
    "static_load": float,
    "amplification_factor": float  # Typically 1.0-1.3
}
```

### `fatigue_analysis()`

AISC 360-16 Appendix 3 fatigue analysis.

**Output:**
```python
{
    "design_life_years": float,
    "passes_25yr_requirement": bool,
    "cycles_to_failure": float | None,
    "stress_range_ksi": float,
    "detail_category": str
}
```

### `connection_design()`

AISC 360-16 Chapter J bolt group analysis.

**Output:**
```python
{
    "bolts_required": int,
    "bolts_provided": int,
    "weld_size_in": float,
    "connection_capacity_kip": float,
    "interaction_ratio": float,  # Combined tension+shear
    "passes": bool
}
```

## 4. Calibration & Uncertainty (`calibration.py`)

### `monte_carlo_reliability()`

Monte Carlo reliability analysis (10,000 samples).

**Target:**
- Reliability index β = 3.5 (ASCE 7)
- Failure probability < 1e-3

**Output:**
```python
{
    "beta": float,  # Reliability index
    "beta_ci": [lower, upper],  # ±10% confidence interval
    "failure_probability": float,
    "pf_ci": [lower, upper],
    "passes_target": bool,
    "target_beta": 3.5
}
```

### `sensitivity_analysis()`

Sobol indices for input importance ranking.

**Output:**
```python
{
    "ranked_inputs": List[str],  # Most to least sensitive
    "sensitivities": Dict[str, float],  # Sobol indices (0-1)
    "n_samples": int
}
```

### `compute_uncertainty_bands()`

Compute ±10% confidence intervals.

**Output:**
```python
{
    "nominal": float,
    "lower_bound": float,
    "upper_bound": float,
    "std_dev": float,
    "coefficient_of_variation": 0.1,
    "confidence_level": 0.9
}
```

## 5. Engineering Documentation (`engineering_docs.py`)

### `generate_calc_sheet()`

Generate LaTeX/HTML calculation sheet with equations.

**Output Formats:**
- `"latex"`: LaTeX source (compile with pdflatex)
- `"html"`: HTML (compile to PDF with weasyprint)

**Content:**
- Input parameters
- ASCE 7-22 equations
- Load derivation steps
- References (ASCE 7-22, AISC 360-16, ACI 318)

### `generate_load_diagram()`

Generate free-body diagram and moment diagram.

**Output:**
- Base64-encoded SVG string
- Or PNG bytes

**Diagrams:**
- Free-body diagram (left): Sign, pole, loads, reactions
- Moment diagram (right): Moment vs. height

### `generate_calc_sheet_pdf()`

Convert calculation sheet to PDF bytes.

## 6. Batch Processing (`batch.py`)

### `solve_batch()`

Parallel processing for multiple project configurations.

**Performance:**
- Target: 100 projects in <10s
- Uses `multiprocessing.Pool` with configurable workers

**Usage:**
```python
from apex.domains.signage.batch import ProjectConfig, solve_batch

configs = [
    ProjectConfig(
        project_id="proj1",
        site=SiteLoads(wind_speed_mph=115.0, exposure="C"),
        cabinets=[{"width_ft": 14.0, "height_ft": 8.0, "weight_psf": 10.0}],
        height_ft=25.0,
    )
    for i in range(100)
]

def progress_cb(total, completed, failed):
    print(f"Processed {completed}/{total} ({failed} failed)")

results = solve_batch(configs, progress_callback=progress_cb, n_workers=4)
```

**Output:**
```python
[
    {
        "project_id": str,
        "result": {
            "a_ft2": float,
            "z_cg_ft": float,
            "weight_estimate_lb": float,
            "mu_kipft": float,
        },
        "error": str | None
    },
    ...
]
```

**Integration:**
- Agent 2: `POST /batch/solve` endpoint
- Accepts `List[ProjectConfig]`
- Returns `List[Envelope]`

## Dependencies Added

- `deap==1.4.1` - Genetic algorithms
- `scikit-learn==1.4.1.post1` - ML models, anomaly detection
- `scipy==1.11.4` - Statistical functions
- `matplotlib==3.9.0` - Diagrams
- `jinja2==3.1.3` - Template engine
- `weasyprint==61.2` - PDF generation
- `pandas==2.2.1` - Training data loading

## Testing

Tests in `services/api/tests/advanced/`:
- `test_optimization.py` - Pareto optimization, GA
- `test_ml_models.py` - ML predictions, anomaly detection
- `test_structural_analysis.py` - Dynamic loads, fatigue, connections
- `test_calibration.py` - Monte Carlo, sensitivity
- `test_batch.py` - Batch processing

## Performance Targets

- `pareto_optimize_poles()`: <1s for 50 candidates
- `baseplate_optimize_ga()`: <5s convergence
- `predict_initial_config()`: <10ms (cached)
- `detect_unusual_config()`: <5ms
- `solve_batch()`: 100 projects in <10s

## Next Steps for Agent 2

1. **Pareto Optimization:**
   - Add `?optimize=pareto` to `POST /poles/options`
   - Return `trace.pareto_frontier` in Envelope

2. **AI Recommendations:**
   - Add `trace.ai_suggestion` to `POST /cabinets/derive`
   - Load training data from `data/projects.csv` if available

3. **Anomaly Detection:**
   - Call `detect_unusual_config()` in derive endpoints
   - Add to `assumptions`, lower `confidence` by 0.1 if anomalous

4. **Batch Processing:**
   - Create `POST /batch/solve` endpoint
   - Accept `List[ProjectConfig]`, return `List[Envelope]`

5. **Engineering Docs:**
   - Add `?format=pdf` to calculation endpoints
   - Generate calc sheets on demand

