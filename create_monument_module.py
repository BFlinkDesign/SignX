#!/usr/bin/env python
"""
Create Monument Pole Tables for SIGN X Studio
Direct SQL approach - bypasses Alembic issues
"""

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

async def create_monument_tables():
    """Create monument pole calculation tables"""
    logger.info("="*60)
    logger.info("CREATING MONUMENT POLE MODULE")
    logger.info("="*60 + "\n")
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Create ENUM types
        logger.info("[INFO] Creating ENUM types...")
        await conn.execute("""
            DO $$ BEGIN
                CREATE TYPE exposure_category AS ENUM ('B', 'C', 'D');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        
        await conn.execute("""
            DO $$ BEGIN
                CREATE TYPE risk_category AS ENUM ('I', 'II', 'III', 'IV');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        
        await conn.execute("""
            DO $$ BEGIN
                CREATE TYPE foundation_type AS ENUM (
                    'drilled_shaft',
                    'spread_footing',
                    'concrete_pier',
                    'helical_anchor'
                );
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        logger.info("[OK] ENUM types created\n")
        
        # Monument Configs table
        logger.info("[INFO] Creating monument_configs table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS monument_configs (
                id VARCHAR(255) PRIMARY KEY,
                project_id VARCHAR(255) NOT NULL,
                config_name VARCHAR(255),
                
                -- Sign Geometry
                pole_height_ft FLOAT NOT NULL,
                sign_area_sqft FLOAT NOT NULL,
                sign_width_ft FLOAT NOT NULL,
                sign_height_ft FLOAT NOT NULL,
                sign_clearance_ft FLOAT NOT NULL,
                sign_thickness_in FLOAT,
                
                -- Wind Parameters (ASCE 7-22)
                wind_speed_mph FLOAT NOT NULL,
                exposure_category exposure_category NOT NULL,
                risk_category risk_category NOT NULL DEFAULT 'II',
                topographic_factor FLOAT NOT NULL DEFAULT 1.0,
                gust_factor FLOAT NOT NULL DEFAULT 0.85,
                importance_factor FLOAT NOT NULL DEFAULT 1.0,
                
                -- Pole Selection (References AISC)
                pole_section VARCHAR(50) NOT NULL REFERENCES aisc_shapes_v16(aisc_manual_label) ON DELETE RESTRICT,
                pole_material VARCHAR(20) NOT NULL DEFAULT 'A500',
                pole_yield_stress_ksi FLOAT NOT NULL DEFAULT 50,
                pole_embedment_ft FLOAT NOT NULL,
                
                -- Base Plate
                base_plate_width_in FLOAT,
                base_plate_length_in FLOAT,
                base_plate_thickness_in FLOAT,
                anchor_bolt_diameter_in FLOAT,
                anchor_bolt_count INTEGER,
                anchor_bolt_circle_dia_in FLOAT,
                
                -- Foundation
                foundation_type foundation_type,
                foundation_diameter_in FLOAT,
                foundation_depth_ft FLOAT,
                soil_bearing_capacity_psf FLOAT,
                soil_passive_pressure_pcf FLOAT,
                
                -- Metadata
                notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                
                -- Constraints
                CONSTRAINT ck_monument_pole_height CHECK (pole_height_ft > 0 AND pole_height_ft <= 30),
                CONSTRAINT ck_monument_sign_area CHECK (sign_area_sqft > 0 AND sign_area_sqft <= 500),
                CONSTRAINT ck_monument_wind_speed CHECK (wind_speed_mph >= 85 AND wind_speed_mph <= 200),
                CONSTRAINT ck_monument_embedment CHECK (pole_embedment_ft >= 3 AND pole_embedment_ft <= 12),
                CONSTRAINT ck_monument_yield_stress CHECK (pole_yield_stress_ksi >= 36 AND pole_yield_stress_ksi <= 70)
            )
        """)
        logger.info("[OK] monument_configs table created\n")
        
        # Monument Results table
        logger.info("[INFO] Creating monument_results table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS monument_results (
                id VARCHAR(255) PRIMARY KEY,
                config_id VARCHAR(255) NOT NULL REFERENCES monument_configs(id) ON DELETE CASCADE,
                project_id VARCHAR(255) NOT NULL,
                
                -- Wind Load Analysis
                wind_pressure_psf FLOAT NOT NULL,
                design_wind_force_lbs FLOAT NOT NULL,
                wind_moment_arm_ft FLOAT NOT NULL,
                
                -- Pole Structural Analysis
                moment_at_base_kipft FLOAT NOT NULL,
                shear_at_base_kip FLOAT NOT NULL,
                axial_load_kip FLOAT NOT NULL,
                torsion_kipft FLOAT NOT NULL DEFAULT 0,
                
                -- Stress Analysis
                bending_stress_ksi FLOAT NOT NULL,
                allowable_bending_ksi FLOAT NOT NULL,
                stress_ratio FLOAT NOT NULL,
                shear_stress_ksi FLOAT,
                combined_stress_ratio FLOAT,
                
                -- Deflection
                tip_deflection_in FLOAT NOT NULL,
                deflection_ratio FLOAT NOT NULL,
                max_deflection_limit_in FLOAT NOT NULL,
                
                -- Foundation
                overturning_moment_kipft FLOAT NOT NULL,
                resisting_moment_kipft FLOAT NOT NULL,
                overturning_safety_factor FLOAT NOT NULL,
                soil_bearing_pressure_psf FLOAT,
                bearing_safety_factor FLOAT,
                
                -- Base Plate
                base_plate_bending_stress_ksi FLOAT,
                anchor_bolt_tension_kip FLOAT,
                anchor_bolt_utilization FLOAT,
                
                -- Code Compliance
                passes_strength BOOLEAN NOT NULL,
                passes_deflection BOOLEAN NOT NULL,
                passes_overturning BOOLEAN NOT NULL,
                passes_bearing BOOLEAN NOT NULL,
                passes_all_checks BOOLEAN NOT NULL,
                
                -- Fatigue
                fatigue_cycles INTEGER,
                fatigue_stress_range_ksi FLOAT,
                fatigue_category VARCHAR(10),
                
                -- Metadata
                analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                analysis_version VARCHAR(20),
                warnings JSON,
                
                CONSTRAINT ck_monument_stress_positive CHECK (stress_ratio >= 0),
                CONSTRAINT ck_monument_overturning_positive CHECK (overturning_safety_factor >= 0)
            )
        """)
        logger.info("[OK] monument_results table created\n")
        
        # Create indexes
        logger.info("[INFO] Creating indexes...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_monument_configs_project ON monument_configs(project_id);
            CREATE INDEX IF NOT EXISTS idx_monument_configs_pole ON monument_configs(pole_section);
            CREATE INDEX IF NOT EXISTS idx_monument_results_config ON monument_results(config_id);
            CREATE INDEX IF NOT EXISTS idx_monument_results_project ON monument_results(project_id);
            CREATE INDEX IF NOT EXISTS idx_monument_results_passes ON monument_results(passes_all_checks);
        """)
        logger.info("[OK] Indexes created\n")
        
        # Create helper view for monument pole selection
        logger.info("[INFO] Creating monument_pole_sections view...")
        await conn.execute("""
            CREATE OR REPLACE VIEW monument_pole_sections AS
            SELECT 
                aisc_manual_label,
                type,
                w as weight_plf,
                area as area_in2,
                d as depth_in,
                nominal_depth,
                tw as wall_thickness_in,
                ix as ix_in4,
                sx as sx_in3,
                rx as rx_in,
                zx as zx_in3,
                is_astm_a1085,
                (w * 0.90) as material_cost_per_ft
            FROM aisc_shapes_v16
            WHERE type IN ('HSS', 'PIPE')
              AND nominal_depth >= 6
              AND nominal_depth <= 16
              AND w <= 100
            ORDER BY type, nominal_depth, w
        """)
        logger.info("[OK] monument_pole_sections view created\n")
        
        # Create wind pressure calculation function
        logger.info("[INFO] Creating wind pressure function...")
        await conn.execute("""
            CREATE OR REPLACE FUNCTION calculate_wind_pressure(
                p_wind_speed_mph FLOAT,
                p_exposure exposure_category,
                p_risk_category risk_category DEFAULT 'II',
                p_height_ft FLOAT DEFAULT 20
            ) RETURNS FLOAT AS $$
            DECLARE
                v_velocity_pressure FLOAT;
                v_exposure_coeff FLOAT;
                v_importance_factor FLOAT;
                v_design_pressure FLOAT;
            BEGIN
                -- Velocity pressure: qz = 0.00256 * Kz * Kzt * Kd * V^2 (psf)
                -- Simplified for typical cases
                
                -- Exposure coefficient (varies with height and exposure)
                v_exposure_coeff := CASE p_exposure
                    WHEN 'B' THEN 0.7   -- Suburban
                    WHEN 'C' THEN 0.85  -- Open terrain (typical)
                    WHEN 'D' THEN 1.0   -- Flat/coastal
                END;
                
                -- Importance factor based on risk category
                v_importance_factor := CASE p_risk_category
                    WHEN 'I' THEN 0.87
                    WHEN 'II' THEN 1.0
                    WHEN 'III' THEN 1.15
                    WHEN 'IV' THEN 1.15
                END;
                
                -- Velocity pressure
                v_velocity_pressure := 0.00256 * v_exposure_coeff * POWER(p_wind_speed_mph, 2);
                
                -- Design pressure (includes gust factor, shape factor for signs ≈ 1.8)
                v_design_pressure := v_velocity_pressure * v_importance_factor * 1.8;
                
                RETURN v_design_pressure;
            END;
            $$ LANGUAGE plpgsql IMMUTABLE;
        """)
        logger.info("[OK] Wind pressure function created\n")
        
        logger.info("="*60)
        logger.info("MONUMENT POLE MODULE COMPLETE")
        logger.info("="*60)
        logger.info("\n[SUCCESS] Monument pole tables and functions created")
        logger.info("\nNext steps:")
        logger.info("  1. Test monument pole queries")
        logger.info("  2. Create monument pole calculation engine")
        logger.info("  3. Integrate with Eagle Sign projects")
        
    finally:
        await conn.close()


async def test_monument_module():
    """Test monument pole module functionality"""
    logger.info("\n" + "="*60)
    logger.info("TESTING MONUMENT POLE MODULE")
    logger.info("="*60 + "\n")
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Test 1: Check tables exist
        logger.info("[TEST 1] Checking tables...")
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name LIKE 'monument%'
            ORDER BY table_name
        """)
        for table in tables:
            logger.info(f"  [OK] {table['table_name']}")
        
        # Test 2: Query monument pole sections
        logger.info("\n[TEST 2] Monument pole selection (8\" diameter)...")
        sections = await conn.fetch("""
            SELECT aisc_manual_label, weight_plf, ix_in4, material_cost_per_ft
            FROM monument_pole_sections
            WHERE nominal_depth = 8
            ORDER BY weight_plf
            LIMIT 5
        """)
        
        if sections:
            logger.info(f"  [OK] Found {len(sections)} suitable 8\" poles:")
            for sec in sections:
                print(f"      {sec['aisc_manual_label']:20s} W={sec['weight_plf']:6.2f} lb/ft, "
                      f"Ix={sec['ix_in4']:7.1f} in4, ${sec['material_cost_per_ft']:.2f}/ft")
        else:
            logger.error("  [FAIL] No sections found")
        
        # Test 3: Wind pressure calculation
        logger.info("\n[TEST 3] Wind pressure calculation (115 mph, Exposure C)...")
        pressure = await conn.fetchval("""
            SELECT calculate_wind_pressure(115, 'C'::exposure_category, 'II'::risk_category, 15)
        """)
        logger.info(f"  [OK] Design wind pressure: {pressure:.2f} psf")
        
        # Test 4: Check foreign key to AISC
        logger.info("\n[TEST 4] Foreign key relationship to AISC catalog...")
        fkey = await conn.fetchrow("""
            SELECT 
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table,
                ccu.column_name AS foreign_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
              ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name = 'monument_configs'
              AND ccu.table_name = 'aisc_shapes_v16'
        """)
        
        if fkey:
            print(f"  [OK] monument_configs.{fkey['column_name']} -> "
                  f"{fkey['foreign_table']}.{fkey['foreign_column']}")
        else:
            logger.warning("  [WARN] Foreign key not found")
        
        logger.info("\n" + "="*60)
        logger.info("MONUMENT POLE MODULE TESTS COMPLETE")
        logger.info("="*60)
        
    finally:
        await conn.close()


async def main():
    """Create and test monument pole module"""
    await create_monument_tables()
    await test_monument_module()


if __name__ == "__main__":
    asyncio.run(main())
