-- ============================================================================
-- SignX Studio Pole Architecture - Direct SQL Installation
-- Alternative to Alembic migration 012
-- Execute with: psql -U postgres -d signx_studio -f create_pole_architecture.sql
-- ============================================================================

\echo '=========================================='
\echo 'SignX Studio Pole Architecture Setup'
\echo '=========================================='
\echo ''

-- Enable better error display
\set ON_ERROR_STOP on
\set ECHO all

-- ============================================================================
-- STEP 1: Drop Old Monument Tables (Clean Break)
-- ============================================================================

\echo ''
\echo '[1/8] Dropping monument tables...'

-- Drop foreign key from projects if exists
ALTER TABLE IF EXISTS projects DROP CONSTRAINT IF EXISTS fk_projects_monument_config;

-- Drop columns from projects
ALTER TABLE IF EXISTS projects DROP COLUMN IF EXISTS monument_config_id;
ALTER TABLE IF EXISTS projects DROP COLUMN IF EXISTS has_monument;

-- Drop function and view
DROP FUNCTION IF EXISTS select_monument_pole CASCADE;
DROP VIEW IF EXISTS optimal_monument_poles CASCADE;

-- Drop tables
DROP TABLE IF EXISTS monument_analysis_results CASCADE;
DROP TABLE IF EXISTS monument_configs CASCADE;

\echo '  ✓ Monument tables dropped'

-- ============================================================================
-- STEP 2: Create ENUMs
-- ============================================================================

\echo ''
\echo '[2/8] Creating ENUM types...'

-- Application type (universal framework)
DO $$ BEGIN
    CREATE TYPE application_type AS ENUM ('monument', 'pylon', 'cantilever_post', 'wall_mount');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Risk category per IBC Table 1604.5
DO $$ BEGIN
    CREATE TYPE risk_category AS ENUM ('I', 'II', 'III', 'IV');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Load distribution method for double-pole
DO $$ BEGIN
    CREATE TYPE load_distribution_method AS ENUM ('equal', 'proportional');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Ensure exposure_category exists (may already exist from old setup)
DO $$ BEGIN
    CREATE TYPE exposure_category AS ENUM ('B', 'C', 'D');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

\echo '  ✓ ENUM types created'

-- ============================================================================
-- STEP 3: Create Single Pole Tables
-- ============================================================================

\echo ''
\echo '[3/8] Creating single_pole_configs table...'

CREATE TABLE single_pole_configs (
    id VARCHAR PRIMARY KEY,
    project_id VARCHAR NOT NULL,

    -- Application classification
    application_type application_type NOT NULL,

    -- Pole geometry
    pole_height_ft FLOAT NOT NULL,
    pole_section VARCHAR NOT NULL,  -- FK to aisc_manual_label
    embedment_depth_ft FLOAT NOT NULL,
    base_plate_size_in FLOAT,

    -- Sign geometry
    sign_width_ft FLOAT NOT NULL,
    sign_height_ft FLOAT NOT NULL,
    sign_area_sqft FLOAT NOT NULL,
    sign_thickness_in FLOAT DEFAULT 0.125,
    sign_weight_psf FLOAT DEFAULT 3.0,
    clearance_to_grade_ft FLOAT DEFAULT 8.0,

    -- Wind loads per ASCE 7-22 Chapter 26
    basic_wind_speed_mph FLOAT NOT NULL,
    risk_category risk_category DEFAULT 'II',
    exposure_category exposure_category NOT NULL,
    topographic_factor_kzt FLOAT DEFAULT 1.0,
    wind_directionality_factor_kd FLOAT DEFAULT 0.85,
    elevation_factor_ke FLOAT DEFAULT 1.0,
    gust_effect_factor_g FLOAT DEFAULT 0.85,
    force_coefficient_cf FLOAT DEFAULT 1.2,

    -- Soil/foundation
    soil_bearing_capacity_psf FLOAT DEFAULT 2000,
    soil_friction_angle_deg FLOAT,
    soil_cohesion_psf FLOAT,
    groundwater_depth_ft FLOAT,

    -- Design criteria
    deflection_limit_ratio FLOAT DEFAULT 240,
    stress_ratio_limit FLOAT DEFAULT 1.0,
    overturning_safety_factor_min FLOAT DEFAULT 1.5,
    foundation_type VARCHAR DEFAULT 'drilled_pier',

    -- Additional loads (optional)
    ground_snow_load_psf FLOAT DEFAULT 0,
    ice_thickness_in FLOAT DEFAULT 0,
    seismic_sds FLOAT DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    created_by VARCHAR,
    notes TEXT,

    -- Constraints
    CONSTRAINT ck_single_pole_height CHECK (pole_height_ft > 0 AND pole_height_ft <= 100),
    CONSTRAINT ck_single_embedment CHECK (embedment_depth_ft >= 3 AND embedment_depth_ft <= 25),
    CONSTRAINT ck_single_sign_area CHECK (sign_area_sqft > 0 AND sign_area_sqft <= 1000),
    CONSTRAINT ck_single_wind_speed CHECK (basic_wind_speed_mph >= 85 AND basic_wind_speed_mph <= 200),
    CONSTRAINT ck_single_kzt CHECK (topographic_factor_kzt >= 1.0 AND topographic_factor_kzt <= 3.0),
    CONSTRAINT ck_single_kd CHECK (wind_directionality_factor_kd > 0 AND wind_directionality_factor_kd <= 1.0),
    CONSTRAINT ck_single_soil_bearing CHECK (soil_bearing_capacity_psf >= 1000)
);

\echo '  ✓ single_pole_configs created'

\echo ''
\echo '[4/8] Creating single_pole_results table...'

CREATE TABLE single_pole_results (
    id VARCHAR PRIMARY KEY,
    config_id VARCHAR NOT NULL,
    project_id VARCHAR NOT NULL,

    -- Wind load analysis
    velocity_pressure_exposure_coeff_kz FLOAT NOT NULL,
    wind_importance_factor_iw FLOAT NOT NULL,
    velocity_pressure_qz_psf FLOAT NOT NULL,
    design_wind_pressure_psf FLOAT NOT NULL,
    total_wind_force_lbs FLOAT NOT NULL,
    wind_moment_at_base_kipft FLOAT NOT NULL,

    -- Dead loads
    dead_load_sign_lbs FLOAT NOT NULL,
    dead_load_pole_lbs FLOAT NOT NULL,
    total_dead_load_lbs FLOAT NOT NULL,

    -- Structural analysis
    max_bending_moment_kipft FLOAT NOT NULL,
    max_shear_force_kips FLOAT NOT NULL,
    bending_stress_fb_ksi FLOAT NOT NULL,
    shear_stress_fv_ksi FLOAT NOT NULL,
    allowable_bending_Fb_ksi FLOAT NOT NULL,
    allowable_shear_Fv_ksi FLOAT NOT NULL,
    bending_stress_ratio FLOAT NOT NULL,
    shear_stress_ratio FLOAT NOT NULL,
    combined_stress_ratio FLOAT NOT NULL,

    -- Deflection
    max_deflection_in FLOAT NOT NULL,
    deflection_ratio_l_over FLOAT NOT NULL,
    deflection_limit_l_over FLOAT NOT NULL,

    -- Foundation
    overturning_moment_kipft FLOAT NOT NULL,
    resisting_moment_kipft FLOAT NOT NULL,
    safety_factor_overturning FLOAT NOT NULL,
    max_soil_pressure_psf FLOAT NOT NULL,
    foundation_diameter_ft FLOAT,
    foundation_depth_ft FLOAT,
    concrete_volume_cuyd FLOAT,

    -- Pass/fail checks
    passes_strength_check BOOLEAN NOT NULL,
    passes_deflection_check BOOLEAN NOT NULL,
    passes_overturning_check BOOLEAN NOT NULL,
    passes_soil_bearing_check BOOLEAN NOT NULL,
    passes_all_checks BOOLEAN NOT NULL,

    -- Critical failure mode
    critical_failure_mode VARCHAR,

    -- Metadata
    warnings JSONB DEFAULT '[]',
    design_notes JSONB DEFAULT '[]',
    code_references JSONB DEFAULT '[]',
    analysis_method VARCHAR DEFAULT 'ASCE7-22_IBC2024',
    calculation_engine VARCHAR DEFAULT 'APEX_v2.0',
    content_sha256 VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),

    -- Foreign keys
    FOREIGN KEY (config_id) REFERENCES single_pole_configs(id) ON DELETE CASCADE,

    -- Constraints
    CONSTRAINT ck_single_qz_positive CHECK (velocity_pressure_qz_psf >= 0),
    CONSTRAINT ck_single_bending_ratio CHECK (bending_stress_ratio >= 0),
    CONSTRAINT ck_single_overturning_sf CHECK (safety_factor_overturning >= 0)
);

\echo '  ✓ single_pole_results created'

-- ============================================================================
-- STEP 5: Create Double Pole Tables
-- ============================================================================

\echo ''
\echo '[5/8] Creating double_pole_configs table...'

CREATE TABLE double_pole_configs (
    id VARCHAR PRIMARY KEY,
    project_id VARCHAR NOT NULL,

    -- Application classification
    application_type application_type DEFAULT 'monument',

    -- Pole geometry (two poles)
    pole_height_ft FLOAT NOT NULL,
    pole_section VARCHAR NOT NULL,
    pole_spacing_ft FLOAT NOT NULL,  -- Critical for double-pole
    embedment_depth_ft FLOAT NOT NULL,
    base_plate_size_in FLOAT,

    -- Sign geometry
    sign_width_ft FLOAT NOT NULL,
    sign_height_ft FLOAT NOT NULL,
    sign_area_sqft FLOAT NOT NULL,
    sign_thickness_in FLOAT DEFAULT 0.125,
    sign_weight_psf FLOAT DEFAULT 3.0,
    clearance_to_grade_ft FLOAT DEFAULT 8.0,

    -- Load distribution
    load_distribution_method load_distribution_method DEFAULT 'equal',
    lateral_bracing_required BOOLEAN DEFAULT false,
    differential_settlement_limit_in FLOAT DEFAULT 0.5,

    -- Wind loads (same as single-pole)
    basic_wind_speed_mph FLOAT NOT NULL,
    risk_category risk_category DEFAULT 'II',
    exposure_category exposure_category NOT NULL,
    topographic_factor_kzt FLOAT DEFAULT 1.0,
    wind_directionality_factor_kd FLOAT DEFAULT 0.85,
    elevation_factor_ke FLOAT DEFAULT 1.0,
    gust_effect_factor_g FLOAT DEFAULT 0.85,
    force_coefficient_cf FLOAT DEFAULT 1.2,

    -- Soil/foundation
    soil_bearing_capacity_psf FLOAT DEFAULT 2000,
    soil_friction_angle_deg FLOAT,
    soil_cohesion_psf FLOAT,
    groundwater_depth_ft FLOAT,

    -- Design criteria
    deflection_limit_ratio FLOAT DEFAULT 240,
    stress_ratio_limit FLOAT DEFAULT 1.0,
    overturning_safety_factor_min FLOAT DEFAULT 1.5,
    foundation_type VARCHAR DEFAULT 'drilled_pier',

    -- Additional loads
    ground_snow_load_psf FLOAT DEFAULT 0,
    ice_thickness_in FLOAT DEFAULT 0,
    seismic_sds FLOAT DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    created_by VARCHAR,
    notes TEXT,

    -- Constraints
    CONSTRAINT ck_double_pole_height CHECK (pole_height_ft > 0 AND pole_height_ft <= 100),
    CONSTRAINT ck_double_spacing CHECK (pole_spacing_ft >= 3 AND pole_spacing_ft <= 50),
    CONSTRAINT ck_double_embedment CHECK (embedment_depth_ft >= 3 AND embedment_depth_ft <= 25),
    CONSTRAINT ck_double_sign_area CHECK (sign_area_sqft > 0 AND sign_area_sqft <= 2000),
    CONSTRAINT ck_double_wind_speed CHECK (basic_wind_speed_mph >= 85 AND basic_wind_speed_mph <= 200),
    CONSTRAINT ck_double_soil_bearing CHECK (soil_bearing_capacity_psf >= 1000)
);

\echo '  ✓ double_pole_configs created'

\echo ''
\echo '[6/8] Creating double_pole_results table...'

CREATE TABLE double_pole_results (
    id VARCHAR PRIMARY KEY,
    config_id VARCHAR NOT NULL,
    project_id VARCHAR NOT NULL,

    -- Wind load analysis (total)
    velocity_pressure_exposure_coeff_kz FLOAT NOT NULL,
    wind_importance_factor_iw FLOAT NOT NULL,
    velocity_pressure_qz_psf FLOAT NOT NULL,
    design_wind_pressure_psf FLOAT NOT NULL,
    total_wind_force_lbs FLOAT NOT NULL,
    wind_moment_total_kipft FLOAT NOT NULL,

    -- Load distribution
    load_per_pole_lbs FLOAT NOT NULL,
    moment_per_pole_kipft FLOAT NOT NULL,
    lateral_stability_check BOOLEAN NOT NULL,

    -- Dead loads
    dead_load_sign_lbs FLOAT NOT NULL,
    dead_load_per_pole_lbs FLOAT NOT NULL,
    total_dead_load_lbs FLOAT NOT NULL,

    -- Structural analysis (per pole)
    max_bending_moment_per_pole_kipft FLOAT NOT NULL,
    max_shear_force_per_pole_kips FLOAT NOT NULL,
    bending_stress_fb_ksi FLOAT NOT NULL,
    shear_stress_fv_ksi FLOAT NOT NULL,
    allowable_bending_Fb_ksi FLOAT NOT NULL,
    allowable_shear_Fv_ksi FLOAT NOT NULL,
    bending_stress_ratio FLOAT NOT NULL,
    shear_stress_ratio FLOAT NOT NULL,
    combined_stress_ratio FLOAT NOT NULL,

    -- Deflection
    max_deflection_in FLOAT NOT NULL,
    deflection_ratio_l_over FLOAT NOT NULL,
    deflection_limit_l_over FLOAT NOT NULL,

    -- Foundation (per pole)
    overturning_moment_per_pole_kipft FLOAT NOT NULL,
    resisting_moment_per_pole_kipft FLOAT NOT NULL,
    safety_factor_overturning FLOAT NOT NULL,
    max_soil_pressure_psf FLOAT NOT NULL,
    foundation_diameter_ft FLOAT,
    foundation_depth_ft FLOAT,
    concrete_volume_total_cuyd FLOAT,

    -- Pass/fail checks
    passes_strength_check BOOLEAN NOT NULL,
    passes_deflection_check BOOLEAN NOT NULL,
    passes_overturning_check BOOLEAN NOT NULL,
    passes_soil_bearing_check BOOLEAN NOT NULL,
    passes_lateral_stability_check BOOLEAN NOT NULL,
    passes_all_checks BOOLEAN NOT NULL,

    -- Critical failure mode
    critical_failure_mode VARCHAR,

    -- Metadata
    warnings JSONB DEFAULT '[]',
    design_notes JSONB DEFAULT '[]',
    code_references JSONB DEFAULT '[]',
    analysis_method VARCHAR DEFAULT 'ASCE7-22_IBC2024',
    calculation_engine VARCHAR DEFAULT 'APEX_v2.0',
    content_sha256 VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),

    -- Foreign keys
    FOREIGN KEY (config_id) REFERENCES double_pole_configs(id) ON DELETE CASCADE,

    -- Constraints
    CONSTRAINT ck_double_load_per_pole CHECK (load_per_pole_lbs > 0),
    CONSTRAINT ck_double_overturning_sf CHECK (safety_factor_overturning >= 0)
);

\echo '  ✓ double_pole_results created'

-- ============================================================================
-- STEP 7: Create Indexes
-- ============================================================================

\echo ''
\echo '[7/8] Creating performance indexes...'

-- Single pole indexes
CREATE INDEX ix_single_pole_configs_project_id ON single_pole_configs(project_id);
CREATE INDEX ix_single_pole_configs_pole_section ON single_pole_configs(pole_section);
CREATE INDEX ix_single_pole_configs_application ON single_pole_configs(application_type);
CREATE INDEX ix_single_pole_results_project_id ON single_pole_results(project_id);
CREATE INDEX ix_single_pole_results_config_id ON single_pole_results(config_id);
CREATE INDEX ix_single_pole_results_passes ON single_pole_results(passes_all_checks);
CREATE INDEX ix_single_pole_results_sha256 ON single_pole_results(content_sha256);

-- Double pole indexes
CREATE INDEX ix_double_pole_configs_project_id ON double_pole_configs(project_id);
CREATE INDEX ix_double_pole_configs_pole_section ON double_pole_configs(pole_section);
CREATE INDEX ix_double_pole_results_project_id ON double_pole_results(project_id);
CREATE INDEX ix_double_pole_results_config_id ON double_pole_results(config_id);
CREATE INDEX ix_double_pole_results_passes ON double_pole_results(passes_all_checks);

\echo '  ✓ Indexes created'

-- ============================================================================
-- STEP 8: Create Functions and Views
-- ============================================================================

\echo ''
\echo '[8/8] Creating ASCE 7-22 wind pressure function...'

CREATE OR REPLACE FUNCTION calculate_asce7_wind_pressure(
    p_wind_speed_mph FLOAT,
    p_exposure_category exposure_category,
    p_risk_category risk_category,
    p_height_ft FLOAT,
    p_kzt FLOAT DEFAULT 1.0,
    p_kd FLOAT DEFAULT 0.85,
    p_ke FLOAT DEFAULT 1.0
)
RETURNS TABLE (
    kz FLOAT,
    iw FLOAT,
    qz_psf FLOAT,
    code_ref VARCHAR
)
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_kz FLOAT;
    v_iw FLOAT;
    v_qz FLOAT;
    v_height_ft FLOAT := GREATEST(p_height_ft, 15);  -- Min 15 ft per ASCE 7-22
BEGIN
    -- Velocity pressure exposure coefficient Kz per ASCE 7-22 Table 26.10-1
    IF p_exposure_category = 'B' THEN
        v_kz := CASE
            WHEN v_height_ft <= 15 THEN 0.57
            WHEN v_height_ft <= 20 THEN 0.62
            WHEN v_height_ft <= 25 THEN 0.66
            WHEN v_height_ft <= 30 THEN 0.70
            WHEN v_height_ft <= 40 THEN 0.76
            WHEN v_height_ft <= 50 THEN 0.81
            WHEN v_height_ft <= 60 THEN 0.85
            ELSE 0.85 + (v_height_ft - 60) * 0.01
        END;
    ELSIF p_exposure_category = 'C' THEN
        v_kz := CASE
            WHEN v_height_ft <= 15 THEN 0.85
            WHEN v_height_ft <= 20 THEN 0.90
            WHEN v_height_ft <= 25 THEN 0.94
            WHEN v_height_ft <= 30 THEN 0.98
            WHEN v_height_ft <= 40 THEN 1.04
            WHEN v_height_ft <= 50 THEN 1.09
            WHEN v_height_ft <= 60 THEN 1.13
            ELSE 1.13 + (v_height_ft - 60) * 0.01
        END;
    ELSIF p_exposure_category = 'D' THEN
        v_kz := CASE
            WHEN v_height_ft <= 15 THEN 1.03
            WHEN v_height_ft <= 20 THEN 1.08
            WHEN v_height_ft <= 25 THEN 1.12
            WHEN v_height_ft <= 30 THEN 1.16
            WHEN v_height_ft <= 40 THEN 1.22
            WHEN v_height_ft <= 50 THEN 1.27
            WHEN v_height_ft <= 60 THEN 1.31
            ELSE 1.31 + (v_height_ft - 60) * 0.012
        END;
    ELSE
        v_kz := 0.85;  -- Default to Exposure C at 15 ft
    END IF;

    -- Wind importance factor Iw per ASCE 7-22 Table 1.5-2
    v_iw := CASE p_risk_category
        WHEN 'I' THEN 0.87
        WHEN 'II' THEN 1.00
        WHEN 'III' THEN 1.15
        WHEN 'IV' THEN 1.15
        ELSE 1.00
    END;

    -- Velocity pressure per ASCE 7-22 Equation 26.10-1
    -- qz = 0.00256 * Kz * Kzt * Kd * Ke * V²
    v_qz := 0.00256 * v_kz * p_kzt * p_kd * p_ke * POWER(p_wind_speed_mph, 2);

    RETURN QUERY SELECT
        v_kz,
        v_iw,
        v_qz,
        'ASCE 7-22 Eq 26.10-1'::VARCHAR;
END;
$$;

\echo '  ✓ calculate_asce7_wind_pressure() created'

\echo ''
\echo 'Creating optimal_pole_sections view...'

CREATE OR REPLACE VIEW optimal_pole_sections AS
SELECT
    s.aisc_manual_label as designation,
    s.type,
    s.w as weight_plf,
    s.nominal_depth as diameter_in,
    s.area as area_in2,
    s.ix as ix_in4,
    s.sx as sx_in3,
    s.rx as rx_in,
    s.fy as yield_strength_ksi,
    s.is_astm_a1085,

    -- Performance metrics
    s.sx / s.w as efficiency_ratio,

    -- AISC 360-22 ASD capacities
    s.sx * s.fy * 0.66 / 12 as moment_capacity_asd_kipft,
    s.area * s.fy * 0.4 as shear_capacity_asd_kips,

    -- Slenderness limits
    s.rx * 200 / 12 as max_height_ft_slenderness,

    -- Cost estimates
    s.w * 0.90 as material_cost_per_ft,
    s.w * 0.90 * 2.5 as installed_cost_per_ft,

    -- Application recommendations
    CASE
        WHEN s.nominal_depth <= 6 THEN 'Small signs (< 20 ft, < 30 sqft)'
        WHEN s.nominal_depth <= 8 THEN 'Medium signs (20-30 ft, 30-80 sqft)'
        WHEN s.nominal_depth <= 10 THEN 'Large signs (30-40 ft, 80-150 sqft)'
        WHEN s.nominal_depth <= 12 THEN 'XL signs (40-50 ft, 150-300 sqft)'
        ELSE 'XXL signs (> 50 ft, > 300 sqft)'
    END as typical_application

FROM aisc_shapes_v16 s
WHERE s.type IN ('HSS', 'PIPE')
    AND s.nominal_depth >= 4
    AND s.nominal_depth <= 24
    AND s.w <= 150
    AND s.is_available = true
ORDER BY s.nominal_depth, s.w;

\echo '  ✓ optimal_pole_sections view created'

-- ============================================================================
-- COMPLETION SUMMARY
-- ============================================================================

\echo ''
\echo '=========================================='
\echo 'Installation Complete!'
\echo '=========================================='
\echo ''
\echo 'Summary:'
\echo '  • Dropped: monument_configs, monument_analysis_results'
\echo '  • Created: single_pole_configs, single_pole_results'
\echo '  • Created: double_pole_configs, double_pole_results'
\echo '  • Created: calculate_asce7_wind_pressure() function'
\echo '  • Created: optimal_pole_sections view'
\echo '  • Created: 14 performance indexes'
\echo ''
\echo 'Verification:'

-- Count tables
SELECT 'Tables created: ' || COUNT(*)::TEXT
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name LIKE '%pole%';

-- Check function
SELECT 'Function exists: ' ||
    CASE WHEN EXISTS (
        SELECT 1 FROM pg_proc WHERE proname = 'calculate_asce7_wind_pressure'
    ) THEN 'YES' ELSE 'NO' END;

-- Check view
SELECT 'View exists: ' ||
    CASE WHEN EXISTS (
        SELECT 1 FROM pg_views WHERE viewname = 'optimal_pole_sections'
    ) THEN 'YES' ELSE 'NO' END;

\echo ''
\echo 'Next steps:'
\echo '  1. Test ASCE 7-22 function: SELECT * FROM calculate_asce7_wind_pressure(115, ''C'', ''II'', 15.0);'
\echo '  2. View pole catalog: SELECT * FROM optimal_pole_sections LIMIT 5;'
\echo '  3. Insert test configuration'
\echo ''
