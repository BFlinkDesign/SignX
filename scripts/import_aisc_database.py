#!/usr/bin/env python
"""
Import AISC Shapes Database v16.0 into APEX
Uses existing Excel files from H:/BOT TRAINING/Engineering
"""

import pandas as pd
import asyncio
import asyncpg
import json
from pathlib import Path
import sys

import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Build database URL from environment variables
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "signx_studio")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Engineering resources path
ENGINEERING_PATH = Path("H:/BOT TRAINING/Engineering")

# Database connection
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


async def create_shapes_table(conn):
    """Create comprehensive AISC shapes table"""
    
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS aisc_shapes_v16 (
        id SERIAL PRIMARY KEY,
        type VARCHAR(20) NOT NULL,
        edi_std_nomenclature VARCHAR(100),
        aisc_manual_label VARCHAR(100) UNIQUE NOT NULL,
        
        -- Material spec
        t_f VARCHAR(10),  -- Material spec (A36, A572, etc.)
        
        -- Weight and area
        w FLOAT,  -- Weight per foot (lb/ft)
        area FLOAT,  -- Cross-sectional area (in²)
        
        -- Dimensions
        d FLOAT,  -- Depth (in)
        d_det FLOAT,  -- Detailed depth
        ht FLOAT,  -- Height
        h FLOAT,  -- Clear distance between flanges
        od FLOAT,  -- Outside diameter (pipes)
        bf FLOAT,  -- Flange width
        bf_det FLOAT,  -- Detailed flange width
        b FLOAT,  -- Width
        id_dim FLOAT,  -- Inside diameter (pipes)
        tw FLOAT,  -- Web thickness
        tw_det FLOAT,  -- Detailed web thickness
        tf FLOAT,  -- Flange thickness
        tf_det FLOAT,  -- Detailed flange thickness
        
        -- Section properties - Strong axis
        ix FLOAT,  -- Moment of inertia (in⁴)
        sx FLOAT,  -- Section modulus (in³)
        rx FLOAT,  -- Radius of gyration (in)
        zx FLOAT,  -- Plastic modulus (in³)
        
        -- Section properties - Weak axis  
        iy FLOAT,  -- Moment of inertia (in⁴)
        sy FLOAT,  -- Section modulus (in³)
        ry FLOAT,  -- Radius of gyration (in)
        zy FLOAT,  -- Plastic modulus (in³)
        
        -- Torsional properties
        j FLOAT,  -- Torsional constant (in⁴)
        cw FLOAT,  -- Warping constant (in⁶)
        rts FLOAT,  -- Effective radius of gyration
        ho FLOAT,  -- Distance between flange centroids
        
        -- Additional properties for HSS
        torsion_constant FLOAT,
        tdes FLOAT,  -- Design wall thickness
        wt_class VARCHAR(20),  -- Weight class
        
        -- Shear properties
        aw FLOAT,  -- Web area
        
        -- Compact/slender criteria
        bf_2tf FLOAT,  -- Flange slenderness
        h_tw FLOAT,  -- Web slenderness
        
        -- For angles
        x_bar FLOAT,  -- X centroid
        y_bar FLOAT,  -- Y centroid
        ro FLOAT,  -- Polar radius of gyration
        h_bar FLOAT,  -- H value for single angles
        
        -- Availability flags
        is_available BOOLEAN DEFAULT true,
        is_astm_a1085 BOOLEAN DEFAULT false,  -- For HSS
        
        -- Search optimization
        nominal_depth INTEGER,  -- Rounded depth for quick filtering
        nominal_weight INTEGER,  -- Rounded weight for quick filtering
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        -- Indexes for common queries
        INDEX idx_type (type),
        INDEX idx_weight (w),
        INDEX idx_sx (sx),
        INDEX idx_ix (ix),
        INDEX idx_nominal (nominal_depth, nominal_weight),
        INDEX idx_label_search (aisc_manual_label)
    );
    
    -- Create view for sign-relevant shapes
    CREATE OR REPLACE VIEW sign_pole_sections AS
    SELECT 
        aisc_manual_label as designation,
        type,
        w as weight_plf,
        area as area_in2,
        ix as ix_in4,
        sx as sx_in3,
        rx as rx_in,
        zx as zx_in3,
        j as j_in4,
        CASE 
            WHEN type = 'HSS' THEN d * 2.5  -- Max cantilever = 2.5 * width
            WHEN type = 'PIPE' THEN d * 2.0
            WHEN type = 'W' THEN d * 1.5
            ELSE d
        END as max_cantilever_ft
    FROM aisc_shapes_v16
    WHERE type IN ('HSS', 'PIPE', 'W', 'WT')
        AND w > 10  -- Min 10 lb/ft for signs
        AND sx > 5  -- Min section modulus
    ORDER BY type, w;
    
    -- Create table for special sign sections not in AISC
    CREATE TABLE IF NOT EXISTS custom_sign_sections (
        id SERIAL PRIMARY KEY,
        designation VARCHAR(100) UNIQUE NOT NULL,
        type VARCHAR(50),  -- 'ALUMINUM', 'COMPOSITE', 'CUSTOM_STEEL'
        material VARCHAR(50),  -- '6061-T6', 'A572-50', etc.
        weight_plf FLOAT,
        area_in2 FLOAT,
        ix_in4 FLOAT,
        sx_in3 FLOAT,
        rx_in FLOAT,
        iy_in4 FLOAT,
        sy_in3 FLOAT,
        ry_in FLOAT,
        j_in4 FLOAT,
        max_span_ft FLOAT,  -- Max recommended cantilever
        cost_per_ft DECIMAL(10,2),
        supplier VARCHAR(100),
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    logger.info("[OK] Created aisc_shapes_v16 table")
    logger.info("[OK] Created sign_pole_sections view")
    logger.info("[OK] Created custom_sign_sections table")


async def import_aisc_data(conn):
    """Import AISC shapes from Excel"""
    
    # Load main AISC database
    main_file = ENGINEERING_PATH / "aisc-shapes-database-v16.0.xlsx"
    logger.info(f"\nReading {main_file}...")
    
    df = pd.read_excel(main_file, sheet_name='Database v16.0')
    logger.info(f"Found {len(df)} shapes")
    
    # Clean column names (remove spaces, lowercase)
    df.columns = [col.lower().replace(' ', '_').replace('/', '_') for col in df.columns]
    
    # Helper function to safely convert to float
    def safe_float(val, default=None):
        if pd.isna(val):
            return default
        if isinstance(val, str):
            # Handle strings with special characters
            val = val.replace('�', '').replace('-', '').strip()
            if not val:
                return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default
    
    # Prepare data for insertion
    records = []
    skipped = 0
    for _, row in df.iterrows():
        # Skip rows without valid designation
        if pd.isna(row.get('aisc_manual_label')):
            skipped += 1
            continue
            
        # Calculate nominal values for search optimization
        nominal_depth = int(safe_float(row.get('d'), 0) or 0)
        nominal_weight = int(safe_float(row.get('w'), 0) or 0)
        
        record = {
            'type': str(row.get('type', '')),
            'edi_std_nomenclature': str(row.get('edi_std_nomenclature', '')) if pd.notna(row.get('edi_std_nomenclature')) else None,
            'aisc_manual_label': str(row.get('aisc_manual_label')),
            't_f': str(row.get('t_f', '')) if pd.notna(row.get('t_f')) else None,
            'w': safe_float(row.get('w')),
            'area': safe_float(row.get('a')),
            'd': safe_float(row.get('d')),
            'bf': safe_float(row.get('bf')),
            'tw': safe_float(row.get('tw')),
            'tf': safe_float(row.get('tf')),
            'ix': safe_float(row.get('ix')),
            'sx': safe_float(row.get('sx')),
            'rx': safe_float(row.get('rx')),
            'zx': safe_float(row.get('zx')),
            'iy': safe_float(row.get('iy')),
            'sy': safe_float(row.get('sy')),
            'ry': safe_float(row.get('ry')),
            'zy': safe_float(row.get('zy')),
            'j': safe_float(row.get('j')),
            'cw': safe_float(row.get('cw')),
            'nominal_depth': nominal_depth,
            'nominal_weight': nominal_weight,
        }
        records.append(record)
    
    if skipped:
        logger.info(f"Skipped {skipped} invalid rows")
    
    # Batch insert
    logger.info(f"\nInserting {len(records)} shapes...")
    
    # Insert in batches using executemany
    if records:
        columns = list(records[0].keys())
        
        # Build INSERT query
        placeholders = ', '.join(f'${i+1}' for i in range(len(columns)))
        columns_str = ', '.join(columns)
        
        query = f"""
        INSERT INTO aisc_shapes_v16 ({columns_str})
        VALUES ({placeholders})
        ON CONFLICT (aisc_manual_label) DO NOTHING
        """
        
        # Convert records to tuples
        values = [tuple(r[col] for col in columns) for r in records]
        
        # Insert in batches of 100
        batch_size = 100
        for i in range(0, len(values), batch_size):
            batch = values[i:i + batch_size]
            await conn.executemany(query, batch)
            if (i + batch_size) % 500 == 0:
                logger.info(f"  Inserted {min(i + batch_size, len(values))}/{len(values)} shapes...")
    
    logger.info(f"[OK] Imported {len(records)} AISC shapes")
    
    # Now import A1085 HSS shapes
    a1085_file = ENGINEERING_PATH / "aisc-shapes-database-v16.0_a1085.xlsx"
    if a1085_file.exists():
        logger.info(f"\nReading A1085 HSS shapes from {a1085_file}...")
        df_a1085 = pd.read_excel(a1085_file, sheet_name='v16.0 Database_A1085 ')
        
        # Update existing HSS shapes to mark as A1085
        a1085_labels = df_a1085['AISC_Manual_Label'].tolist() if 'AISC_Manual_Label' in df_a1085.columns else []
        
        if a1085_labels:
            await conn.execute("""
                UPDATE aisc_shapes_v16 
                SET is_astm_a1085 = true 
                WHERE aisc_manual_label = ANY($1::text[])
            """, a1085_labels)
            logger.info(f"[OK] Marked {len(a1085_labels)} shapes as ASTM A1085")


async def add_custom_sign_sections(conn):
    """Add aluminum and special sign sections"""
    
    custom_sections = [
        # Common aluminum sections for signs
        ('AL-4X4X1/4', 'ALUMINUM', '6061-T6', 4.38, 1.29, 2.73, 1.37, 1.45, 2.73, 1.37, 1.45, 1.82, 15.0, 8.50),
        ('AL-6X6X3/8', 'ALUMINUM', '6061-T6', 9.85, 2.89, 13.7, 4.57, 2.18, 13.7, 4.57, 2.18, 9.13, 20.0, 12.00),
        ('AL-8X8X1/2', 'ALUMINUM', '6061-T6', 17.54, 5.15, 43.3, 10.8, 2.90, 43.3, 10.8, 2.90, 28.9, 25.0, 18.00),
        
        # Breakaway posts
        ('BREAKAWAY-3X3', 'BREAKAWAY', 'A36', 7.11, 2.09, 3.02, 2.01, 1.20, 3.02, 2.01, 1.20, 2.01, 8.0, 25.00),
        
        # Square tube (non-HSS)
        ('SQ-4X4X3/16', 'SQUARE_TUBE', 'A500B', 6.87, 2.02, 5.41, 2.70, 1.64, 5.41, 2.70, 1.64, 8.45, 12.0, 4.50),
    ]
    
    for section in custom_sections:
        await conn.execute("""
            INSERT INTO custom_sign_sections 
            (designation, type, material, weight_plf, area_in2, ix_in4, sx_in3, rx_in, 
             iy_in4, sy_in3, ry_in, j_in4, max_span_ft, cost_per_ft)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (designation) DO NOTHING
        """, *section)
    
    logger.info(f"[OK] Added {len(custom_sections)} custom sign sections")


async def create_material_cost_table(conn):
    """Create table for tracking material costs"""
    
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS material_cost_indices (
        id SERIAL PRIMARY KEY,
        material VARCHAR(50) NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        index_value FLOAT NOT NULL,  -- 100 = baseline
        price_per_lb DECIMAL(10,4),
        source VARCHAR(100),
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(material, year, month)
    );
    
    -- Insert historical indices (from ENR or other sources)
    INSERT INTO material_cost_indices (material, year, month, index_value, price_per_lb, source)
    VALUES 
        -- Steel indices (example values)
        ('STEEL_STRUCTURAL', 2020, 1, 100.0, 0.65, 'ENR'),
        ('STEEL_STRUCTURAL', 2021, 1, 115.2, 0.75, 'ENR'),
        ('STEEL_STRUCTURAL', 2022, 1, 142.8, 0.93, 'ENR'),
        ('STEEL_STRUCTURAL', 2023, 1, 128.5, 0.84, 'ENR'),
        ('STEEL_STRUCTURAL', 2024, 1, 135.2, 0.88, 'ENR'),
        ('STEEL_STRUCTURAL', 2025, 1, 138.7, 0.90, 'ENR'),
        
        -- Aluminum indices
        ('ALUMINUM_6061', 2020, 1, 100.0, 1.85, 'LME'),
        ('ALUMINUM_6061', 2021, 1, 108.5, 2.01, 'LME'),
        ('ALUMINUM_6061', 2022, 1, 125.3, 2.32, 'LME'),
        ('ALUMINUM_6061', 2023, 1, 118.2, 2.19, 'LME'),
        ('ALUMINUM_6061', 2024, 1, 122.5, 2.27, 'LME'),
        ('ALUMINUM_6061', 2025, 1, 124.8, 2.31, 'LME')
    ON CONFLICT DO NOTHING;
    """)
    
    logger.info("[OK] Created material cost tracking table")


async def create_sign_specific_views(conn):
    """Create views optimized for sign calculations"""
    
    await conn.execute("""
    -- View for cantilever sign poles
    CREATE OR REPLACE VIEW cantilever_pole_sections AS
    SELECT 
        aisc_manual_label as designation,
        type,
        w as weight_plf,
        area as area_in2,
        ix as ix_in4,
        sx as sx_in3,
        zx as zx_in3,
        j as j_in4,
        -- Estimate max cantilever based on section
        CASE 
            WHEN sx < 10 THEN 10
            WHEN sx < 25 THEN 15
            WHEN sx < 50 THEN 20
            WHEN sx < 100 THEN 25
            ELSE 30
        END as max_cantilever_ft,
        -- Estimate cost multiplier
        CASE 
            WHEN type = 'HSS' AND is_astm_a1085 THEN 1.1
            WHEN type = 'HSS' THEN 1.0
            WHEN type = 'PIPE' THEN 0.95
            WHEN type = 'W' THEN 1.15
            ELSE 1.0
        END as cost_factor
    FROM aisc_shapes_v16
    WHERE type IN ('HSS', 'PIPE', 'W')
        AND sx >= 10  -- Min for cantilever signs
        AND w <= 100  -- Max practical weight
    ORDER BY sx;
    
    -- View for single pole signs
    CREATE OR REPLACE VIEW single_pole_sections AS
    SELECT 
        aisc_manual_label as designation,
        type,
        w as weight_plf,
        area as area_in2,
        ix as ix_in4,
        sx as sx_in3,
        rx as rx_in,
        -- Estimate max height based on rx
        CASE 
            WHEN rx < 2 THEN 20
            WHEN rx < 3 THEN 30
            WHEN rx < 4 THEN 40
            ELSE 50
        END as max_height_ft
    FROM aisc_shapes_v16
    WHERE type IN ('HSS', 'PIPE', 'W')
        AND rx >= 1.5  -- Min radius of gyration
    ORDER BY w;
    
    -- Combined view with aluminum options
    CREATE OR REPLACE VIEW all_sign_poles AS
    SELECT 
        designation,
        type,
        'STEEL' as material,
        weight_plf,
        area_in2,
        sx_in3,
        ix_in4
    FROM sign_pole_sections
    UNION ALL
    SELECT 
        designation,
        type,
        material,
        weight_plf,
        area_in2,
        sx_in3,
        ix_in4
    FROM custom_sign_sections
    WHERE type IN ('ALUMINUM', 'SQUARE_TUBE')
    ORDER BY material, weight_plf;
    """)
    
    logger.info("[OK] Created sign-specific views")


async def main():
    """Main import function"""
    
    logger.info("=" * 60)
    logger.info("AISC SHAPES DATABASE IMPORT FOR APEX")
    logger.info("=" * 60)
    
    # Check if files exist
    if not ENGINEERING_PATH.exists():
        logger.error(f"ERROR: Path not found: {ENGINEERING_PATH}")
        logger.info("Please ensure H:\\BOT TRAINING\\Engineering exists")
        return
    
    main_file = ENGINEERING_PATH / "aisc-shapes-database-v16.0.xlsx"
    if not main_file.exists():
        logger.error(f"ERROR: AISC database not found: {main_file}")
        return
    
    # Connect to database
    logger.info(f"\nConnecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Create tables
        await create_shapes_table(conn)
        
        # Import AISC data
        await import_aisc_data(conn)
        
        # Add custom sections
        await add_custom_sign_sections(conn)
        
        # Create cost tracking
        await create_material_cost_table(conn)
        
        # Create views
        await create_sign_specific_views(conn)
        
        # Verify import
        count = await conn.fetchval("SELECT COUNT(*) FROM aisc_shapes_v16")
        hss_count = await conn.fetchval("SELECT COUNT(*) FROM aisc_shapes_v16 WHERE type = 'HSS'")
        a1085_count = await conn.fetchval("SELECT COUNT(*) FROM aisc_shapes_v16 WHERE is_astm_a1085 = true")
        
        logger.info("\n" + "=" * 60)
        logger.info("IMPORT COMPLETE!")
        logger.info(f"Total shapes: {count}")
        logger.info(f"HSS shapes: {hss_count}")
        logger.info(f"A1085 HSS shapes: {a1085_count}")
        logger.info("=" * 60)
        
        # Example query
        logger.info("\nExample: Finding HSS for 20ft cantilever sign...")
        result = await conn.fetch("""
            SELECT designation, weight_plf, sx_in3, max_cantilever_ft
            FROM cantilever_pole_sections
            WHERE type = 'HSS' 
                AND max_cantilever_ft >= 20
            ORDER BY weight_plf
            LIMIT 5
        """)
        
        for row in result:
            logger.info(f"  {row['designation']}: {row['weight_plf']} lb/ft, Sx={row['sx_in3']} in³")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())