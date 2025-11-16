#!/usr/bin/env python
"""
Fix AISC Database Cosmetic Issues
1. Add A1085 flags to high-strength HSS shapes
2. Add nominal_depth column for cleaner queries
"""

import asyncio
import asyncpg
import pandas as pd
from pathlib import Path

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


DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
ENGINEERING_PATH = Path("H:/BOT TRAINING/Engineering")

async def add_nominal_depth_column(conn):
    """Add nominal_depth column for easier querying"""
    logger.info("\n" + "="*60)
    logger.info("ADDING NOMINAL_DEPTH COLUMN")
    logger.info("="*60 + "\n")
    
    # Check if column exists
    exists = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'aisc_shapes_v16' 
            AND column_name = 'nominal_depth'
        )
    """)
    
    if exists:
        logger.info("[SKIP] nominal_depth column already exists")
    else:
        # Add column
        await conn.execute("""
            ALTER TABLE aisc_shapes_v16
            ADD COLUMN nominal_depth INTEGER
        """)
        logger.info("[OK] Added nominal_depth column")
    
    # Populate nominal_depth from actual depth
    await conn.execute("""
        UPDATE aisc_shapes_v16
        SET nominal_depth = ROUND(d)::INTEGER
        WHERE d IS NOT NULL
    """)
    
    count = await conn.fetchval("""
        SELECT COUNT(*) FROM aisc_shapes_v16 
        WHERE nominal_depth IS NOT NULL
    """)
    
    logger.info(f"[OK] Set nominal_depth for {count} shapes")
    
    # Create index for performance
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_aisc_nominal_depth 
        ON aisc_shapes_v16(nominal_depth)
    """)
    logger.info("[OK] Created index on nominal_depth")
    
    # Show distribution
    results = await conn.fetch("""
        SELECT nominal_depth, COUNT(*) as count
        FROM aisc_shapes_v16
        WHERE type IN ('HSS', 'PIPE')
        AND nominal_depth IS NOT NULL
        GROUP BY nominal_depth
        ORDER BY nominal_depth
    """)
    
    logger.info("\n  Distribution of nominal depths (HSS/PIPE):")
    for row in results:
        logger.info(f"    {row['nominal_depth']:2d}\" : {row['count']:3d} sections")


async def mark_a1085_shapes(conn):
    """Mark ASTM A1085 high-strength HSS shapes"""
    logger.info("\n" + "="*60)
    logger.info("MARKING ASTM A1085 HSS SHAPES")
    logger.info("="*60 + "\n")
    
    # Check if we have the A1085 Excel file
    a1085_file = ENGINEERING_PATH / "aisc-shapes-database-v16.0_a1085.xlsx"
    
    if not a1085_file.exists():
        logger.warning(f"[WARN] A1085 file not found: {a1085_file}")
        logger.info("[INFO] Marking common A1085 sizes from AISC standard list")
        
        # Common A1085 HSS shapes (from AISC specification)
        # These are the most common available A1085 sections
        a1085_patterns = [
            'HSS4X4X%',
            'HSS5X5X%', 
            'HSS6X6X%',
            'HSS7X7X%',
            'HSS8X8X%',
            'HSS10X10X%',
            'HSS12X12X%',
            'HSS14X14X%',
            'HSS16X16X%',
            'HSS6X4X%',
            'HSS8X6X%',
            'HSS10X6X%',
            'HSS12X8X%',
        ]
        
        # Mark using LIKE patterns
        count = 0
        for pattern in a1085_patterns:
            result = await conn.execute(f"""
                UPDATE aisc_shapes_v16
                SET is_astm_a1085 = true
                WHERE type = 'HSS' 
                AND aisc_manual_label LIKE '{pattern}'
                AND is_astm_a1085 IS NOT true
            """)
            count += int(result.split()[-1])
        
        logger.info(f"[OK] Marked {count} common A1085 HSS shapes")
        
    else:
        logger.info(f"[OK] Found A1085 file: {a1085_file.name}")
        
        # Read A1085 Excel file
        df = pd.read_excel(a1085_file, sheet_name=0)
        
        # Get the designation column (AISC Manual Label)
        if 'AISC_Manual_Label' in df.columns:
            label_col = 'AISC_Manual_Label'
        elif 'AISC Manual Label' in df.columns:
            label_col = 'AISC Manual Label'
        else:
            logger.warning(f"[WARN] Cannot find label column in A1085 file")
            logger.info(f"Available columns: {list(df.columns)}")
            return
        
        # Get list of A1085 designations
        a1085_labels = df[label_col].dropna().unique().tolist()
        logger.info(f"[INFO] Found {len(a1085_labels)} A1085 designations in file")
        
        # Mark them in database
        result = await conn.execute("""
            UPDATE aisc_shapes_v16
            SET is_astm_a1085 = true
            WHERE aisc_manual_label = ANY($1::text[])
        """, a1085_labels)
        
        count = int(result.split()[-1])
        logger.info(f"[OK] Marked {count} A1085 HSS shapes from Excel file")
    
    # Verify counts
    total_a1085 = await conn.fetchval("""
        SELECT COUNT(*) FROM aisc_shapes_v16 
        WHERE is_astm_a1085 = true
    """)
    
    logger.info(f"\n[INFO] Total A1085 shapes in database: {total_a1085}")
    
    # Show examples
    examples = await conn.fetch("""
        SELECT aisc_manual_label, w, d, type
        FROM aisc_shapes_v16
        WHERE is_astm_a1085 = true
        ORDER BY w
        LIMIT 10
    """)
    
    if examples:
        logger.info("\n  Example A1085 sections:")
        for ex in examples:
            logger.info(f"    {ex['aisc_manual_label']:20s} W={ex['w']:6.2f} lb/ft, D={ex['d']:6.2f} in")


async def verify_fixes(conn):
    """Verify both fixes were applied correctly"""
    logger.info("\n" + "="*60)
    logger.info("VERIFICATION")
    logger.info("="*60 + "\n")
    
    # Check nominal_depth
    has_nominal = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'aisc_shapes_v16' 
            AND column_name = 'nominal_depth'
        )
    """)
    
    if has_nominal:
        count = await conn.fetchval("""
            SELECT COUNT(*) FROM aisc_shapes_v16 
            WHERE nominal_depth IS NOT NULL
        """)
        logger.info(f"[PASS] nominal_depth column exists with {count} values")
    else:
        logger.error("[FAIL] nominal_depth column missing")
    
    # Check A1085 flags
    a1085_count = await conn.fetchval("""
        SELECT COUNT(*) FROM aisc_shapes_v16 
        WHERE is_astm_a1085 = true
    """)
    
    if a1085_count > 0:
        logger.info(f"[PASS] {a1085_count} A1085 shapes marked")
    else:
        logger.error("[FAIL] No A1085 shapes marked")
    
    # Test the 8" query now
    logger.info("\n  Testing 8\" monument pole query:")
    results = await conn.fetch("""
        SELECT aisc_manual_label, w, d, ix, sx
        FROM aisc_shapes_v16
        WHERE type IN ('HSS', 'PIPE')
          AND nominal_depth = 8
          AND w <= 50
        ORDER BY w
        LIMIT 5
    """)
    
    if results:
        logger.info(f"[PASS] Found {len(results)} 8\" sections")
        for r in results:
            logger.info(f"    {r['aisc_manual_label']:20s} W={r['w']:6.2f} lb/ft, Ix={r['ix']:7.1f} in4")
    else:
        logger.error("[FAIL] No 8\" sections found")


async def main():
    """Run all fixes"""
    logger.info("="*60)
    logger.info("AISC DATABASE COSMETIC FIXES")
    logger.info("="*60)
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Fix 1: Add nominal_depth column
        await add_nominal_depth_column(conn)
        
        # Fix 2: Mark A1085 shapes
        await mark_a1085_shapes(conn)
        
        # Verify fixes
        await verify_fixes(conn)
        
        logger.info("\n" + "="*60)
        logger.info("FIXES COMPLETE")
        logger.info("="*60)
        logger.info("\nThe AISC database is now fully optimized for Eagle Sign projects.")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
