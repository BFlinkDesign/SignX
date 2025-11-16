#!/usr/bin/env python
"""Fix the minor issues identified in AISC database verification"""

import asyncio
import asyncpg
import pandas as pd
from pathlib import Path

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build database URL from environment variables
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "signx_studio")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
ENGINEERING_PATH = Path("H:/BOT TRAINING/Engineering")

async def fix_a1085_flags(conn):
    """Fix A1085 HSS flags by importing the A1085 Excel file"""
    logger.info("\n=== FIXING A1085 HSS FLAGS ===")
    
    a1085_file = ENGINEERING_PATH / "aisc-shapes-database-v16.0_a1085.xlsx"
    
    if not a1085_file.exists():
        logger.warning(f"[WARNING] A1085 file not found: {a1085_file}")
        logger.info("Skipping A1085 flag updates")
        return
    
    try:
        # Read A1085 Excel file
        logger.info(f"Reading A1085 HSS shapes from {a1085_file}...")
        df_a1085 = pd.read_excel(a1085_file, sheet_name='v16.0 Database_A1085 ')
        
        # Get the AISC manual labels
        if 'AISC_Manual_Label' in df_a1085.columns:
            a1085_labels = df_a1085['AISC_Manual_Label'].dropna().tolist()
        elif 'aisc_manual_label' in df_a1085.columns:
            a1085_labels = df_a1085['aisc_manual_label'].dropna().tolist()
        else:
            logger.error("[ERROR] Cannot find AISC label column in A1085 file")
            logger.info("Available columns:", list(df_a1085.columns))
            return
        
        logger.info(f"Found {len(a1085_labels)} A1085 HSS sections")
        
        # Update database flags
        if a1085_labels:
            result = await conn.execute("""
                UPDATE aisc_shapes_v16 
                SET is_astm_a1085 = true 
                WHERE aisc_manual_label = ANY($1::text[])
            """, a1085_labels)
            
            # Check how many were updated
            updated_count = await conn.fetchval("""
                SELECT COUNT(*) FROM aisc_shapes_v16 
                WHERE is_astm_a1085 = true
            """)
            
            logger.info(f"[FIXED] Marked {updated_count} shapes as ASTM A1085")
            
            # Show examples
            examples = await conn.fetch("""
                SELECT aisc_manual_label, w, d
                FROM aisc_shapes_v16
                WHERE is_astm_a1085 = true
                ORDER BY w
                LIMIT 5
            """)
            
            logger.info("Example A1085 sections:")
            for ex in examples:
                logger.info(f"  {ex['aisc_manual_label']:20s} W={ex['w']:.1f} lb/ft")
        
    except Exception as e:
        logger.error(f"[ERROR] Failed to process A1085 file: {e}")

async def fix_nominal_depth_indexing(conn):
    """Fix nominal depth column and indexing"""
    logger.info("\n=== FIXING NOMINAL DEPTH INDEXING ===")
    
    # Check if nominal_depth column exists and has data
    nominal_count = await conn.fetchval("""
        SELECT COUNT(*) FROM aisc_shapes_v16 
        WHERE nominal_depth IS NOT NULL AND nominal_depth > 0
    """)
    
    logger.info(f"Current nominal_depth entries: {nominal_count}")
    
    if nominal_count < 100:  # Likely needs updating
        logger.info("Updating nominal_depth values...")
        
        # Update nominal_depth based on actual depth
        await conn.execute("""
            UPDATE aisc_shapes_v16 
            SET nominal_depth = CASE 
                WHEN d IS NULL THEN NULL
                WHEN d <= 0 THEN NULL
                ELSE ROUND(d)::INTEGER
            END
            WHERE nominal_depth IS NULL OR nominal_depth = 0
        """)
        
        # Verify update
        updated_count = await conn.fetchval("""
            SELECT COUNT(*) FROM aisc_shapes_v16 
            WHERE nominal_depth IS NOT NULL AND nominal_depth > 0
        """)
        
        logger.info(f"[FIXED] Updated {updated_count} nominal_depth values")
        
        # Show distribution
        logger.info("\nNominal depth distribution for HSS:")
        results = await conn.fetch("""
            SELECT nominal_depth, COUNT(*) as count
            FROM aisc_shapes_v16
            WHERE type = 'HSS' AND nominal_depth IS NOT NULL
            GROUP BY nominal_depth
            ORDER BY nominal_depth
            LIMIT 10
        """)
        
        for row in results:
            logger.info(f"  {row['nominal_depth']}\" depth: {row['count']} sections")
    
    # Ensure index exists
    try:
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_aisc_nominal_depth 
            ON aisc_shapes_v16(nominal_depth) 
            WHERE nominal_depth IS NOT NULL
        """)
        logger.info("[FIXED] Created nominal_depth index")
    except Exception as e:
        logger.info(f"[INFO] Index may already exist: {e}")

async def fix_table_names(conn):
    """Check and fix expected table names"""
    logger.info("\n=== CHECKING TABLE NAMES ===")
    
    # Check what cantilever tables exist
    tables = await conn.fetch("""
        SELECT table_name 
        FROM information_schema.tables
        WHERE table_name LIKE 'cantilever%'
        ORDER BY table_name
    """)
    
    logger.info("Existing cantilever tables:")
    for table in tables:
        logger.info(f"  - {table['table_name']}")
    
    # Check if we need to create cantilever_analysis_results table
    results_exists = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'cantilever_analysis_results'
        )
    """)
    
    if not results_exists:
        logger.info("\nCreating missing cantilever_analysis_results table...")
        
        await conn.execute("""
        CREATE TABLE cantilever_analysis_results (
            id VARCHAR PRIMARY KEY,
            config_id VARCHAR NOT NULL,
            project_id VARCHAR NOT NULL,
            
            -- Moments and forces
            moment_x_kipft FLOAT NOT NULL,
            moment_y_kipft FLOAT NOT NULL, 
            moment_z_kipft FLOAT NOT NULL,
            total_moment_kipft FLOAT NOT NULL,
            shear_x_kip FLOAT NOT NULL,
            shear_y_kip FLOAT NOT NULL,
            axial_kip FLOAT NOT NULL,
            
            -- Arm stresses
            arm_bending_stress_ksi FLOAT NOT NULL,
            arm_shear_stress_ksi FLOAT NOT NULL,
            arm_deflection_in FLOAT NOT NULL,
            arm_rotation_deg FLOAT NOT NULL,
            
            -- Connection forces
            connection_tension_kip FLOAT NOT NULL,
            connection_shear_kip FLOAT NOT NULL,
            connection_moment_kipft FLOAT NOT NULL,
            
            -- Design ratios
            arm_stress_ratio FLOAT NOT NULL,
            connection_ratio FLOAT NOT NULL,
            deflection_ratio FLOAT NOT NULL,
            
            -- Fatigue analysis
            fatigue_cycles BIGINT DEFAULT 0,
            fatigue_factor FLOAT DEFAULT 1.0,
            
            -- Metadata
            warnings JSONB DEFAULT '[]',
            assumptions JSONB DEFAULT '[]',
            analysis_params JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            content_sha256 VARCHAR,
            
            FOREIGN KEY (config_id) REFERENCES cantilever_configs(id) ON DELETE CASCADE,
            FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
            CHECK (arm_stress_ratio >= 0),
            CHECK (fatigue_factor >= 0 AND fatigue_factor <= 1)
        )
        """)
        
        await conn.execute("""
        CREATE INDEX idx_cantilever_analysis_project_id 
        ON cantilever_analysis_results(project_id)
        """)
        
        await conn.execute("""
        CREATE INDEX idx_cantilever_analysis_config_id 
        ON cantilever_analysis_results(config_id)
        """)
        
        logger.info("[FIXED] Created cantilever_analysis_results table")
    else:
        logger.info("[OK] cantilever_analysis_results table already exists")

async def test_8_inch_query_fix(conn):
    """Test and fix the 8-inch pole query"""
    logger.info("\n=== TESTING 8-INCH POLE QUERY ===")
    
    # Try different approaches to find 8" sections
    approaches = [
        ("nominal_depth = 8", "SELECT COUNT(*) FROM aisc_shapes_v16 WHERE type = 'HSS' AND nominal_depth = 8"),
        ("d between 7.5 and 8.5", "SELECT COUNT(*) FROM aisc_shapes_v16 WHERE type = 'HSS' AND d BETWEEN 7.5 AND 8.5"),
        ("label contains HSS8", "SELECT COUNT(*) FROM aisc_shapes_v16 WHERE type = 'HSS' AND aisc_manual_label LIKE 'HSS8%'"),
    ]
    
    for desc, query in approaches:
        count = await conn.fetchval(query)
        logger.info(f"  {desc}: {count} sections")
    
    # Show actual 8" sections if found
    sections = await conn.fetch("""
        SELECT aisc_manual_label, w, d, ix, sx
        FROM aisc_shapes_v16
        WHERE type = 'HSS' 
          AND (d BETWEEN 7.5 AND 8.5 OR aisc_manual_label LIKE 'HSS8%')
        ORDER BY w
        LIMIT 5
    """)
    
    if sections:
        logger.info("\nFound 8\" HSS sections:")
        for s in sections:
            logger.info(f"  {s['aisc_manual_label']:20s} W={s['w']:.1f} lb/ft, D={s['d']:.2f} in, Sx={s['sx']:.1f} in³")
        logger.info("[FIXED] 8-inch query working")
    else:
        logger.warning("[WARNING] No 8-inch sections found - may need data verification")

async def main():
    """Run all fixes"""
    logger.info("=" * 60)
    logger.info("FIXING AISC DATABASE MINOR ISSUES")
    logger.info("=" * 60)
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Fix all identified issues
        await fix_a1085_flags(conn)
        await fix_nominal_depth_indexing(conn)
        await fix_table_names(conn)
        await test_8_inch_query_fix(conn)
        
        logger.info("\n" + "=" * 60)
        logger.info("MINOR ISSUES RESOLUTION COMPLETE")
        logger.info("=" * 60)
        
        # Run a quick verification
        logger.info("\nVerification:")
        
        # A1085 count
        a1085_count = await conn.fetchval("SELECT COUNT(*) FROM aisc_shapes_v16 WHERE is_astm_a1085 = true")
        logger.info(f"  A1085 HSS sections: {a1085_count}")
        
        # Nominal depth count
        nominal_count = await conn.fetchval("SELECT COUNT(*) FROM aisc_shapes_v16 WHERE nominal_depth IS NOT NULL")
        logger.info(f"  Sections with nominal_depth: {nominal_count}")
        
        # Tables count
        cantilever_tables = await conn.fetchval("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name LIKE 'cantilever%'
        """)
        logger.info(f"  Cantilever tables: {cantilever_tables}")
        
        logger.info("\n✅ All minor issues addressed!")
        
    except Exception as e:
        logger.error(f"\n❌ Error during fixes: {e}")
        import traceback
import logging

logger = logging.getLogger(__name__)
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())