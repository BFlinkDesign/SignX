#!/usr/bin/env python
"""Fix monument function datatype mismatch"""

import asyncio
import asyncpg

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


async def fix_function():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("""
        CREATE OR REPLACE FUNCTION select_monument_pole(
            p_wind_moment_kipft FLOAT,
            p_height_ft FLOAT,
            p_max_diameter_in INTEGER DEFAULT 14,
            p_prefer_a1085 BOOLEAN DEFAULT FALSE
        )
        RETURNS TABLE (
            designation TEXT,
            type TEXT,
            diameter_in INTEGER,
            weight_plf FLOAT,
            moment_capacity_kipft FLOAT,
            stress_ratio FLOAT,
            slenderness_ratio FLOAT,
            cost_per_ft FLOAT,
            is_a1085 BOOLEAN,
            status TEXT
        )
        LANGUAGE plpgsql
        AS $func$
        DECLARE
            v_required_sx FLOAT;
            v_max_slenderness FLOAT := 200;
        BEGIN
            v_required_sx := p_wind_moment_kipft * 12 / (50 * 0.9);
            
            RETURN QUERY
            SELECT 
                s.aisc_manual_label::TEXT,
                s.type::TEXT,
                s.nominal_depth,
                s.w,
                s.sx * 50 * 0.9 / 12 as moment_cap,
                (p_wind_moment_kipft * 12) / (s.sx * 50 * 0.9) as stress_ratio,
                (p_height_ft * 12) / s.rx as slenderness,
                s.w * 0.90 as cost,
                s.is_astm_a1085,
                CASE 
                    WHEN (p_wind_moment_kipft * 12) / (s.sx * 50 * 0.9) > 1.0 THEN 'OVERSTRESSED'
                    WHEN (p_height_ft * 12) / s.rx > 200 THEN 'TOO_SLENDER'
                    WHEN (p_wind_moment_kipft * 12) / (s.sx * 50 * 0.9) > 0.9 THEN 'HIGH_STRESS'
                    ELSE 'OK'
                END::TEXT as status
            FROM aisc_shapes_v16 s
            WHERE s.type IN ('HSS', 'PIPE')
                AND s.nominal_depth <= p_max_diameter_in
                AND s.sx >= v_required_sx * 0.8
                AND s.rx >= (p_height_ft * 12) / v_max_slenderness * 0.9
                AND (NOT p_prefer_a1085 OR s.is_astm_a1085 = true)
                AND s.is_available = true
            ORDER BY 
                CASE WHEN p_prefer_a1085 AND s.is_astm_a1085 THEN 0 ELSE 1 END,
                (p_wind_moment_kipft * 12) / (s.sx * 50 * 0.9),
                s.w
            LIMIT 10;
        END;
        $func$;
        """)
        logger.info('Fixed function datatype')
        
        # Test the function
        results = await conn.fetch("""
            SELECT designation, diameter_in, stress_ratio, status
            FROM select_monument_pole(150, 25, 12, false)
            LIMIT 5
        """)
        
        logger.info(f'\nSections for 150 kip-ft moment, 25ft height:')
        for r in results:
            logger.info(f'  {r[0]:15s} D={r[1]:2d}" Ratio={r[2]:.3f} {r[3]}')
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_function())