#!/usr/bin/env python
"""Set up monument tables and test functionality"""

import asyncio
import asyncpg
import logging

logger = logging.getLogger(__name__)

async def setup_monument_tables():
    conn = await asyncpg.connect('postgresql://apex:apex@localhost:5432/apex')
    
    try:
        logger.info('Creating monument tables...')
        
        # Create enums
        await conn.execute('''
            DO $$ BEGIN
                CREATE TYPE exposure_category AS ENUM ('B', 'C', 'D');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        ''')
        
        await conn.execute('''
            DO $$ BEGIN
                CREATE TYPE importance_factor AS ENUM ('I', 'II', 'III', 'IV');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        ''')
        
        # Create monument_configs table
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS monument_configs (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR NOT NULL,
            
            -- Pole geometry
            pole_height_ft FLOAT NOT NULL,
            pole_section VARCHAR NOT NULL,
            base_plate_size_in FLOAT,
            embedment_depth_ft FLOAT,
            
            -- Sign geometry  
            sign_width_ft FLOAT NOT NULL,
            sign_height_ft FLOAT NOT NULL,
            sign_area_sqft FLOAT NOT NULL,
            sign_thickness_in FLOAT DEFAULT 0.125,
            clearance_to_grade_ft FLOAT DEFAULT 8.0,
            
            -- Environmental loads
            basic_wind_speed_mph FLOAT NOT NULL,
            exposure_category exposure_category NOT NULL,
            importance_factor importance_factor DEFAULT 'II',
            gust_factor FLOAT DEFAULT 0.85,
            force_coefficient FLOAT DEFAULT 1.2,
            
            -- Site conditions
            ground_snow_load_psf FLOAT DEFAULT 0,
            ice_thickness_in FLOAT DEFAULT 0,
            seismic_sds FLOAT DEFAULT 0,
            soil_bearing_capacity_psf FLOAT DEFAULT 2000,
            
            -- Design preferences
            deflection_limit_ratio FLOAT DEFAULT 200,
            stress_ratio_limit FLOAT DEFAULT 0.9,
            foundation_type VARCHAR DEFAULT 'spread_footing',
            
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            
            FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
            FOREIGN KEY (pole_section) REFERENCES aisc_shapes_v16(aisc_manual_label) ON DELETE RESTRICT,
            
            CHECK (pole_height_ft > 0 AND pole_height_ft <= 50),
            CHECK (sign_area_sqft > 0 AND sign_area_sqft <= 500),
            CHECK (basic_wind_speed_mph >= 85 AND basic_wind_speed_mph <= 200),
            CHECK (soil_bearing_capacity_psf >= 1000)
        )
        ''')
        logger.info('[OK] Created monument_configs table')
        
        # Create view for optimal monument poles
        await conn.execute('''
        CREATE OR REPLACE VIEW optimal_monument_poles AS
        SELECT 
            s.aisc_manual_label as designation,
            s.type,
            s.w as weight_plf,
            s.nominal_depth as diameter_in,
            s.area as area_in2,
            s.ix as ix_in4,
            s.sx as sx_in3,
            s.rx as rx_in,
            s.is_astm_a1085,
            
            -- Performance metrics
            CASE WHEN s.w > 0 THEN s.sx / s.w ELSE 0 END as efficiency_ratio,
            
            -- Wind capacity estimates
            s.sx * 50 * 0.9 / 12 as moment_capacity_kipft,
            
            -- Max recommended height
            CASE WHEN s.rx > 0 THEN s.rx * 200 / 12 ELSE 0 END as max_height_ft,
            
            -- Cost estimates
            s.w * 0.90 as material_cost_per_ft,
            s.w * 0.90 * 2.5 as installed_cost_per_ft,
            
            -- Typical applications
            CASE 
                WHEN s.nominal_depth <= 6 THEN 'Small monument (< 16 ft)'
                WHEN s.nominal_depth <= 10 THEN 'Medium monument (16-25 ft)'
                WHEN s.nominal_depth <= 14 THEN 'Large monument (25-35 ft)'
                ELSE 'Extra large monument (> 35 ft)'
            END as typical_application
            
        FROM aisc_shapes_v16 s
        WHERE s.type IN ('HSS', 'PIPE')
            AND s.nominal_depth >= 6
            AND s.nominal_depth <= 16
            AND s.w <= 100
            AND s.is_available = true
        ORDER BY s.nominal_depth, s.w
        ''')
        logger.info('[OK] Created optimal_monument_poles view')
        
        # Create monument pole selection function
        await conn.execute('''
        CREATE OR REPLACE FUNCTION select_monument_pole(
            p_wind_moment_kipft FLOAT,
            p_height_ft FLOAT,
            p_max_diameter_in INTEGER DEFAULT 14,
            p_prefer_a1085 BOOLEAN DEFAULT FALSE
        )
        RETURNS TABLE (
            designation VARCHAR,
            type VARCHAR,
            diameter_in INTEGER,
            weight_plf FLOAT,
            moment_capacity_kipft FLOAT,
            stress_ratio FLOAT,
            slenderness_ratio FLOAT,
            cost_per_ft FLOAT,
            is_a1085 BOOLEAN,
            status VARCHAR
        )
        LANGUAGE plpgsql
        AS $func$
        DECLARE
            v_required_sx FLOAT;
            v_max_slenderness FLOAT := 200;
        BEGIN
            -- Calculate required section modulus
            v_required_sx := p_wind_moment_kipft * 12 / (50 * 0.9);
            
            RETURN QUERY
            SELECT 
                s.aisc_manual_label,
                s.type,
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
                END as status
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
        ''')
        logger.info('[OK] Created select_monument_pole function')
        
        logger.info('\n=== TESTING MONUMENT SETUP ===')
        
        # Test the view
        sections = await conn.fetch('''
            SELECT designation, diameter_in, weight_plf, moment_capacity_kipft, typical_application
            FROM optimal_monument_poles
            WHERE diameter_in IN (8, 10, 12)
            ORDER BY diameter_in, weight_plf
            LIMIT 10
        ''')
        
        logger.info('\nAvailable monument sections:')
        for s in sections:
            logger.info(f'  {s[0]:15s} D={s[1]:2d}" W={s[2]:6.1f} lb/ft Cap={s[3]:6.1f} kip-ft {s[4]}')
        
        # Test the function
        results = await conn.fetch('''
            SELECT designation, diameter_in, stress_ratio, status
            FROM select_monument_pole(150, 25, 12, false)
            LIMIT 5
        ''')
        
        logger.info(f'\nSections for 150 kip-ft moment, 25ft height:')
        for r in results:
            logger.info(f'  {r[0]:15s} D={r[1]:2d}" Ratio={r[2]:.3f} {r[3]}')
        
        logger.info('\n[SUCCESS] Monument module setup complete!')
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(setup_monument_tables())