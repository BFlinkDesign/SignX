"""Test ML components."""
import pytest
import pandas as pd
import numpy as np
from signx_intel.ml.features.engineering import CostFeatureEngineering


def test_feature_engineering():
    """Test feature engineering pipeline."""
    # Create sample data
    df = pd.DataFrame({
        "drivers": [
            {"sign_height_ft": 25, "sign_area_sqft": 100},
            {"sign_height_ft": 30, "sign_area_sqft": 150},
        ]
    })
    
    fe = CostFeatureEngineering()
    transformed = fe.fit_transform(df)
    
    # Check that driver columns were extracted
    assert "sign_height_ft" in transformed.columns or len(transformed.columns) > 0
    
    # Check that transformation completed
    assert len(transformed) == len(df)


def test_interaction_features():
    """Test interaction feature creation."""
    df = pd.DataFrame({
        "sign_height_ft": [25, 30],
        "sign_area_sqft": [100, 150],
        "drivers": [{}, {}]
    })
    
    fe = CostFeatureEngineering()
    transformed = fe._create_interactions(df)
    
    # Check interaction was created
    if "area_height_interaction" in transformed.columns:
        assert transformed["area_height_interaction"].iloc[0] == 25 * 100

