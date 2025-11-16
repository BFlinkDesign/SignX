#!/usr/bin/env python3
"""Extract cost data from PDF summaries and create training dataset.

Usage:
    python scripts/extract_pdfs.py --input data/pdfs/cost_summaries --output data/raw/extracted_costs.parquet
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import structlog

# Add services to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ml.pdf_extractor import extract_pdf_batch
from services.ml.data_validator import DataValidator
import logging

logger = logging.getLogger(__name__)

logger = structlog.get_logger(__name__)


def main():
    """Main extraction pipeline."""
    parser = argparse.ArgumentParser(description="Extract cost data from PDF summaries")
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Directory containing PDF cost summaries"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/raw/extracted_costs.parquet"),
        help="Output parquet file path"
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/extraction_report.json"),
        help="Quality report output path"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        structlog.configure(
            processors=[
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.dev.ConsoleRenderer()
            ]
        )
    
    # Validate input directory
    if not args.input.exists():
        logger.error("input.not_found", path=str(args.input))
        logger.error(f"ERROR: Input directory not found: {args.input}")
        sys.exit(1)
    
    # Extract PDFs
    logger.info(f"\n📂 Extracting PDFs from: {args.input}")
    logger.info(f"📊 Output dataset: {args.output}\n")
    
    valid_records, error_records = extract_pdf_batch(args.input, args.output)
    
    logger.info(f"\n✅ Extraction complete:")
    logger.info(f"   Valid records: {len(valid_records)}")
    logger.error(f"   Failed extractions: {len(error_records)}")
    
    # Validate extracted data
    if valid_records:
        logger.info(f"\n🔍 Running data quality validation...")
        
        df = pd.read_parquet(args.output)
        validator = DataValidator(df)
        quality_report = validator.validate()
        
        logger.info(f"\n📊 Data Quality Report:")
        logger.info(f"   Total records: {quality_report.total_records}")
        logger.info(f"   Valid records: {quality_report.valid_records}")
        logger.info(f"   Invalid records: {quality_report.invalid_records}")
        logger.info(f"   Completeness: {quality_report.completeness_percent:.1f}%")
        logger.info(f"   Cost range: ${quality_report.cost_range[0]:,.2f} - ${quality_report.cost_range[1]:,.2f}")
        
        if quality_report.date_range[0]:
            logger.info(f"   Date range: {quality_report.date_range[0]} to {quality_report.date_range[1]}")
        
        if quality_report.warnings:
            logger.warning(f"\n⚠️  Warnings ({len(quality_report.warnings)}):")
            for warning in quality_report.warnings[:5]:  # Show first 5
                logger.warning(f"   • {warning}")
        
        if quality_report.errors:
            logger.error(f"\n❌ Errors ({len(quality_report.errors)}):")
            for error in quality_report.errors[:5]:
                logger.error(f"   • {error}")
        
        # Save quality report
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with open(args.report, "w") as f:
            json.dump(quality_report.model_dump(), f, indent=2, default=str)
        
        logger.info(f"\n💾 Quality report saved to: {args.report}")
        
        # Show summary statistics
        logger.info(f"\n📈 Summary Statistics:")
        summary = validator.generate_summary_statistics()
        logger.info(summary.to_string())
    
    # Show errors if any
    if error_records:
        logger.error(f"\n❌ Failed PDFs:")
        for err in error_records[:10]:  # Show first 10
            logger.error(f"   • {Path(err['file']).name}: {err.get('error_type', 'unknown')}")
    
    logger.info(f"\n✅ Extraction pipeline complete!")
    logger.info(f"\nNext steps:")
    logger.info(f"   1. Review quality report: {args.report}")
    logger.info(f"   2. Check extracted data: {args.output}")
    logger.info(f"   3. Run training: python scripts/train_cost_model.py")
    
    return 0 if not error_records else 1


if __name__ == "__main__":
    sys.exit(main())

