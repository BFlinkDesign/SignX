"""Anomaly detection for unusual cost patterns."""
from typing import Optional
import joblib
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

from signx_intel.config import get_settings

settings = get_settings()


class CostAnomalyDetector:
    """Detect anomalous cost records using Isolation Forest."""
    
    def __init__(self, model_path: Optional[str] = None):
        """Initialize anomaly detector."""
        self.model = None
        self.model_path = Path(model_path or settings.model_path)
        self.model_path.mkdir(parents=True, exist_ok=True)
    
    def train(
        self,
        df: pd.DataFrame,
        contamination: float = 0.1
    ) -> dict:
        """
        Train anomaly detection model.
        
        Args:
            df: DataFrame with cost features
            contamination: Expected proportion of anomalies (0.0 to 0.5)
        
        Returns:
            Training summary
        """
        print(f"Training anomaly detector on {len(df)} records...")
        
        # Select numeric features
        numeric_df = df.select_dtypes(include=[np.number])
        
        # Train Isolation Forest
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(numeric_df)
        
        # Get anomaly scores
        scores = self.model.score_samples(numeric_df)
        predictions = self.model.predict(numeric_df)
        
        n_anomalies = (predictions == -1).sum()
        
        print(f"✅ Training complete!")
        print(f"   Detected {n_anomalies} anomalies ({n_anomalies/len(df)*100:.1f}%)")
        
        return {
            "n_records": len(df),
            "n_anomalies": int(n_anomalies),
            "anomaly_rate": float(n_anomalies / len(df))
        }
    
    def predict(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """
        Detect anomalies in new data.
        
        Args:
            df: DataFrame with cost features
        
        Returns:
            Tuple of (predictions, anomaly_scores)
            predictions: -1 for anomaly, 1 for normal
            anomaly_scores: Lower is more anomalous
        """
        if self.model is None:
            raise ValueError("Model not trained or loaded")
        
        numeric_df = df.select_dtypes(include=[np.number])
        predictions = self.model.predict(numeric_df)
        scores = self.model.score_samples(numeric_df)
        
        return predictions, scores
    
    def save(self, name: str = "anomaly_detector_v1"):
        """Save model."""
        if self.model is None:
            raise ValueError("No model to save")
        
        model_file = self.model_path / f"{name}.joblib"
        joblib.dump(self.model, model_file)
        print(f"✅ Anomaly detector saved to {model_file}")
    
    def load(self, name: str = "anomaly_detector_v1"):
        """Load model."""
        model_file = self.model_path / f"{name}.joblib"
        
        if not model_file.exists():
            raise FileNotFoundError(f"Model not found: {model_file}")
        
        self.model = joblib.load(model_file)
        print(f"✅ Anomaly detector loaded from {model_file}")

