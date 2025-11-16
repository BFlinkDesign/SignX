#!/usr/bin/env python3
"""Seed AISC sections database from Excel file."""

import os
import sys
import hashlib
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pandas as pd
except ImportError:
    logger.error("Error: pandas not installed. Run: pip install pandas openpyxl")
    sys.exit(1)

from sqlalchemy import create_engine, text


def seed_aisc_sections():
    """Seed AISC sections from Excel file."""
    # Database connection
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://apex:apex@localhost:5432/apex"
    )
    
    # Excel file path
    EXCEL_FILE = Path(__file__).parent.parent.parent / "scripts" / "data" / "aisc_shapes_v16.xlsx"
    
    if not EXCEL_FILE.exists():
        logger.warning(f"Warning: Excel file not found at {EXCEL_FILE}")
        logger.info("Please download from https://www.aisc.org/resources/shapes-database/")
        logger.info("and save as scripts/data/aisc_shapes_v16.xlsx")
        return
    
    # Read Excel file
    logger.info(f"Reading AISC sections from {EXCEL_FILE}...")
    
    try:
        # Try different sheet names
        df = None
        for sheet in ["Database v16.0", "Sheet1", "Database v15.0"]:
            try:
                df = pd.read_excel(EXCEL_FILE, sheet_name=sheet)
                logger.info(f"Successfully read sheet: {sheet}")
                break
            except (ValueError, FileNotFoundError):
                continue
        
        if df is None:
            logger.error(f"Error: Could not read any sheets from {EXCEL_FILE}")
            logger.info(f"Available sheets: {pd.ExcelFile(EXCEL_FILE).sheet_names}")
            return
        
        logger.info(f"Loaded {len(df)} total rows")
        
        # Filter to relevant types
        if 'Type' in df.columns:
            df_filtered = df[df['Type'].isin(['HSS', 'PIPE', 'W'])].copy()
            logger.info(f"Filtered to {len(df_filtered)} HSS/PIPE/W shapes")
        else:
            logger.warning("Warning: No 'Type' column found, using all rows")
            df_filtered = df.copy()
        
        # Get file hash for provenance
        with open(EXCEL_FILE, 'rb') as f:
            source_sha = hashlib.sha256(f.read()).hexdigest()
        
        logger.info(f"Source SHA256: {source_sha[:16]}...")
        
        # Map column names
        column_map = {
            'AISC_Manual_Label': 'designation',
            'Type': 'shape_type',
            'W': 'weight_lbs_per_ft',
            'A': 'area_in2',
            'Ix': 'ix_in4',
            'Sx': 'sx_in3',
            'Fy': 'fy_ksi',
        }
        
        # Rename columns
        df_filtered = df_filtered.rename(columns=column_map)
        
        # Keep only columns that exist
        keep_cols = [col for col in ['designation', 'shape_type', 'weight_lbs_per_ft', 
                                     'area_in2', 'ix_in4', 'sx_in3', 'fy_ksi'] if col in df_filtered.columns]
        
        # Add required columns
        df_filtered['edition'] = '16.0'
        df_filtered['source_sha256'] = source_sha
        
        # Filter rows with required data
        if 'designation' in df_filtered.columns and 'shape_type' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['designation'].notna()]
            df_filtered = df_filtered[df_filtered['shape_type'].notna()]
        
        logger.info(f"Final count: {len(df_filtered)} rows to import")
        
        # Connect to database
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Check if table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'pole_sections'
                )
            """))
            if not result.scalar():
                logger.error("Error: pole_sections table does not exist. Run migrations first.")
                logger.info("Run: docker compose exec api alembic upgrade head")
                return
            
            # Delete existing data
            conn.execute(text("DELETE FROM pole_sections"))
            conn.commit()
            logger.info("Cleared existing pole_sections data")
            
            # Insert new data
            df_filtered[keep_cols + ['edition', 'source_sha256']].to_sql(
                'pole_sections',
                conn,
                if_exists='append',
                index=False,
                method='multi',
                chunksize=100
            )
            conn.commit()
            
            # Verify
            result = conn.execute(text("SELECT COUNT(*) FROM pole_sections"))
            count = result.scalar()
            logger.info(f"✅ Successfully seeded {count} AISC sections")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
import logging

logger = logging.getLogger(__name__)
        traceback.print_exc()


if __name__ == "__main__":
    seed_aisc_sections()

