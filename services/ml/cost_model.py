"""GPU-accelerated cost prediction model using XGBoost and cuML.

This module provides cost estimation ML models that can be trained on GPU
and used for real-time predictions in the SignX-Studio API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
import structlog
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

logger = structlog.get_logger(__name__)


class CostPredictor:
    """GPU-accelerated cost prediction using XGBoost.
    
    Features:
    - GPU training via tree_method='gpu_hist'
    - Uncertainty quantification via prediction intervals
    - Feature importance analysis
    - Model versioning and persistence
    """
    
    def __init__(self, use_gpu: bool = True):
        """Initialize cost predictor.
        
        Args:
            use_gpu: Whether to use GPU acceleration for training
        """
        import xgboost as xgb
        
        self.model = xgb.XGBRegressor(
            n_estimators=500,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            tree_method='gpu_hist' if use_gpu else 'hist',
            objective='reg:squarederror',
            random_state=42,
            n_jobs=-1,
        )
        
        self.feature_columns: Optional[list[str]] = None
        self.feature_importances_: Optional[pd.DataFrame] = None
        self.training_metrics: Optional[dict[str, float]] = None
        self.use_gpu = use_gpu
    
    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer features from raw data."""
        features = df.copy()
        
        # Derived geometric features
        if "height_ft" in features.columns and "sign_area_sqft" in features.columns:
            features["aspect_ratio"] = features["height_ft"] / np.sqrt(features["sign_area_sqft"])
        
        if "pole_height_ft" in features.columns and "pole_size" in features.columns:
            features["slenderness_ratio"] = features["pole_height_ft"] / features["pole_size"]
        
        # Wind loading proxy
        if "wind_speed_mph" in features.columns and "importance_factor" in features.columns:
            features["wind_pressure_psf"] = (
                0.00256 * features["wind_speed_mph"] ** 2 * features["importance_factor"]
            )
        
        # Cost per square foot (for normalization)
        if "total_cost" in features.columns and "sign_area_sqft" in features.columns:
            features["cost_per_sqft"] = features["total_cost"] / features["sign_area_sqft"]
        
        # Structural intensity proxy
        if "embedment_depth_ft" in features.columns and "height_ft" in features.columns:
            features["foundation_ratio"] = features["embedment_depth_ft"] / features["height_ft"]
        
        # Temporal features
        if "quote_date" in features.columns:
            quote_dates = pd.to_datetime(features["quote_date"], errors="coerce")
            features["quote_year"] = quote_dates.dt.year
            features["quote_quarter"] = quote_dates.dt.quarter
            features["quote_month"] = quote_dates.dt.month
        
        return features
    
    def prepare_training_data(
        self,
        df: pd.DataFrame,
        target_col: str = "total_cost"
    ) -> tuple[pd.DataFrame, pd.Series]:
        """Prepare features and target for training.
        
        Args:
            df: Raw DataFrame with cost records
            target_col: Name of target column
            
        Returns:
            Tuple of (X_features, y_target)
        """
        # Engineer features
        df_engineered = self._engineer_features(df)
        
        # Select feature columns
        feature_cols = [
            "height_ft",
            "sign_area_sqft",
            "wind_speed_mph",
            "exposure_code",
            "importance_factor",
            "pole_type_code",
            "pole_size",
            "pole_thickness_in",
            "pole_height_ft",
            "foundation_type_code",
            "embedment_depth_ft",
            "concrete_volume_cuyd",
            "soil_bearing_psf",
            "snow_load_psf",
            "aspect_ratio",
            "slenderness_ratio",
            "wind_pressure_psf",
            "foundation_ratio",
            "quote_year",
            "quote_quarter",
        ]
        
        # Filter to columns that exist
        available_cols = [col for col in feature_cols if col in df_engineered.columns]
        
        X = df_engineered[available_cols].copy()
        y = df_engineered[target_col].copy()
        
        # Fill missing values with median
        X = X.fillna(X.median())
        
        self.feature_columns = available_cols
        
        logger.info("features.prepared",
                   n_features=len(available_cols),
                   n_samples=len(X))
        
        return X, y
    
    def train(
        self,
        df: pd.DataFrame,
        target_col: str = "total_cost",
        test_size: float = 0.2,
        random_state: int = 42
    ) -> dict[str, float]:
        """Train cost prediction model on GPU.
        
        Args:
            df: DataFrame with cost records
            target_col: Target column name
            test_size: Fraction of data for testing
            random_state: Random seed for reproducibility
            
        Returns:
            Dictionary of training metrics
        """
        logger.info("training.start",
                   samples=len(df),
                   use_gpu=self.use_gpu)
        
        # Prepare data
        X, y = self.prepare_training_data(df, target_col)
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        
        logger.info("training.split",
                   train_size=len(X_train),
                   test_size=len(X_test))
        
        # Train
        import time
import logging

logger = logging.getLogger(__name__)
        start = time.time()
        
        self.model.fit(X_train, y_train)
        
        training_time = time.time() - start
        
        logger.info("training.complete", duration=f"{training_time:.2f}s")
        
        # Evaluate
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)
        
        metrics = {
            "train_mae": float(mean_absolute_error(y_train, y_pred_train)),
            "test_mae": float(mean_absolute_error(y_test, y_pred_test)),
            "train_rmse": float(np.sqrt(mean_squared_error(y_train, y_pred_train))),
            "test_rmse": float(np.sqrt(mean_squared_error(y_test, y_pred_test))),
            "train_r2": float(r2_score(y_train, y_pred_train)),
            "test_r2": float(r2_score(y_test, y_pred_test)),
            "train_mape": float(np.mean(np.abs((y_train - y_pred_train) / y_train)) * 100),
            "test_mape": float(np.mean(np.abs((y_test - y_pred_test) / y_test)) * 100),
            "training_time_seconds": training_time,
            "n_features": len(self.feature_columns or []),
            "n_train_samples": len(X_train),
            "n_test_samples": len(X_test),
        }
        
        self.training_metrics = metrics
        
        # Feature importance
        self.feature_importances_ = pd.DataFrame({
            "feature": self.feature_columns,
            "importance": self.model.feature_importances_
        }).sort_values("importance", ascending=False)
        
        logger.info("training.metrics", **metrics)
        
        return metrics
    
    def predict_with_uncertainty(
        self,
        features: dict[str, Any],
        n_iterations: int = 100
    ) -> dict[str, Any]:
        """Predict cost with uncertainty quantification.
        
        Args:
            features: Feature dictionary
            n_iterations: Number of Monte Carlo iterations for uncertainty
            
        Returns:
            Dictionary with prediction and confidence intervals
        """
        if self.feature_columns is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # Convert to DataFrame
        feature_df = pd.DataFrame([features])
        
        # Engineer features
        feature_df = self._engineer_features(feature_df)
        
        # Select and fill
        X = feature_df[self.feature_columns].fillna(feature_df[self.feature_columns].median())
        
        # Base prediction
        base_pred = float(self.model.predict(X)[0])
        
        # Monte Carlo uncertainty estimation
        predictions = []
        for _ in range(n_iterations):
            # Add small noise to inputs
            X_noisy = X + np.random.normal(0, 0.01, X.shape)
            pred = float(self.model.predict(X_noisy)[0])
            predictions.append(pred)
        
        predictions = np.array(predictions)
        
        return {
            "predicted_cost": base_pred,
            "confidence_interval_90": (
                float(np.percentile(predictions, 5)),
                float(np.percentile(predictions, 95))
            ),
            "confidence_interval_95": (
                float(np.percentile(predictions, 2.5)),
                float(np.percentile(predictions, 97.5))
            ),
            "std_dev": float(np.std(predictions)),
            "median": float(np.median(predictions)),
            "model_version": "1.0",
        }
    
    def save(self, output_dir: Path) -> None:
        """Save model and metadata."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model
        model_path = output_dir / "model.pkl"
        joblib.dump(self.model, model_path)
        
        # Save metadata
        metadata = {
            "feature_columns": self.feature_columns,
            "feature_importances": self.feature_importances_.to_dict(orient="records") if self.feature_importances_ is not None else None,
            "training_metrics": self.training_metrics,
            "use_gpu": self.use_gpu,
            "version": "1.0",
        }
        
        metadata_path = output_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info("model.saved", path=str(output_dir))
        
        logger.info(f"\n💾 Model saved to: {output_dir}")
        logger.info(f"   • model.pkl")
        logger.info(f"   • metadata.json")
    
    @classmethod
    def load(cls, model_dir: Path) -> CostPredictor:
        """Load model from disk."""
        model_dir = Path(model_dir)
        
        # Load metadata
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path) as f:
            metadata = json.load(f)
        
        # Load model
        model_path = model_dir / "model.pkl"
        model = joblib.load(model_path)
        
        # Reconstruct predictor
        predictor = cls(use_gpu=metadata.get("use_gpu", False))
        predictor.model = model
        predictor.feature_columns = metadata["feature_columns"]
        predictor.training_metrics = metadata.get("training_metrics")
        
        if metadata.get("feature_importances"):
            predictor.feature_importances_ = pd.DataFrame(metadata["feature_importances"])
        
        logger.info("model.loaded", path=str(model_dir))
        
        return predictor

