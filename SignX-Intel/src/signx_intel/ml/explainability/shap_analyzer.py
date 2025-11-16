"""SHAP-based model explainability."""
from typing import Optional, Dict
import pandas as pd
import numpy as np

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    print("⚠️  SHAP not available. Install with: pip install shap")


class SHAPAnalyzer:
    """SHAP-based explainability for cost predictions."""
    
    def __init__(self, model, X_train: pd.DataFrame):
        """
        Initialize SHAP analyzer.
        
        Args:
            model: Trained model (XGBoost, etc.)
            X_train: Training data for SHAP background
        """
        if not SHAP_AVAILABLE:
            raise ImportError("SHAP not available")
        
        self.model = model
        self.explainer = shap.TreeExplainer(model)
        self.X_train = X_train
    
    def explain_prediction(self, X: pd.DataFrame) -> Dict[str, float]:
        """
        Get SHAP values for a prediction.
        
        Args:
            X: Features to explain
        
        Returns:
            Dictionary of feature: shap_value
        """
        shap_values = self.explainer.shap_values(X)
        
        # Convert to dictionary
        if len(X) == 1:
            feature_importance = dict(zip(X.columns, shap_values[0]))
        else:
            # Average SHAP values for multiple predictions
            avg_shap = np.mean(np.abs(shap_values), axis=0)
            feature_importance = dict(zip(X.columns, avg_shap))
        
        # Sort by absolute importance
        feature_importance = dict(
            sorted(feature_importance.items(), key=lambda x: abs(x[1]), reverse=True)
        )
        
        return feature_importance
    
    def get_top_drivers(self, X: pd.DataFrame, top_n: int = 5) -> list:
        """Get top cost drivers for a prediction."""
        importance = self.explain_prediction(X)
        
        top_drivers = [
            {"driver": k, "importance": abs(v), "shap_value": v}
            for k, v in list(importance.items())[:top_n]
        ]
        
        return top_drivers

