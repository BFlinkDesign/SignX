#!/usr/bin/env python3
"""Test AI cost prediction model with sample designs.

Usage:
    python scripts/test_ai_prediction.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add services to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ml.cost_model import CostPredictor


def main():
    """Test cost prediction with various design scenarios."""
    
    print("\n" + "="*80)
    print("AI COST PREDICTION TEST SUITE")
    print("="*80 + "\n")
    
    # Load model
    model_path = Path("models/cost/v1")
    
    if not model_path.exists():
        print("❌ Model not found. Train model first:")
        print("   python scripts/train_cost_model.py --data data/raw/extracted_costs.parquet")
        return 1
    
    print(f"📂 Loading model from: {model_path}\n")
    predictor = CostPredictor.load(model_path)
    
    # Test scenarios
    scenarios = [
        {
            "name": "Small Monument Sign",
            "height_ft": 15.0,
            "sign_area_sqft": 40.0,
            "wind_speed_mph": 110.0,
            "pole_size": 6.0,
            "embedment_depth_ft": 6.0,
        },
        {
            "name": "Standard Pylon Sign",
            "height_ft": 25.0,
            "sign_area_sqft": 80.0,
            "wind_speed_mph": 115.0,
            "pole_size": 8.0,
            "embedment_depth_ft": 8.0,
        },
        {
            "name": "Large Pole Sign",
            "height_ft": 35.0,
            "sign_area_sqft": 150.0,
            "wind_speed_mph": 120.0,
            "pole_size": 10.0,
            "embedment_depth_ft": 10.0,
        },
    ]
    
    for scenario in scenarios:
        print(f"Scenario: {scenario['name']}")
        print("-" * 80)
        
        # Add default features
        features = {
            **scenario,
            "exposure_code": 1,  # Exposure C
            "importance_factor": 1.0,
            "pole_type_code": 0,  # Round HSS
            "pole_thickness_in": 0.25,
            "pole_height_ft": scenario["height_ft"],
            "foundation_type_code": 0,  # Direct burial
            "concrete_volume_cuyd": scenario["embedment_depth_ft"] * 1.2,
            "soil_bearing_psf": 3000.0,
            "snow_load_psf": 0.0,
        }
        
        # Predict
        prediction = predictor.predict_with_uncertainty(features)
        
        print(f"  Design:")
        print(f"    • Height: {scenario['height_ft']} ft")
        print(f"    • Sign Area: {scenario['sign_area_sqft']} sqft")
        print(f"    • Pole: {scenario['pole_size']}\" diameter")
        print(f"    • Foundation: {scenario['embedment_depth_ft']} ft deep")
        
        print(f"\n  💰 Cost Prediction:")
        print(f"    • Estimated: ${prediction['predicted_cost']:,.2f}")
        print(f"    • 90% CI: ${prediction['confidence_interval_90'][0]:,.2f} - ${prediction['confidence_interval_90'][1]:,.2f}")
        print(f"    • Uncertainty: ±${prediction['std_dev']:,.2f}")
        
        # Calculate interval width as % of prediction
        interval_width = prediction['confidence_interval_90'][1] - prediction['confidence_interval_90'][0]
        uncertainty_pct = (interval_width / prediction['predicted_cost']) * 100
        
        print(f"    • Uncertainty: ±{uncertainty_pct:.1f}%")
        print()
    
    # Show feature importances
    print("="*80)
    print("Top 10 Cost Drivers:")
    print("-"*80)
    
    if predictor.feature_importances_ is not None:
        top_10 = predictor.feature_importances_.head(10)
        for idx, row in top_10.iterrows():
            bar_length = int(row['importance'] * 50)
            bar = "█" * bar_length
            print(f"  {idx+1:2d}. {row['feature']:25s} {bar} {row['importance']:.3f}")
    
    print("\n" + "="*80)
    print("✅ AI cost prediction test complete!")
    print("="*80 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

