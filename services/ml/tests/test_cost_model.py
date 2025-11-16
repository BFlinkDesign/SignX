"""Tests for cost prediction model."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ..cost_model import CostPredictor


@pytest.fixture
def sample_training_data():
    """Generate sample training data for testing."""
    np.random.seed(42)
    
    n_samples = 100
    
    data = {
        "project_id": [f"PROJ-{i:04d}" for i in range(n_samples)],
        "height_ft": np.random.uniform(15, 40, n_samples),
        "sign_area_sqft": np.random.uniform(30, 200, n_samples),
        "wind_speed_mph": np.random.uniform(90, 130, n_samples),
        "exposure_code": np.random.choice([0, 1, 2], n_samples),
        "importance_factor": np.ones(n_samples),
        "pole_type_code": np.random.choice([0, 1, 2], n_samples),
        "pole_size": np.random.choice([6, 8, 10, 12], n_samples),
        "pole_thickness_in": np.random.uniform(0.188, 0.5, n_samples),
        "pole_height_ft": np.random.uniform(15, 40, n_samples),
        "foundation_type_code": np.random.choice([0, 1, 2], n_samples),
        "embedment_depth_ft": np.random.uniform(4, 12, n_samples),
        "concrete_volume_cuyd": np.random.uniform(5, 20, n_samples),
        "soil_bearing_psf": np.ones(n_samples) * 3000,
        "snow_load_psf": np.zeros(n_samples),
        "quote_date": pd.date_range("2020-01-01", periods=n_samples, freq="10D"),
    }
    
    # Generate realistic costs based on features
    data["total_cost"] = (
        5000 +
        data["height_ft"] * 150 +
        data["sign_area_sqft"] * 50 +
        data["pole_size"] * 200 +
        data["embedment_depth_ft"] * 180 +
        np.random.normal(0, 500, n_samples)  # Random noise
    )
    
    return pd.DataFrame(data)


def test_cost_predictor_initialization():
    """Test CostPredictor initialization."""
    predictor = CostPredictor(use_gpu=False)
    
    assert predictor.model is not None
    assert predictor.feature_columns is None
    assert predictor.use_gpu is False


def test_engineer_features(sample_training_data):
    """Test feature engineering."""
    predictor = CostPredictor(use_gpu=False)
    
    engineered = predictor._engineer_features(sample_training_data)
    
    # Check derived features exist
    assert "aspect_ratio" in engineered.columns
    assert "slenderness_ratio" in engineered.columns
    assert "wind_pressure_psf" in engineered.columns
    assert "cost_per_sqft" in engineered.columns
    
    # Check calculations
    assert engineered["aspect_ratio"].notna().all()
    assert (engineered["wind_pressure_psf"] > 0).all()


def test_prepare_training_data(sample_training_data):
    """Test training data preparation."""
    predictor = CostPredictor(use_gpu=False)
    
    X, y = predictor.prepare_training_data(sample_training_data)
    
    assert len(X) == len(sample_training_data)
    assert len(y) == len(sample_training_data)
    assert predictor.feature_columns is not None
    assert len(predictor.feature_columns) > 10
    
    # Check no nulls in features
    assert X.isna().sum().sum() == 0


def test_model_training(sample_training_data):
    """Test model training pipeline."""
    predictor = CostPredictor(use_gpu=False)
    
    metrics = predictor.train(sample_training_data, test_size=0.2)
    
    # Check metrics exist
    assert "test_mae" in metrics
    assert "test_r2" in metrics
    assert "test_mape" in metrics
    assert "training_time_seconds" in metrics
    
    # Check reasonable performance
    assert metrics["test_r2"] > 0.7  # R² should be decent
    assert metrics["test_mape"] < 30  # MAPE should be reasonable
    
    # Check feature importances calculated
    assert predictor.feature_importances_ is not None
    assert len(predictor.feature_importances_) > 0


def test_predict_with_uncertainty(sample_training_data):
    """Test prediction with uncertainty quantification."""
    predictor = CostPredictor(use_gpu=False)
    predictor.train(sample_training_data, test_size=0.2)
    
    # Test prediction
    test_features = {
        "height_ft": 25.0,
        "sign_area_sqft": 75.0,
        "wind_speed_mph": 115.0,
        "exposure_code": 1,
        "importance_factor": 1.0,
        "pole_type_code": 0,
        "pole_size": 8.0,
        "pole_thickness_in": 0.25,
        "pole_height_ft": 25.0,
        "foundation_type_code": 0,
        "embedment_depth_ft": 8.0,
        "concrete_volume_cuyd": 10.0,
        "soil_bearing_psf": 3000.0,
        "snow_load_psf": 0.0,
    }
    
    prediction = predictor.predict_with_uncertainty(test_features)
    
    # Check prediction structure
    assert "predicted_cost" in prediction
    assert "confidence_interval_90" in prediction
    assert "confidence_interval_95" in prediction
    assert "std_dev" in prediction
    
    # Check reasonable values
    assert prediction["predicted_cost"] > 0
    assert prediction["std_dev"] > 0
    assert prediction["confidence_interval_90"][0] < prediction["predicted_cost"]
    assert prediction["confidence_interval_90"][1] > prediction["predicted_cost"]


def test_model_save_load(sample_training_data, tmp_path):
    """Test model persistence."""
    predictor = CostPredictor(use_gpu=False)
    predictor.train(sample_training_data, test_size=0.2)
    
    # Save
    model_dir = tmp_path / "test_model"
    predictor.save(model_dir)
    
    assert (model_dir / "model.pkl").exists()
    assert (model_dir / "metadata.json").exists()
    
    # Load
    loaded_predictor = CostPredictor.load(model_dir)
    
    assert loaded_predictor.feature_columns == predictor.feature_columns
    assert loaded_predictor.training_metrics == predictor.training_metrics
    
    # Test prediction matches
    test_features = {
        "height_ft": 20.0,
        "sign_area_sqft": 60.0,
        "wind_speed_mph": 115.0,
        "exposure_code": 1,
        "importance_factor": 1.0,
        "pole_type_code": 0,
        "pole_size": 8.0,
        "pole_thickness_in": 0.25,
        "pole_height_ft": 20.0,
        "foundation_type_code": 0,
        "embedment_depth_ft": 8.0,
        "concrete_volume_cuyd": 10.0,
        "soil_bearing_psf": 3000.0,
        "snow_load_psf": 0.0,
    }
    
    pred1 = predictor.predict_with_uncertainty(test_features)
    pred2 = loaded_predictor.predict_with_uncertainty(test_features, n_iterations=100)
    
    # Predictions should be close (some variance due to Monte Carlo)
    assert abs(pred1["predicted_cost"] - pred2["predicted_cost"]) < pred1["predicted_cost"] * 0.1

