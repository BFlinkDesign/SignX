#!/usr/bin/env python3
"""
Accuracy Validation Script

Compares APEX solver results against reference data from Eagle Sign projects.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "services" / "api" / "src"))

from apex.domains.signage.models import Cabinet, SiteLoads
from apex.domains.signage.solvers import derive_loads, filter_poles, footing_solve


def load_reference_data(csv_path: Path) -> list[dict]:
    """Load reference data from CSV."""
    if not csv_path.exists():
        logger.info(f"⚠️  Reference data file not found: {csv_path}")
        logger.info("   Using synthetic test cases instead...")
        return _synthetic_test_cases()
    
    data = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


def _synthetic_test_cases() -> list[dict]:
    """Generate synthetic test cases for validation."""
    return [
        {
            "project_id": "test_1",
            "cabinet_width_ft": "14.0",
            "cabinet_height_ft": "8.0",
            "wind_speed_mph": "115.0",
            "exposure": "C",
            "height_ft": "25.0",
            "expected_mu_kipft": "12.5",  # Approximate
            "expected_depth_ft": "4.5",  # Approximate
        },
        {
            "project_id": "test_2",
            "cabinet_width_ft": "10.0",
            "cabinet_height_ft": "6.0",
            "wind_speed_mph": "90.0",
            "exposure": "C",
            "height_ft": "20.0",
            "expected_mu_kipft": "6.8",  # Approximate
            "expected_depth_ft": "3.5",  # Approximate
        },
    ]


def validate_derive_loads(test_case: dict) -> dict:
    """Validate derive_loads against expected results."""
    site = SiteLoads(
        wind_speed_mph=float(test_case["wind_speed_mph"]),
        exposure=test_case.get("exposure", "C"),
    )
    cabinets = [
        Cabinet(
            width_ft=float(test_case["cabinet_width_ft"]),
            height_ft=float(test_case["cabinet_height_ft"]),
            weight_psf=10.0,
        )
    ]
    height_ft = float(test_case["height_ft"])
    
    result = derive_loads(site, cabinets, height_ft, seed=0)
    
    expected_mu = float(test_case.get("expected_mu_kipft", 0.0))
    if expected_mu > 0:
        error_pct = abs(result.mu_kipft - expected_mu) / expected_mu * 100.0
    else:
        error_pct = 0.0
    
    return {
        "project_id": test_case["project_id"],
        "solver": "derive_loads",
        "predicted": result.mu_kipft,
        "expected": expected_mu,
        "error_pct": error_pct,
        "pass": error_pct < 10.0 if expected_mu > 0 else True,
    }


def validate_footing_solve(test_case: dict) -> dict:
    """Validate footing_solve against expected results."""
    mu_kipft = float(test_case.get("mu_kipft", 10.0))
    diameter_ft = 3.0
    soil_psf = 3000.0
    
    depth_ft, request_engineering, warnings = footing_solve(
        mu_kipft=mu_kipft,
        diameter_ft=diameter_ft,
        soil_psf=soil_psf,
        num_poles=1,
        seed=0,
    )
    
    expected_depth = float(test_case.get("expected_depth_ft", 0.0))
    if expected_depth > 0:
        error_pct = abs(depth_ft - expected_depth) / expected_depth * 100.0
    else:
        error_pct = 0.0
    
    return {
        "project_id": test_case["project_id"],
        "solver": "footing_solve",
        "predicted": depth_ft,
        "expected": expected_depth,
        "error_pct": error_pct,
        "pass": error_pct < 10.0 if expected_depth > 0 else True,
    }


def calculate_rmse(predictions: list[float], actuals: list[float]) -> float:
    """Calculate Root Mean Squared Error."""
    if len(predictions) != len(actuals) or len(predictions) == 0:
        return 0.0
    
    errors = [(p - a) ** 2 for p, a in zip(predictions, actuals) if a > 0]
    if not errors:
        return 0.0
    
    mse = np.mean(errors)
    rmse = np.sqrt(mse)
    
    # Normalize by mean actual value
    mean_actual = np.mean([a for a in actuals if a > 0])
    rmse_pct = (rmse / mean_actual * 100.0) if mean_actual > 0 else 0.0
    
    return rmse_pct


def main():
    """Run accuracy validation."""
    import argparse
import logging

logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(description="Validate solver accuracy")
    parser.add_argument(
        "--reference-data",
        type=Path,
        default=Path("data/eagle_sign_projects.csv"),
        help="Path to reference data CSV",
    )
    args = parser.parse_args()
    
    logger.info("Accuracy Validation Suite")
    logger.info("=" * 60)
    
    # Load reference data
    test_cases = load_reference_data(args.reference_data)
    logger.info(f"\nLoaded {len(test_cases)} test cases")
    
    # Validate derive_loads
    logger.info("\nValidating derive_loads()...")
    derive_results = []
    for test_case in test_cases:
        if "cabinet_width_ft" in test_case:
            result = validate_derive_loads(test_case)
            derive_results.append(result)
            status = "✅ PASS" if result["pass"] else "❌ FAIL"
            logger.error(f"  {status}: {result['project_id']} - Error: {result['error_pct']:.1f}%")
    
    # Validate footing_solve
    logger.info("\nValidating footing_solve()...")
    footing_results = []
    for test_case in test_cases:
        if "expected_depth_ft" in test_case:
            result = validate_footing_solve(test_case)
            footing_results.append(result)
            status = "✅ PASS" if result["pass"] else "❌ FAIL"
            logger.error(f"  {status}: {result['project_id']} - Error: {result['error_pct']:.1f}%")
    
    # Calculate RMSE
    logger.info("\n" + "=" * 60)
    logger.info("Summary:")
    
    if derive_results:
        predictions = [r["predicted"] for r in derive_results if r["expected"] > 0]
        actuals = [r["expected"] for r in derive_results if r["expected"] > 0]
        if predictions and actuals:
            rmse_pct = calculate_rmse(predictions, actuals)
            logger.info(f"  derive_loads RMSE: {rmse_pct:.1f}% {'✅' if rmse_pct < 10.0 else '❌'} (target: <10%)")
            passed = sum(1 for r in derive_results if r["pass"])
            logger.info(f"  derive_loads Pass Rate: {passed}/{len(derive_results)} ({100*passed/len(derive_results):.0f}%)")
    
    if footing_results:
        predictions = [r["predicted"] for r in footing_results if r["expected"] > 0]
        actuals = [r["expected"] for r in footing_results if r["expected"] > 0]
        if predictions and actuals:
            rmse_pct = calculate_rmse(predictions, actuals)
            logger.info(f"  footing_solve RMSE: {rmse_pct:.1f}% {'✅' if rmse_pct < 10.0 else '❌'} (target: <10%)")
            passed = sum(1 for r in footing_results if r["pass"])
            logger.info(f"  footing_solve Pass Rate: {passed}/{len(footing_results)} ({100*passed/len(footing_results):.0f}%)")
    
    # Overall status
    all_passed = all(
        r["pass"] for r in derive_results + footing_results
    )
    
    if all_passed:
        logger.info("\n✅ Overall: PASS (all validations within 10% RMSE)")
        sys.exit(0)
    else:
        logger.error("\n❌ Overall: FAIL (some validations exceed 10% RMSE)")
        sys.exit(1)


if __name__ == "__main__":
    main()

