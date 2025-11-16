"""Production inference service for cost predictions."""
from typing import Dict, Any, Optional
from decimal import Decimal

import pandas as pd

from signx_intel.ml.training.cost_predictor import CostPredictor
from signx_intel.ml.training.anomaly_detector import CostAnomalyDetector


class InferenceService:
    """Production inference service."""
    
    def __init__(self):
        """Initialize inference service."""
        self.cost_predictor = None
        self.anomaly_detector = None
        self._load_models()
    
    def _load_models(self):
        """Load trained models."""
        try:
            self.cost_predictor = CostPredictor()
            self.cost_predictor.load("cost_predictor_v1")
        except FileNotFoundError:
            print("⚠️  Cost prediction model not found. Using fallback heuristics.")
        
        try:
            self.anomaly_detector = CostAnomalyDetector()
            self.anomaly_detector.load("anomaly_detector_v1")
        except FileNotFoundError:
            print("⚠️  Anomaly detector not found. Anomaly scores unavailable.")
    
    def predict_cost(
        self,
        drivers: Dict[str, Any],
        use_heuristic: bool = False
    ) -> Dict[str, Any]:
        """
        Predict project cost from drivers.
        
        Args:
            drivers: Dictionary of cost drivers
            use_heuristic: Force use of heuristic fallback
        
        Returns:
            Prediction result dictionary
        """
        if self.cost_predictor is None or use_heuristic:
            return self._heuristic_prediction(drivers)
        
        # Convert to DataFrame
        df = pd.DataFrame([drivers])
        
        # Get prediction
        prediction = self.cost_predictor.predict(df)[0]
        
        # Get anomaly score if available
        anomaly_score = None
        if self.anomaly_detector is not None:
            _, scores = self.anomaly_detector.predict(df)
            # Convert to 0-1 scale (lower score = more anomalous)
            anomaly_score = float(1.0 / (1.0 + abs(scores[0])))
        
        # Get feature importance (simplified)
        confidence = 0.85  # TODO: Calculate actual confidence intervals
        
        return {
            "predicted_cost": Decimal(str(prediction)),
            "confidence_score": confidence,
            "anomaly_score": anomaly_score,
            "model_version": "v1.0",
            "method": "ml_model"
        }
    
    def _heuristic_prediction(self, drivers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback heuristic when ML model unavailable.
        
        This provides reasonable estimates based on domain knowledge.
        """
        base_cost = 1000.0
        
        # Area-based cost
        if "sign_area_sqft" in drivers:
            base_cost += drivers["sign_area_sqft"] * 50.0
        
        # Height multiplier
        if "sign_height_ft" in drivers:
            height_multiplier = 1.0 + (drivers["sign_height_ft"] / 100.0)
            base_cost *= height_multiplier
        
        # Foundation type
        foundation_multipliers = {
            "drilled_pier": 1.5,
            "spread_footing": 1.2,
            "mono_column": 1.0
        }
        if "foundation_type" in drivers:
            mult = foundation_multipliers.get(drivers["foundation_type"], 1.0)
            base_cost *= mult
        
        # Wind loading
        if "wind_speed_mph" in drivers:
            if drivers["wind_speed_mph"] > 130:
                base_cost *= 1.3
            elif drivers["wind_speed_mph"] > 110:
                base_cost *= 1.15
        
        return {
            "predicted_cost": Decimal(str(base_cost)),
            "confidence_score": 0.6,  # Lower confidence for heuristic
            "anomaly_score": None,
            "model_version": "heuristic-v1.0",
            "method": "heuristic"
        }

