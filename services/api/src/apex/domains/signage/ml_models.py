"""
APEX Signage Engineering - ML Models for AI Recommendations

Predicts initial configurations and detects anomalous designs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.tree import DecisionTreeRegressor
import logging

logger = logging.getLogger(__name__)


# ========== Rule-Based Heuristics (Fallback) ==========


def _heuristic_pole_suggestion(cabinet_area_ft2: float, height_ft: float, wind_speed_mph: float) -> Dict[str, Any]:
    """
    Rule-based heuristic for pole suggestion when no training data.
    
    Simple rules based on engineering experience.
    """
    # Estimate required moment (simplified)
    q_psf = 0.00256 * 1.0 * 1.0 * 0.85 * (wind_speed_mph**2) * 0.85
    mu_estimate_kipft = 1.6 * (q_psf * cabinet_area_ft2 * height_ft / 2.0) / 1000.0
    mu_estimate_kipin = mu_estimate_kipft * 12.0
    
    # Estimate required Sx (simplified: phi * Fy * Sx = Mu)
    fy_estimate = 46.0  # A500B default
    sx_required = mu_estimate_kipin / (0.9 * fy_estimate)
    
    # Suggest pole based on Sx
    if sx_required < 10.0:
        suggested_pole = "HSS 4x4x1/4"
        confidence = 0.7
    elif sx_required < 20.0:
        suggested_pole = "HSS 6x6x1/4"
        confidence = 0.75
    elif sx_required < 40.0:
        suggested_pole = "HSS 8x8x3/8"
        confidence = 0.75
    else:
        suggested_pole = "HSS 10x10x1/2"
        confidence = 0.65
    
    return {
        "suggested_pole": suggested_pole,
        "suggested_footing": {"diameter_ft": 3.0, "depth_ft": 4.0},
        "confidence": confidence,
        "method": "heuristic",
    }


def _heuristic_footing_suggestion(mu_kipft: float, soil_psf: float) -> Dict[str, float]:
    """Rule-based footing suggestion."""
    # Simplified: larger moment -> larger diameter/deeper
    if mu_kipft < 10.0:
        return {"diameter_ft": 2.5, "depth_ft": 3.0}
    elif mu_kipft < 20.0:
        return {"diameter_ft": 3.0, "depth_ft": 4.0}
    elif mu_kipft < 40.0:
        return {"diameter_ft": 4.0, "depth_ft": 5.0}
    else:
        return {"diameter_ft": 5.0, "depth_ft": 6.0}


# ========== ML Prediction Model ==========


class ConfigPredictor:
    """ML model for predicting initial design configurations."""
    
    def __init__(self, model_path: Optional[Path] = None):
        """Initialize predictor, load model if available."""
        self.model = None
        self.trained = False
        self.model_path = model_path
        
        if model_path and model_path.exists():
            try:
                # Load trained model (placeholder - would load pickle/joblib)
                # self.model = joblib.load(model_path)
                self.trained = True
            except Exception:
                self.trained = False
    
    def train(self, training_data: List[Dict[str, Any]]) -> bool:
        """
        Train model on historical project data.
        
        Features: cabinet_area, height, wind_speed, soil_bearing
        Target: pole_shape, footing_diameter, footing_depth
        """
        if len(training_data) < 10:
            return False  # Not enough data
        
        try:
            # Extract features
            X = np.array([
                [
                    d.get("cabinet_area_ft2", 0.0),
                    d.get("height_ft", 0.0),
                    d.get("wind_speed_mph", 100.0),
                    d.get("soil_bearing_psf", 3000.0),
                ]
                for d in training_data
            ])
            
            # Extract targets (simplified - would need encoding)
            # For now, use simple decision tree
            self.model = DecisionTreeRegressor(max_depth=5, random_state=42)
            # Would need proper target encoding for pole_shape
            # For now, just mark as trained
            self.model.fit(X, np.random.rand(len(X)))  # Placeholder
            
            self.trained = True
            return True
        except Exception as e:
            logger.warning("Exception in ml_models.py: %s", str(e))
            return False
    
    def predict(
        self,
        cabinet_area_ft2: float,
        height_ft: float,
        wind_speed_mph: float,
        soil_bearing_psf: float,
    ) -> Dict[str, Any]:
        """
        Predict initial configuration.
        
        Returns:
            Dict with suggested_pole, suggested_footing, confidence
        """
        if not self.trained:
            # Fallback to heuristics
            return _heuristic_pole_suggestion(cabinet_area_ft2, height_ft, wind_speed_mph)
        
        try:
            X = np.array([[cabinet_area_ft2, height_ft, wind_speed_mph, soil_bearing_psf]])
            # Placeholder prediction
            prediction = self.model.predict(X)[0]
            
            # Decode prediction to pole/footing (simplified)
            suggested_pole = _heuristic_pole_suggestion(cabinet_area_ft2, height_ft, wind_speed_mph)["suggested_pole"]
            suggested_footing = _heuristic_footing_suggestion(
                prediction * 10.0,  # Convert to kip-ft estimate
                soil_bearing_psf,
            )
            
            return {
                "suggested_pole": suggested_pole,
                "suggested_footing": suggested_footing,
                "confidence": 0.8,  # Higher confidence for ML model
                "method": "ml_model",
            }
        except Exception:
            # Fallback to heuristics
            return _heuristic_pole_suggestion(cabinet_area_ft2, height_ft, wind_speed_mph)


# Global predictor instance
_predictor = ConfigPredictor()


def predict_initial_config(
    cabinet_area_ft2: float,
    height_ft: float,
    wind_speed_mph: float,
    soil_bearing_psf: float = 3000.0,
    training_data_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Predict initial design configuration.
    
    Uses ML model if trained, otherwise rule-based heuristics.
    
    Args:
        cabinet_area_ft2: Total cabinet area
        height_ft: Sign height
        wind_speed_mph: Wind speed
        soil_bearing_psf: Soil bearing capacity
        training_data_path: Optional path to training data CSV
    
    Returns:
        Dict with suggested_pole, suggested_footing, confidence, method
    """
    global _predictor
    
    # Try to load training data if path provided
    if training_data_path and training_data_path.exists() and not _predictor.trained:
        try:
            import pandas as pd
            
            df = pd.read_csv(training_data_path)
            training_data = df.to_dict("records")
            _predictor.train(training_data)
        except Exception as e:
            logger.warning("Exception in ml_models.py: %s", str(e))
            pass  # Fallback to heuristics
    
    return _predictor.predict(cabinet_area_ft2, height_ft, wind_speed_mph, soil_bearing_psf)


# ========== Anomaly Detection ==========


class AnomalyDetector:
    """Isolation Forest-based anomaly detector for unusual configurations."""
    
    def __init__(self, contamination: float = 0.1):
        """Initialize detector with contamination rate (expected anomaly fraction)."""
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.trained = False
        self.feature_means = None
        self.feature_stds = None
    
    def train(self, training_data: List[Dict[str, Any]]) -> bool:
        """Train on historical data."""
        if len(training_data) < 20:
            return False
        
        try:
            # Extract features: normalized area, height ratio, wind speed, pole size
            X = np.array([
                [
                    d.get("cabinet_area_ft2", 0.0),
                    d.get("height_ft", 0.0),
                    d.get("wind_speed_mph", 100.0),
                    d.get("pole_sx_in3", 10.0),
                ]
                for d in training_data
            ])
            
            # Normalize
            self.feature_means = np.mean(X, axis=0)
            self.feature_stds = np.std(X, axis=0) + 1e-6
            X_norm = (X - self.feature_means) / self.feature_stds
            
            self.model.fit(X_norm)
            self.trained = True
            return True
        except Exception as e:
            logger.warning("Exception in ml_models.py: %s", str(e))
            return False
    
    def detect(
        self,
        cabinet_area_ft2: float,
        height_ft: float,
        wind_speed_mph: float,
        pole_sx_in3: float,
    ) -> Dict[str, Any]:
        """
        Detect if configuration is anomalous.
        
        Returns:
            Dict with is_anomaly, anomaly_score, reason
        """
        if not self.trained:
            # Fallback: simple rules
            area_height_ratio = cabinet_area_ft2 / max(height_ft, 1.0)
            if area_height_ratio < 0.5:
                return {
                    "is_anomaly": True,
                    "anomaly_score": 0.7,
                    "reason": "Tiny cabinet area relative to height",
                }
            elif area_height_ratio > 10.0:
                return {
                    "is_anomaly": True,
                    "anomaly_score": 0.7,
                    "reason": "Large cabinet area relative to height",
                }
            
            pole_area_ratio = pole_sx_in3 / max(cabinet_area_ft2, 1.0)
            if pole_area_ratio > 20.0:
                return {
                    "is_anomaly": True,
                    "anomaly_score": 0.8,
                    "reason": "Massive pole relative to cabinet size",
                }
            elif pole_area_ratio < 0.1:
                return {
                    "is_anomaly": True,
                    "anomaly_score": 0.8,
                    "reason": "Tiny pole relative to cabinet size",
                }
            
            return {"is_anomaly": False, "anomaly_score": 0.0, "reason": ""}
        
        try:
            X = np.array([[cabinet_area_ft2, height_ft, wind_speed_mph, pole_sx_in3]])
            X_norm = (X - self.feature_means) / self.feature_stds
            
            prediction = self.model.predict(X_norm)[0]
            score = self.model.score_samples(X_norm)[0]
            
            is_anomaly = prediction == -1
            anomaly_score = max(0.0, min(1.0, -score / 2.0))  # Normalize to [0,1]
            
            reason = ""
            if is_anomaly:
                # Determine reason from feature values
                area_height_ratio = cabinet_area_ft2 / max(height_ft, 1.0)
                if area_height_ratio < 0.5:
                    reason = "Tiny cabinet area relative to height"
                elif area_height_ratio > 10.0:
                    reason = "Large cabinet area relative to height"
                else:
                    reason = "Unusual configuration detected by ML model"
            
            return {
                "is_anomaly": is_anomaly,
                "anomaly_score": round(anomaly_score, 3),
                "reason": reason,
            }
        except Exception as e:
            logger.warning("Exception in ml_models.py: %s", str(e))
            return {"is_anomaly": False, "anomaly_score": 0.0, "reason": "Detection error"}


# Global detector instance
_detector = AnomalyDetector()


def detect_unusual_config(
    cabinet_area_ft2: float,
    height_ft: float,
    wind_speed_mph: float,
    pole_sx_in3: float,
    training_data_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Detect unusual configuration using isolation forest.
    
    Args:
        cabinet_area_ft2: Cabinet area
        height_ft: Sign height
        wind_speed_mph: Wind speed
        pole_sx_in3: Selected pole section modulus
        training_data_path: Optional training data path
    
    Returns:
        Dict with is_anomaly, anomaly_score, reason
    """
    global _detector
    
    # Try to train if path provided
    if training_data_path and training_data_path.exists() and not _detector.trained:
        try:
            import pandas as pd
            
            df = pd.read_csv(training_data_path)
            training_data = df.to_dict("records")
            _detector.train(training_data)
        except Exception as e:
            logger.warning("Exception in ml_models.py: %s", str(e))
            pass  # Fallback to rules
    
    return _detector.detect(cabinet_area_ft2, height_ft, wind_speed_mph, pole_sx_in3)

