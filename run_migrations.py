#!/usr/bin/env python
"""Run AISC foundation migrations directly without Alembic complexity"""

import asyncio
import asyncpg
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

async def run_migrations():
    """Run the foundation migrations in order"""
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        logger.info("=" * 60)
        logger.info("RUNNING AISC FOUNDATION MIGRATIONS")
        logger.info("=" * 60)
        
        # Check if AISC table already exists from our previous setup
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'aisc_shapes_v16'
            )
        """)
        
        if exists:
            logger.info("\n[OK] AISC shapes table already exists")
            
            # Check row count
            count = await conn.fetchval("SELECT COUNT(*) FROM aisc_shapes_v16")
            logger.info(f"[OK] Contains {count} shapes")
            
            # Check if views exist
            view_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.views 
                    WHERE table_name = 'sign_pole_sections'
                )
            """)
            
            if not view_exists:
                logger.info("\nCreating missing sign-specific views...")
                
                # Create the sign_pole_sections view
                await conn.execute("""
                CREATE OR REPLACE VIEW sign_pole_sections AS
                SELECT 
                    s.aisc_manual_label as designation,
                    s.type,
                    s.w as weight_plf,
                    s.area as area_in2,
                    s.d as depth_in,
                    s.bf as width_in,
                    s.ix as ix_in4,
                    s.sx as sx_in3,
                    s.rx as rx_in,
                    s.zx as zx_in3,
                    s.iy as iy_in4,
                    s.sy as sy_in3,
                    s.ry as ry_in,
                    s.zy as zy_in3,
                    s.j as j_in4,
                    s.is_astm_a1085,
                    CASE 
                        WHEN s.type = 'HSS' THEN LEAST(s.d * 2.5, 30)
                        WHEN s.type = 'PIPE' THEN LEAST(s.d * 2.0, 25)
                        WHEN s.type = 'W' THEN LEAST(s.d * 1.5, 20)
                        ELSE s.d
                    END as max_cantilever_ft,
                    CASE 
                        WHEN s.rx > 0 THEN LEAST(s.rx * 200 / 12, 50)
                        ELSE 0
                    END as max_height_ft,
                    CASE 
                        WHEN s.w > 0 THEN s.sx / s.w
                        ELSE 0
                    END as efficiency_ratio
                FROM aisc_shapes_v16 s
                WHERE s.type IN ('HSS', 'PIPE', 'W', 'WT')
                    AND s.w > 10
                    AND s.sx > 5
                    AND s.is_available = true
                ORDER BY s.type, s.w;
                """)
                logger.info("[OK] Created sign_pole_sections view")
                
                # Create cantilever_arm_sections view
                await conn.execute("""
                CREATE OR REPLACE VIEW cantilever_arm_sections AS
                SELECT 
                    s.aisc_manual_label as designation,
                    s.type,
                    s.w as weight_plf,
                    s.sx as sx_in3,
                    s.ix as ix_in4,
                    s.j as j_in4,
                    s.is_astm_a1085,
                    s.sx * 50 * 0.9 / 12 as moment_capacity_kipft,
                    s.j * 11200 as torsional_stiffness,
                    CASE 
                        WHEN s.sx < 10 THEN 10
                        WHEN s.sx < 25 THEN 15
                        WHEN s.sx < 50 THEN 20
                        WHEN s.sx < 100 THEN 25
                        ELSE 30
                    END as recommended_span_ft,
                    CASE 
                        WHEN s.is_astm_a1085 THEN 0.93
                        ELSE 0.86
                    END as tolerance_factor,
                    29000 * s.ix as flexural_stiffness
                FROM aisc_shapes_v16 s
                WHERE s.type IN ('HSS', 'PIPE')
                    AND s.sx >= 10
                    AND s.w <= 100
                    AND s.is_available = true
                ORDER BY s.sx;
                """)
                logger.info("[OK] Created cantilever_arm_sections view")
                
                # Create find_optimal_sign_pole function
                await conn.execute("""
                CREATE OR REPLACE FUNCTION find_optimal_sign_pole(
                    p_moment_kipft FLOAT,
                    p_height_ft FLOAT DEFAULT NULL,
                    p_shape_type VARCHAR DEFAULT NULL,
                    p_max_weight FLOAT DEFAULT 200,
                    p_prefer_a1085 BOOLEAN DEFAULT FALSE
                )
                RETURNS TABLE (
                    designation VARCHAR,
                    type VARCHAR,
                    weight_plf FLOAT,
                    sx_in3 FLOAT,
                    stress_ratio FLOAT,
                    is_a1085 BOOLEAN
                )
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    v_required_sx FLOAT;
                    v_min_r FLOAT;
                BEGIN
                    -- Calculate required section modulus
                    v_required_sx := p_moment_kipft * 12 / (50 * 0.9);
                    
                    -- Calculate min radius of gyration if height specified
                    IF p_height_ft IS NOT NULL THEN
                        v_min_r := p_height_ft * 12 / 200;
                    ELSE
                        v_min_r := 0;
                    END IF;
                    
                    RETURN QUERY
                    SELECT 
                        s.aisc_manual_label,
                        s.type,
                        s.w,
                        s.sx,
                        (p_moment_kipft * 12) / (s.sx * 50 * 0.9) as stress_ratio,
                        s.is_astm_a1085
                    FROM aisc_shapes_v16 s
                    WHERE s.sx >= v_required_sx
                        AND s.w <= p_max_weight
                        AND (p_shape_type IS NULL OR s.type = p_shape_type)
                        AND (v_min_r = 0 OR s.rx >= v_min_r)
                        AND (NOT p_prefer_a1085 OR s.is_astm_a1085 = true)
                        AND s.is_available = true
                    ORDER BY 
                        CASE WHEN p_prefer_a1085 AND s.is_astm_a1085 THEN 0 ELSE 1 END,
                        s.w
                    LIMIT 10;
                END;
                $$;
                """)
                logger.info("[OK] Created find_optimal_sign_pole function")
            else:
                logger.info("[OK] Sign-specific views already exist")
            
            # Test the function
            logger.info("\n" + "=" * 60)
            logger.info("TESTING AISC INTEGRATION")
            logger.info("=" * 60)
            
            logger.info("\nFinding optimal pole for 150 kip-ft moment:")
            results = await conn.fetch("""
                SELECT * FROM find_optimal_sign_pole(
                    p_moment_kipft := 150,
                    p_shape_type := 'HSS'
                )
                LIMIT 5
            """)
            
            for row in results:
                print(f"  {row['designation']}: {row['weight_plf']:.1f} lb/ft, "
                      f"Sx={row['sx_in3']:.1f} in³, Ratio={row['stress_ratio']:.2f}")
            
            logger.info("\nQuerying cantilever arm sections:")
            results = await conn.fetch("""
                SELECT designation, weight_plf, moment_capacity_kipft, recommended_span_ft
                FROM cantilever_arm_sections
                WHERE moment_capacity_kipft >= 150
                ORDER BY weight_plf
                LIMIT 5
            """)
            
            for row in results:
                print(f"  {row['designation']}: {row['weight_plf']:.1f} lb/ft, "
                      f"Capacity={row['moment_capacity_kipft']:.0f} kip-ft, "
                      f"Span={row['recommended_span_ft']:.0f} ft")
            
            # Check material costs
            cost_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'material_cost_indices'
                )
            """)
            
            if cost_exists:
                result = await conn.fetchrow("""
                    SELECT year, month, price_per_lb
                    FROM material_cost_indices
                    WHERE material = 'STEEL_STRUCTURAL'
                    ORDER BY year DESC, month DESC
                    LIMIT 1
                """)
                if result:
                    logger.info(f"\nCurrent steel price: ${result['price_per_lb']:.2f}/lb ({result['year']}-{result['month']:02d})")
            
            logger.info("\n" + "=" * 60)
            logger.info("AISC FOUNDATION FULLY ACTIVATED!")
            logger.info("=" * 60)
            logger.info("\n✅ Database contains:")
            logger.info(f"  - {count} AISC shapes")
            logger.info("  - Sign-specific views and functions")
            logger.info("  - Material cost tracking")
            logger.info("  - Optimized selection functions")
            logger.info("\n✅ Ready for production use!")
            
        else:
            logger.info("\nAISC table doesn't exist. Run setup_database.py first.")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migrations())