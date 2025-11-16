"""Cost prediction model training."""
import joblib
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

from signx_intel.ml.features.engineering import CostFeatureEngineering
from signx_intel.config import get_settings

settings = get_settings()


class CostPredictor:
    """XGBoost-based cost prediction model."""
    
    def __init__(self, model_path: Optional[str] = None):
        """Initialize predictor."""
        self.model = None
        self.feature_engineer = CostFeatureEngineering()
        self.model_path = Path(model_path or settings.model_path)
        self.model_path.mkdir(parents=True, exist_ok=True)
        self.metrics = {}
    
    def train(
        self,
        df: pd.DataFrame,
        target_col: str = "total_cost",
        test_size: float = 0.2,
        random_state: int = 42
    ) -> dict:
        """
        Train cost prediction model.
        
        Args:
            df: DataFrame with cost records
            target_col: Target column name
            test_size: Test set size
            random_state: Random seed
        
        Returns:
            Training metrics
        """
        print(f"Training on {len(df)} records...")
        
        # Separate features and target
        y = df[target_col]
        X = df.drop(columns=[target_col])
        
        # Feature engineering
        print("Engineering features...")
        X_transformed = self.feature_engineer.fit_transform(X)
        
        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X_transformed, y, test_size=test_size, random_state=random_state
        )
        
        print(f"Training set: {len(X_train)}, Test set: {len(X_test)}")
        
        # Train XGBoost model
        print("Training XGBoost model...")
        self.model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            tree_method='hist',  # Use 'gpu_hist' if GPU available
            random_state=random_state,
            n_jobs=-1
        )
        
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        
        # Evaluate
        print("Evaluating model...")
        y_pred = self.model.predict(X_test)
        
        self.metrics = {
            "mae": mean_absolute_error(y_test, y_pred),
            "rmse": np.sqrt(mean_squared_error(y_test, y_pred)),
            "r2": r2_score(y_test, y_pred),
            "train_size": len(X_train),
            "test_size": len(X_test)
        }
        
        print(f"✅ Training complete!")
        print(f"   MAE: ${self.metrics['mae']:.2f}")
        print(f"   RMSE: ${self.metrics['rmse']:.2f}")
        print(f"   R²: {self.metrics['r2']:.3f}")
        
        return self.metrics
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions.
        
        Args:
            X: Features DataFrame
        
        Returns:
            Predictions array
        """
        if self.model is None:
            raise ValueError("Model not trained or loaded")
        
        X_transformed = self.feature_engineer.transform(X)
        return self.model.predict(X_transformed)
    
    def save(self, name: str = "cost_predictor_v1"):
        """Save model and feature engineer."""
        if self.model is None:
            raise ValueError("No model to save")
        
        model_file = self.model_path / f"{name}.joblib"
        fe_file = self.model_path / f"{name}_feature_engineer.joblib"
        metrics_file = self.model_path / f"{name}_metrics.joblib"
        
        joblib.dump(self.model, model_file)
        joblib.dump(self.feature_engineer, fe_file)
        joblib.dump(self.metrics, metrics_file)
        
        print(f"✅ Model saved to {model_file}")
    
    def load(self, name: str = "cost_predictor_v1"):
        """Load model and feature engineer."""
        model_file = self.model_path / f"{name}.joblib"
        fe_file = self.model_path / f"{name}_feature_engineer.joblib"
        metrics_file = self.model_path / f"{name}_metrics.joblib"
        
        if not model_file.exists():
            raise FileNotFoundError(f"Model not found: {model_file}")
        
        self.model = joblib.load(model_file)
        self.feature_engineer = joblib.load(fe_file)
        
        if metrics_file.exists():
            self.metrics = joblib.load(metrics_file)
        
        print(f"✅ Model loaded from {model_file}")
        if self.metrics:
            print(f"   Model metrics - MAE: ${self.metrics.get('mae', 0):.2f}, R²: {self.metrics.get('r2', 0):.3f}")


def main():
    """CLI entry point for training."""
    # TODO: Load data from database or Parquet files
    print("Cost Predictor Training")
    print("=" * 50)
    print("\nTo train a model:")
    print("1. Add your cost data to the database")
    print("2. Export to DataFrame")
    print("3. Call predictor.train(df)")
    print("\nExample:")
    print("  predictor = CostPredictor()")
    print("  predictor.train(df)")
    print("  predictor.save('my_model_v1')")


if __name__ == "__main__":
    main()

