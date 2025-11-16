#!/usr/bin/env python3
"""Train GPU-accelerated cost prediction model.

Usage:
    python scripts/train_cost_model.py --data data/raw/extracted_costs.parquet --output models/cost/v1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import structlog

# Add services to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ml.cost_model import CostPredictor
import logging

logger = logging.getLogger(__name__)

logger = structlog.get_logger(__name__)


def main():
    """Main training pipeline."""
    parser = argparse.ArgumentParser(description="Train cost prediction model")
    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="Path to training data parquet file"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("models/cost/v1"),
        help="Output directory for trained model"
    )
    parser.add_argument(
        "--no-gpu",
        action="store_true",
        help="Disable GPU acceleration (use CPU only)"
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of data to use for testing"
    )
    
    args = parser.parse_args()
    
    # Load data
    logger.info(f"\n📂 Loading training data from: {args.data}")
    
    if not args.data.exists():
        logger.error(f"ERROR: Data file not found: {args.data}")
        logger.info(f"\nRun extraction first:")
        logger.info(f"  python scripts/extract_pdfs.py --input data/pdfs/cost_summaries --output {args.data}")
        sys.exit(1)
    
    df = pd.read_parquet(args.data)
    
    logger.info(f"✅ Loaded {len(df):,} records")
    logger.info(f"\nDataset summary:")
    logger.info(f"  Date range: {df['quote_date'].min()} to {df['quote_date'].max()}")
    logger.info(f"  Cost range: ${df['total_cost'].min():,.2f} to ${df['total_cost'].max():,.2f}")
    logger.info(f"  Mean cost: ${df['total_cost'].mean():,.2f}")
    
    # Initialize model
    use_gpu = not args.no_gpu
    
    logger.info(f"\n🎯 Training model (GPU: {use_gpu})...")
    
    predictor = CostPredictor(use_gpu=use_gpu)
    
    # Train
    metrics = predictor.train(df, test_size=args.test_size)
    
    # Display results
    logger.info(f"\n📊 Training Results:")
    logger.info(f"   Training MAE: ${metrics['train_mae']:,.2f}")
    logger.info(f"   Test MAE: ${metrics['test_mae']:,.2f}")
    logger.info(f"   Training MAPE: {metrics['train_mape']:.1f}%")
    logger.info(f"   Test MAPE: {metrics['test_mape']:.1f}%")
    logger.info(f"   Training R²: {metrics['train_r2']:.3f}")
    logger.info(f"   Test R²: {metrics['test_r2']:.3f}")
    logger.info(f"   Training time: {metrics['training_time_seconds']:.2f}s")
    
    # Feature importance
    logger.info(f"\n🎯 Top 10 Most Important Features:")
    if predictor.feature_importances_ is not None:
        top_features = predictor.feature_importances_.head(10)
        for idx, row in top_features.iterrows():
            logger.info(f"   {idx+1:2d}. {row['feature']:30s} {row['importance']:.4f}")
    
    # Save model
    predictor.save(args.output)
    
    # Test prediction
    logger.info(f"\n🧪 Testing prediction on sample design...")
    
    sample_design = {
        "height_ft": 25.0,
        "sign_area_sqft": 80.0,
        "wind_speed_mph": 115.0,
        "exposure_code": 1,  # Exposure C
        "importance_factor": 1.0,
        "pole_type_code": 0,  # Round HSS
        "pole_size": 8.0,
        "pole_thickness_in": 0.25,
        "pole_height_ft": 20.0,
        "foundation_type_code": 0,  # Direct burial
        "embedment_depth_ft": 8.0,
        "concrete_volume_cuyd": 10.0,
        "soil_bearing_psf": 3000.0,
        "snow_load_psf": 0.0,
    }
    
    prediction = predictor.predict_with_uncertainty(sample_design)
    
    logger.info(f"\nSample Design:")
    logger.info(f"   Height: {sample_design['height_ft']} ft")
    logger.info(f"   Sign Area: {sample_design['sign_area_sqft']} sqft")
    logger.info(f"   Wind Speed: {sample_design['wind_speed_mph']} mph")
    logger.info(f"   Pole: {sample_design['pole_size']}\" Round HSS")
    
    logger.info(f"\n💰 Cost Prediction:")
    logger.info(f"   Estimated: ${prediction['predicted_cost']:,.2f}")
    logger.info(f"   90% CI: ${prediction['confidence_interval_90'][0]:,.2f} - ${prediction['confidence_interval_90'][1]:,.2f}")
    logger.info(f"   Std Dev: ${prediction['std_dev']:,.2f}")
    
    logger.info(f"\n✅ Model training complete!")
    logger.info(f"\nNext steps:")
    logger.info(f"   1. Review feature importances above")
    logger.info(f"   2. Test predictions: python scripts/test_cost_model.py")
    logger.info(f"   3. Deploy to API: Add to services/api/src/apex/api/routes/ai.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

