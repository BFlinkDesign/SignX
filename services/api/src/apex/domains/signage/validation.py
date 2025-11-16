"""
APEX Signage Engineering - Real-World Validation & Calibration

Compare solver predictions against field data and auto-tune parameters.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import optimize, stats
import logging

logger = logging.getLogger(__name__)


# ========== Field Data Validation ==========


class FieldDataValidator:
    """Validates solver predictions against actual field installations."""
    
    def __init__(self, field_data_path: Optional[Path] = None):
        """
        Initialize validator with field data.
        
        Args:
            field_data_path: Path to CSV with historical project data
        """
        self.field_data: List[Dict[str, Any]] = []
        if field_data_path and field_data_path.exists():
            try:
                df = pd.read_csv(field_data_path)
                self.field_data = df.to_dict("records")
            except Exception as e:
                logger.warning("Exception in validation.py: %s", str(e))
                pass
    
    def validate_against_field_data(
        self,
        predictions: List[Dict[str, Any]],
        actuals: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        """
        Compare predictions vs actual installations.
        
        Args:
            predictions: List of prediction dicts with {pole_height, footing_depth, cost}
            actuals: List of actual dicts (or use self.field_data)
        
        Returns:
            Dict with RMSE, R², MAE, biases, recommendations
        """
        actuals = actuals or self.field_data
        
        if len(predictions) == 0 or len(actuals) == 0:
            return {
                "rmse": {},
                "r2": {},
                "mae": {},
                "biases": {},
                "recommendations": ["No field data available"],
            }
        
        # Extract metrics
        metrics = ["pole_height", "footing_depth", "cost"]
        results = {}
        
        for metric in metrics:
            pred_values = [p.get(metric, 0.0) for p in predictions if metric in p]
            actual_values = [a.get(metric, 0.0) for a in actuals if metric in a]
            
            if len(pred_values) != len(actual_values) or len(pred_values) == 0:
                continue
            
            pred_array = np.array(pred_values)
            actual_array = np.array(actual_values)
            
            # RMSE
            rmse = np.sqrt(np.mean((pred_array - actual_array) ** 2))
            
            # R²
            ss_res = np.sum((actual_array - pred_array) ** 2)
            ss_tot = np.sum((actual_array - np.mean(actual_array)) ** 2)
            r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
            
            # MAE
            mae = np.mean(np.abs(pred_array - actual_array))
            
            # Bias (systematic error)
            bias = np.mean(pred_array - actual_array)
            bias_pct = (bias / np.mean(actual_array)) * 100.0 if np.mean(actual_array) > 0 else 0.0
            
            results[metric] = {
                "rmse": round(rmse, 2),
                "rmse_pct": round((rmse / np.mean(actual_array)) * 100.0, 1) if np.mean(actual_array) > 0 else 0.0,
                "r2": round(r2, 3),
                "mae": round(mae, 2),
                "bias": round(bias, 2),
                "bias_pct": round(bias_pct, 1),
            }
        
        # Identify systematic biases
        biases = {}
        recommendations = []
        
        for metric, stats_dict in results.items():
            if abs(stats_dict["bias_pct"]) > 5.0:  # >5% bias
                biases[metric] = {
                    "direction": "overestimate" if stats_dict["bias"] > 0 else "underestimate",
                    "magnitude_pct": stats_dict["bias_pct"],
                }
                
                if metric == "footing_depth" and stats_dict["bias"] > 0:
                    recommendations.append(
                        f"Systematically overestimating footing depth by {stats_dict['bias_pct']:.1f}%. "
                        "Consider reducing soil bearing multiplier or calibration constant K."
                    )
                elif metric == "pole_height" and abs(stats_dict["bias_pct"]) > 10.0:
                    recommendations.append(
                        f"Pole height prediction bias: {stats_dict['bias_pct']:.1f}%. "
                        "Review wind load factors or exposure category assumptions."
                    )
        
        # Overall assessment
        target_rmse_pct = 10.0  # Target <10% RMSE
        all_rmse_ok = all(stats["rmse_pct"] < target_rmse_pct for stats in results.values())
        
        if not all_rmse_ok:
            recommendations.append(
                f"RMSE exceeds {target_rmse_pct}% target for some metrics. "
                "Consider retraining ML models or adjusting solver parameters."
            )
        
        return {
            "rmse": {k: v["rmse"] for k, v in results.items()},
            "rmse_pct": {k: v["rmse_pct"] for k, v in results.items()},
            "r2": {k: v["r2"] for k, v in results.items()},
            "mae": {k: v["mae"] for k, v in results.items()},
            "biases": biases,
            "recommendations": recommendations,
            "meets_target": all_rmse_ok,
        }


# ========== Auto-Tuning ==========


class SolverParameterTuner:
    """Auto-tune solver parameters based on field performance."""
    
    def __init__(self):
        """Initialize tuner with default parameters."""
        self.current_params = {
            "soil_bearing_multiplier": 1.0,
            "footing_calibration_k": 1.0,
            "safety_factor_base": 2.0,
            "wind_load_factor": 1.6,
        }
    
    def tune_parameters(
        self,
        field_data: List[Dict[str, Any]],
        objective: str = "minimize_error",
    ) -> Dict[str, float]:
        """
        Auto-tune parameters to minimize prediction error.
        
        Args:
            field_data: List of {predicted, actual, inputs} dicts
            objective: "minimize_error" or "minimize_error_with_safety"
        
        Returns:
            Dict of tuned parameter values
        """
        if len(field_data) < 10:
            return self.current_params  # Not enough data
        
        def objective_function(params: np.ndarray) -> float:
            """Minimize prediction error."""
            k, soil_mult = params
            
            errors = []
            for record in field_data:
                # Simplified: adjust predicted based on params
                predicted_adj = record.get("predicted_depth", 0.0) * k * soil_mult
                actual = record.get("actual_depth", 0.0)
                
                if actual > 0:
                    error = abs(predicted_adj - actual) / actual
                    errors.append(error)
            
            return np.mean(errors) if errors else 1000.0
        
        # Optimize calibration constant K and soil multiplier
        initial_guess = [self.current_params["footing_calibration_k"], self.current_params["soil_bearing_multiplier"]]
        bounds = [(0.5, 2.0), (0.8, 1.5)]  # Reasonable bounds
        
        try:
            result = optimize.minimize(
                objective_function,
                initial_guess,
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": 50},
            )
            
            if result.success:
                self.current_params["footing_calibration_k"] = round(result.x[0], 3)
                self.current_params["soil_bearing_multiplier"] = round(result.x[1], 3)
        except Exception as e:
            logger.warning("Exception in validation.py: %s", str(e))
            pass  # Keep defaults if optimization fails
        
        return self.current_params
    
    def validate_safety(self, tuned_params: Dict[str, float]) -> bool:
        """
        Validate that tuned parameters maintain safety.
        
        Returns False if parameters reduce safety factors below minimums.
        """
        # Ensure safety factors don't decrease too much
        if tuned_params.get("safety_factor_base", 2.0) < 1.5:
            return False
        
        # Ensure calibration doesn't reduce capacity
        if tuned_params.get("soil_bearing_multiplier", 1.0) < 0.8:
            return False
        
        return True


# ========== Validation Report Generation ==========


def generate_validation_report(
    validation_results: Dict[str, Any],
    output_path: Path,
    field_data: List[Dict[str, Any]] | None = None,
) -> Path:
    """
    Generate PDF validation report with scatter plots and statistics.
    
    Args:
        validation_results: Results from validate_against_field_data()
        output_path: Output PDF path
        field_data: Optional field data for plots
    
    Returns:
        Path to generated PDF
    """
    from matplotlib import pyplot as plt
    from weasyprint import HTML
    
    # Generate scatter plots
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; margin: 1in; }
            h1 { color: #333; }
            .metric { margin: 20px 0; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <h1>APEX Solver Validation Report</h1>
        
        <h2>Statistical Summary</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>RMSE (%)</th>
                <th>R²</th>
                <th>MAE</th>
                <th>Bias (%)</th>
            </tr>
    """
    
    for metric in ["pole_height", "footing_depth", "cost"]:
        if metric in validation_results.get("rmse", {}):
            stats = {
                "rmse_pct": validation_results["rmse_pct"].get(metric, 0.0),
                "r2": validation_results["r2"].get(metric, 0.0),
                "mae": validation_results["mae"].get(metric, 0.0),
                "bias_pct": validation_results.get("biases", {}).get(metric, {}).get("magnitude_pct", 0.0),
            }
            html_content += f"""
            <tr>
                <td>{metric}</td>
                <td>{stats['rmse_pct']:.1f}</td>
                <td>{stats['r2']:.3f}</td>
                <td>{stats['mae']:.2f}</td>
                <td>{stats['bias_pct']:.1f}</td>
            </tr>
            """
    
    html_content += """
        </table>
        
        <h2>Recommendations</h2>
        <ul>
    """
    
    for rec in validation_results.get("recommendations", []):
        html_content += f"<li>{rec}</li>"
    
    html_content += """
        </ul>
        
        <h2>Assessment</h2>
        <p>
    """
    
    if validation_results.get("meets_target", False):
        html_content += "✅ Validation PASSED: All metrics meet <10% RMSE target."
    else:
        html_content += "⚠️ Validation FAILED: Some metrics exceed <10% RMSE target. Parameter tuning recommended."
    
    html_content += """
        </p>
    </body>
    </html>
    """
    
    # Generate PDF
    pdf_bytes = HTML(string=html_content).write_pdf()
    output_path.write_bytes(pdf_bytes)
    
    return output_path


# ========== Convenience Functions ==========


def validate_against_field_data(
    predictions: List[Dict[str, Any]],
    field_data_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Convenience function to validate predictions.
    
    Args:
        predictions: List of prediction dicts
        field_data_path: Optional path to field data CSV
    
    Returns:
        Validation results dict
    """
    validator = FieldDataValidator(field_data_path)
    return validator.validate_against_field_data(predictions)


def auto_tune_parameters(
    field_data_path: Path,
    objective: str = "minimize_error",
) -> Dict[str, float]:
    """
    Auto-tune solver parameters from field data.
    
    Args:
        field_data_path: Path to CSV with field data
        objective: Tuning objective
    
    Returns:
        Tuned parameter dict
    """
    tuner = SolverParameterTuner()
    
    if field_data_path.exists():
        try:
            df = pd.read_csv(field_data_path)
            field_data = df.to_dict("records")
            return tuner.tune_parameters(field_data, objective)
        except Exception as e:
            logger.warning("Exception in validation.py: %s", str(e))
            pass
    
    return tuner.current_params

