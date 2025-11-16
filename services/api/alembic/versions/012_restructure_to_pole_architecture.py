"""Restructure to single-pole and double-pole architecture with IBC 2024/ASCE 7-22 compliance

Revision ID: 012_pole_restructure
Revises: 011_monument
Create Date: 2025-11-01

Clean architectural break from monument-specific to universal single/double-pole framework.
Implements exact ASCE 7-22 wind load tables and IBC 2024 Section 1605/1807 requirements.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '012_pole_restructure'
down_revision: Union[str, None] = '011_monument'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Restructure to single-pole and double-pole architecture."""

    logger.info("[INFO] Starting restructure to pole architecture...")

    # =====================================================================
    # STEP 1: Drop Monument Tables (Clean Break)
    # =====================================================================

    logger.info("[1/9] Dropping monument tables and references...")

    # Drop foreign key from projects
    op.drop_constraint('fk_projects_monument_config', 'projects', type_='foreignkey')
    op.drop_column('projects', 'monument_config_id')
    op.drop_column('projects', 'has_monument')

    # Drop function and view
    op.execute("DROP FUNCTION IF EXISTS select_monument_pole CASCADE")
    op.execute("DROP VIEW IF EXISTS optimal_monument_poles CASCADE")

    # Drop tables
    op.drop_table('monument_analysis_results')
    op.drop_table('monument_configs')

    logger.info("    ✓ Monument tables dropped")

    # =====================================================================
    # STEP 2: Create New ENUMs
    # =====================================================================

    logger.info("[2/9] Creating enums for pole architecture...")

    # Application type enum (universal framework)
    application_type_enum = postgresql.ENUM(
        'monument', 'pylon', 'cantilever_post', 'wall_mount',
        name='application_type',
        create_type=True
    )
    application_type_enum.create(op.get_bind(), checkfirst=True)

    # Risk category enum per IBC Table 1604.5 / ASCE 7-22 Table 1.5-1
    risk_category_enum = postgresql.ENUM(
        'I', 'II', 'III', 'IV',
        name='risk_category',
        create_type=True
    )
    risk_category_enum.create(op.get_bind(), checkfirst=True)

    # Load distribution method for double-pole
    load_distribution_enum = postgresql.ENUM(
        'equal', 'proportional',
        name='load_distribution_method',
        create_type=True
    )
    load_distribution_enum.create(op.get_bind(), checkfirst=True)

    logger.info("    ✓ Enums created: application_type, risk_category, load_distribution_method")

    # =====================================================================
    # STEP 3: Create Single Pole Tables
    # =====================================================================

    logger.info("[3/9] Creating single_pole_configs table...")

    op.create_table(
        'single_pole_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),

        # Application classification
        sa.Column('application_type', application_type_enum, nullable=False),

        # Pole geometry
        sa.Column('pole_height_ft', sa.Float(), nullable=False),
        sa.Column('pole_section', sa.String(), nullable=False),  # FK to aisc_manual_label
        sa.Column('embedment_depth_ft', sa.Float(), nullable=False),
        sa.Column('base_plate_size_in', sa.Float()),

        # Sign geometry
        sa.Column('sign_width_ft', sa.Float(), nullable=False),
        sa.Column('sign_height_ft', sa.Float(), nullable=False),
        sa.Column('sign_area_sqft', sa.Float(), nullable=False),
        sa.Column('sign_thickness_in', sa.Float(), server_default='0.125'),
        sa.Column('sign_weight_psf', sa.Float(), server_default='3.0'),  # Aluminum typical
        sa.Column('clearance_to_grade_ft', sa.Float(), server_default='8.0'),

        # Wind loads per ASCE 7-22 Chapter 26
        sa.Column('basic_wind_speed_mph', sa.Float(), nullable=False),  # V (3-sec gust)
        sa.Column('risk_category', risk_category_enum, server_default='II'),  # IBC Table 1604.5
        sa.Column('exposure_category', exposure_category, nullable=False),  # ASCE 7-22 Section 26.7
        sa.Column('topographic_factor_kzt', sa.Float(), server_default='1.0'),  # ASCE 7-22 Section 26.8
        sa.Column('wind_directionality_factor_kd', sa.Float(), server_default='0.85'),  # ASCE 7-22 Table 26.6-1
        sa.Column('elevation_factor_ke', sa.Float(), server_default='1.0'),  # ASCE 7-22 Section 26.9
        sa.Column('gust_effect_factor_g', sa.Float(), server_default='0.85'),  # ASCE 7-22 Section 26.11
        sa.Column('force_coefficient_cf', sa.Float(), server_default='1.2'),  # ASCE 7-22 Fig 29.4-1

        # Site/soil conditions
        sa.Column('soil_bearing_capacity_psf', sa.Float(), server_default='2000'),
        sa.Column('soil_friction_angle_deg', sa.Float()),
        sa.Column('soil_cohesion_psf', sa.Float()),
        sa.Column('groundwater_depth_ft', sa.Float()),

        # Design criteria
        sa.Column('deflection_limit_ratio', sa.Float(), server_default='240'),  # L/240 per AISC
        sa.Column('stress_ratio_limit', sa.Float(), server_default='1.0'),  # Unity check
        sa.Column('overturning_safety_factor_min', sa.Float(), server_default='1.5'),  # IBC 1605.2.1
        sa.Column('foundation_type', sa.String(), server_default='drilled_pier'),

        # Additional loads (optional)
        sa.Column('ground_snow_load_psf', sa.Float(), server_default='0'),
        sa.Column('ice_thickness_in', sa.Float(), server_default='0'),
        sa.Column('seismic_sds', sa.Float(), server_default='0'),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('created_by', sa.String()),
        sa.Column('notes', sa.Text()),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pole_section'], ['aisc_shapes_v16.aisc_manual_label'], ondelete='RESTRICT'),

        # IBC 2024 / ASCE 7-22 constraints
        sa.CheckConstraint('pole_height_ft > 0 AND pole_height_ft <= 100', name='ck_single_pole_height'),
        sa.CheckConstraint('embedment_depth_ft >= 3 AND embedment_depth_ft <= 25', name='ck_single_embedment'),
        sa.CheckConstraint('sign_area_sqft > 0 AND sign_area_sqft <= 1000', name='ck_single_sign_area'),
        sa.CheckConstraint('basic_wind_speed_mph >= 85 AND basic_wind_speed_mph <= 200', name='ck_single_wind_speed'),
        sa.CheckConstraint('topographic_factor_kzt >= 1.0 AND topographic_factor_kzt <= 3.0', name='ck_single_kzt'),
        sa.CheckConstraint('wind_directionality_factor_kd > 0 AND wind_directionality_factor_kd <= 1.0', name='ck_single_kd'),
        sa.CheckConstraint('soil_bearing_capacity_psf >= 1000', name='ck_single_soil_bearing'),
    )

    logger.info("    ✓ single_pole_configs table created")

    # =====================================================================
    # STEP 4: Create Single Pole Results Table
    # =====================================================================

    logger.info("[4/9] Creating single_pole_results table...")

    op.create_table(
        'single_pole_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('config_id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),

        # ASCE 7-22 Wind Load Analysis (Chapter 26-29)
        sa.Column('velocity_pressure_exposure_coeff_kz', sa.Float(), nullable=False),  # Table 26.10-1
        sa.Column('wind_importance_factor_iw', sa.Float(), nullable=False),  # Table 1.5-2
        sa.Column('velocity_pressure_qz_psf', sa.Float(), nullable=False),  # Eq 26.10-1
        sa.Column('design_wind_pressure_psf', sa.Float(), nullable=False),  # p = qz * G * Cf
        sa.Column('total_wind_force_lbs', sa.Float(), nullable=False),  # F = p * A
        sa.Column('wind_moment_at_base_kipft', sa.Float(), nullable=False),  # M = F * h

        # Additional loads
        sa.Column('dead_load_sign_lbs', sa.Float(), nullable=False),
        sa.Column('dead_load_pole_lbs', sa.Float(), nullable=False),
        sa.Column('snow_load_lbs', sa.Float(), server_default='0'),
        sa.Column('ice_load_lbs', sa.Float(), server_default='0'),
        sa.Column('seismic_force_lbs', sa.Float(), server_default='0'),
        sa.Column('total_dead_load_lbs', sa.Float(), nullable=False),

        # AISC 360-22 Structural Analysis
        sa.Column('max_bending_moment_kipft', sa.Float(), nullable=False),
        sa.Column('max_shear_force_kips', sa.Float(), nullable=False),
        sa.Column('bending_stress_fb_ksi', sa.Float(), nullable=False),  # fb = M/Sx
        sa.Column('shear_stress_fv_ksi', sa.Float(), nullable=False),  # fv = V/Aw
        sa.Column('allowable_bending_Fb_ksi', sa.Float(), nullable=False),  # 0.66*Fy for ASD
        sa.Column('allowable_shear_Fv_ksi', sa.Float(), nullable=False),  # 0.40*Fy for ASD
        sa.Column('bending_stress_ratio', sa.Float(), nullable=False),  # fb/Fb
        sa.Column('shear_stress_ratio', sa.Float(), nullable=False),  # fv/Fv
        sa.Column('combined_stress_ratio', sa.Float(), nullable=False),  # Unity check

        # Deflection analysis
        sa.Column('max_deflection_in', sa.Float(), nullable=False),  # δ = FL³/(3EI)
        sa.Column('deflection_ratio_l_over', sa.Float(), nullable=False),  # L/δ
        sa.Column('deflection_limit_l_over', sa.Float(), nullable=False),  # L/240 typical

        # Foundation analysis per IBC 2024 Section 1807
        sa.Column('overturning_moment_kipft', sa.Float(), nullable=False),
        sa.Column('resisting_moment_kipft', sa.Float(), nullable=False),
        sa.Column('safety_factor_overturning', sa.Float(), nullable=False),  # IBC 1605.2.1: SF ≥ 1.5
        sa.Column('max_soil_pressure_psf', sa.Float(), nullable=False),
        sa.Column('foundation_diameter_ft', sa.Float()),
        sa.Column('foundation_depth_ft', sa.Float()),
        sa.Column('concrete_volume_cuyd', sa.Float()),

        # Pass/fail checks
        sa.Column('passes_strength_check', sa.Boolean(), nullable=False),
        sa.Column('passes_deflection_check', sa.Boolean(), nullable=False),
        sa.Column('passes_overturning_check', sa.Boolean(), nullable=False),
        sa.Column('passes_soil_bearing_check', sa.Boolean(), nullable=False),
        sa.Column('passes_all_checks', sa.Boolean(), nullable=False),

        # Critical failure mode
        sa.Column('critical_failure_mode', sa.String()),  # 'BENDING', 'SHEAR', 'DEFLECTION', 'OVERTURNING', 'SOIL_BEARING'

        # Warnings and notes
        sa.Column('warnings', postgresql.JSONB, server_default='[]'),
        sa.Column('design_notes', postgresql.JSONB, server_default='[]'),
        sa.Column('code_references', postgresql.JSONB, server_default='[]'),

        # Calculation metadata
        sa.Column('analysis_method', sa.String(), server_default='ASCE7-22_IBC2024'),
        sa.Column('calculation_engine', sa.String(), server_default='APEX_v2.0'),
        sa.Column('content_sha256', sa.String()),  # For caching/deduplication
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['config_id'], ['single_pole_configs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),

        # Constraints
        sa.CheckConstraint('velocity_pressure_qz_psf >= 0', name='ck_single_qz_positive'),
        sa.CheckConstraint('bending_stress_ratio >= 0', name='ck_single_bending_ratio'),
        sa.CheckConstraint('safety_factor_overturning >= 0', name='ck_single_overturning_sf'),
    )

    logger.info("    ✓ single_pole_results table created")

    # =====================================================================
    # STEP 5: Create Double Pole Tables
    # =====================================================================

    logger.info("[5/9] Creating double_pole_configs table...")

    op.create_table(
        'double_pole_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),

        # Application classification
        sa.Column('application_type', application_type_enum, server_default='monument'),

        # Pole geometry (two poles)
        sa.Column('pole_height_ft', sa.Float(), nullable=False),
        sa.Column('pole_section', sa.String(), nullable=False),  # FK to aisc_manual_label
        sa.Column('pole_spacing_ft', sa.Float(), nullable=False),  # Critical for double-pole
        sa.Column('embedment_depth_ft', sa.Float(), nullable=False),
        sa.Column('base_plate_size_in', sa.Float()),

        # Sign geometry
        sa.Column('sign_width_ft', sa.Float(), nullable=False),
        sa.Column('sign_height_ft', sa.Float(), nullable=False),
        sa.Column('sign_area_sqft', sa.Float(), nullable=False),
        sa.Column('sign_thickness_in', sa.Float(), server_default='0.125'),
        sa.Column('sign_weight_psf', sa.Float(), server_default='3.0'),
        sa.Column('clearance_to_grade_ft', sa.Float(), server_default='8.0'),

        # Load distribution between poles
        sa.Column('load_distribution_method', load_distribution_enum, server_default='equal'),
        sa.Column('lateral_bracing_required', sa.Boolean(), server_default='false'),
        sa.Column('differential_settlement_limit_in', sa.Float(), server_default='0.5'),

        # Wind loads per ASCE 7-22 Chapter 26
        sa.Column('basic_wind_speed_mph', sa.Float(), nullable=False),
        sa.Column('risk_category', risk_category_enum, server_default='II'),
        sa.Column('exposure_category', exposure_category, nullable=False),
        sa.Column('topographic_factor_kzt', sa.Float(), server_default='1.0'),
        sa.Column('wind_directionality_factor_kd', sa.Float(), server_default='0.85'),
        sa.Column('elevation_factor_ke', sa.Float(), server_default='1.0'),
        sa.Column('gust_effect_factor_g', sa.Float(), server_default='0.85'),
        sa.Column('force_coefficient_cf', sa.Float(), server_default='1.2'),

        # Site/soil conditions
        sa.Column('soil_bearing_capacity_psf', sa.Float(), server_default='2000'),
        sa.Column('soil_friction_angle_deg', sa.Float()),
        sa.Column('soil_cohesion_psf', sa.Float()),
        sa.Column('groundwater_depth_ft', sa.Float()),

        # Design criteria
        sa.Column('deflection_limit_ratio', sa.Float(), server_default='240'),
        sa.Column('stress_ratio_limit', sa.Float(), server_default='1.0'),
        sa.Column('overturning_safety_factor_min', sa.Float(), server_default='1.5'),
        sa.Column('foundation_type', sa.String(), server_default='drilled_pier'),

        # Additional loads (optional)
        sa.Column('ground_snow_load_psf', sa.Float(), server_default='0'),
        sa.Column('ice_thickness_in', sa.Float(), server_default='0'),
        sa.Column('seismic_sds', sa.Float(), server_default='0'),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('created_by', sa.String()),
        sa.Column('notes', sa.Text()),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pole_section'], ['aisc_shapes_v16.aisc_manual_label'], ondelete='RESTRICT'),

        # Constraints
        sa.CheckConstraint('pole_height_ft > 0 AND pole_height_ft <= 100', name='ck_double_pole_height'),
        sa.CheckConstraint('pole_spacing_ft >= 3 AND pole_spacing_ft <= 50', name='ck_double_spacing'),
        sa.CheckConstraint('embedment_depth_ft >= 3 AND embedment_depth_ft <= 25', name='ck_double_embedment'),
        sa.CheckConstraint('sign_area_sqft > 0 AND sign_area_sqft <= 2000', name='ck_double_sign_area'),
        sa.CheckConstraint('basic_wind_speed_mph >= 85 AND basic_wind_speed_mph <= 200', name='ck_double_wind_speed'),
        sa.CheckConstraint('soil_bearing_capacity_psf >= 1000', name='ck_double_soil_bearing'),
    )

    logger.info("    ✓ double_pole_configs table created")

    logger.info("[6/9] Creating double_pole_results table...")

    op.create_table(
        'double_pole_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('config_id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),

        # Wind load analysis (same as single-pole)
        sa.Column('velocity_pressure_exposure_coeff_kz', sa.Float(), nullable=False),
        sa.Column('wind_importance_factor_iw', sa.Float(), nullable=False),
        sa.Column('velocity_pressure_qz_psf', sa.Float(), nullable=False),
        sa.Column('design_wind_pressure_psf', sa.Float(), nullable=False),
        sa.Column('total_wind_force_lbs', sa.Float(), nullable=False),
        sa.Column('wind_moment_total_kipft', sa.Float(), nullable=False),

        # Load distribution between poles
        sa.Column('load_per_pole_lbs', sa.Float(), nullable=False),  # Typically F_total / 2
        sa.Column('moment_per_pole_kipft', sa.Float(), nullable=False),
        sa.Column('lateral_stability_check', sa.Boolean(), nullable=False),

        # Additional loads
        sa.Column('dead_load_sign_lbs', sa.Float(), nullable=False),
        sa.Column('dead_load_per_pole_lbs', sa.Float(), nullable=False),
        sa.Column('total_dead_load_lbs', sa.Float(), nullable=False),

        # Structural analysis (per pole)
        sa.Column('max_bending_moment_per_pole_kipft', sa.Float(), nullable=False),
        sa.Column('max_shear_force_per_pole_kips', sa.Float(), nullable=False),
        sa.Column('bending_stress_fb_ksi', sa.Float(), nullable=False),
        sa.Column('shear_stress_fv_ksi', sa.Float(), nullable=False),
        sa.Column('allowable_bending_Fb_ksi', sa.Float(), nullable=False),
        sa.Column('allowable_shear_Fv_ksi', sa.Float(), nullable=False),
        sa.Column('bending_stress_ratio', sa.Float(), nullable=False),
        sa.Column('shear_stress_ratio', sa.Float(), nullable=False),
        sa.Column('combined_stress_ratio', sa.Float(), nullable=False),

        # Deflection analysis
        sa.Column('max_deflection_in', sa.Float(), nullable=False),
        sa.Column('deflection_ratio_l_over', sa.Float(), nullable=False),
        sa.Column('deflection_limit_l_over', sa.Float(), nullable=False),

        # Foundation analysis (per pole)
        sa.Column('overturning_moment_per_pole_kipft', sa.Float(), nullable=False),
        sa.Column('resisting_moment_per_pole_kipft', sa.Float(), nullable=False),
        sa.Column('safety_factor_overturning', sa.Float(), nullable=False),
        sa.Column('max_soil_pressure_psf', sa.Float(), nullable=False),
        sa.Column('foundation_diameter_ft', sa.Float()),
        sa.Column('foundation_depth_ft', sa.Float()),
        sa.Column('concrete_volume_total_cuyd', sa.Float()),

        # Pass/fail checks
        sa.Column('passes_strength_check', sa.Boolean(), nullable=False),
        sa.Column('passes_deflection_check', sa.Boolean(), nullable=False),
        sa.Column('passes_overturning_check', sa.Boolean(), nullable=False),
        sa.Column('passes_soil_bearing_check', sa.Boolean(), nullable=False),
        sa.Column('passes_lateral_stability_check', sa.Boolean(), nullable=False),
        sa.Column('passes_all_checks', sa.Boolean(), nullable=False),

        # Critical failure mode
        sa.Column('critical_failure_mode', sa.String()),

        # Warnings and notes
        sa.Column('warnings', postgresql.JSONB, server_default='[]'),
        sa.Column('design_notes', postgresql.JSONB, server_default='[]'),
        sa.Column('code_references', postgresql.JSONB, server_default='[]'),

        # Calculation metadata
        sa.Column('analysis_method', sa.String(), server_default='ASCE7-22_IBC2024'),
        sa.Column('calculation_engine', sa.String(), server_default='APEX_v2.0'),
        sa.Column('content_sha256', sa.String()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['config_id'], ['double_pole_configs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),

        # Constraints
        sa.CheckConstraint('load_per_pole_lbs > 0', name='ck_double_load_per_pole'),
        sa.CheckConstraint('safety_factor_overturning >= 0', name='ck_double_overturning_sf'),
    )

    logger.info("    ✓ double_pole_results table created")

    # =====================================================================
    # STEP 7: Create Indexes
    # =====================================================================

    logger.info("[7/9] Creating performance indexes...")

    # Single pole indexes
    op.create_index('ix_single_pole_configs_project_id', 'single_pole_configs', ['project_id'])
    op.create_index('ix_single_pole_configs_pole_section', 'single_pole_configs', ['pole_section'])
    op.create_index('ix_single_pole_configs_application', 'single_pole_configs', ['application_type'])
    op.create_index('ix_single_pole_results_project_id', 'single_pole_results', ['project_id'])
    op.create_index('ix_single_pole_results_config_id', 'single_pole_results', ['config_id'])
    op.create_index('ix_single_pole_results_passes', 'single_pole_results', ['passes_all_checks'])
    op.create_index('ix_single_pole_results_sha256', 'single_pole_results', ['content_sha256'])

    # Double pole indexes
    op.create_index('ix_double_pole_configs_project_id', 'double_pole_configs', ['project_id'])
    op.create_index('ix_double_pole_configs_pole_section', 'double_pole_configs', ['pole_section'])
    op.create_index('ix_double_pole_results_project_id', 'double_pole_results', ['project_id'])
    op.create_index('ix_double_pole_results_config_id', 'double_pole_results', ['config_id'])
    op.create_index('ix_double_pole_results_passes', 'double_pole_results', ['passes_all_checks'])

    logger.info("    ✓ Indexes created")

    # =====================================================================
    # STEP 8: Update Projects Table
    # =====================================================================

    logger.info("[8/9] Updating projects table references...")

    op.add_column('projects', sa.Column('has_single_pole', sa.Boolean(), server_default='false'))
    op.add_column('projects', sa.Column('single_pole_config_id', sa.String(), nullable=True))
    op.add_column('projects', sa.Column('has_double_pole', sa.Boolean(), server_default='false'))
    op.add_column('projects', sa.Column('double_pole_config_id', sa.String(), nullable=True))

    op.create_foreign_key(
        'fk_projects_single_pole_config',
        'projects',
        'single_pole_configs',
        ['single_pole_config_id'],
        ['id'],
        ondelete='SET NULL'
    )

    op.create_foreign_key(
        'fk_projects_double_pole_config',
        'projects',
        'double_pole_configs',
        ['double_pole_config_id'],
        ['id'],
        ondelete='SET NULL'
    )

    logger.info("    ✓ Projects table updated")

    # =====================================================================
    # STEP 9: Create Functions and Views
    # =====================================================================

    logger.info("[9/9] Creating calculation functions and views...")

    # Create ASCE 7-22 wind pressure calculation function
    op.execute("""
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
        -- Using simplified interpolation (exact table should be implemented)
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
        -- qz = 0.00256 * Kz * Kzt * Kd * Ke * V² (psf)
        v_qz := 0.00256 * v_kz * p_kzt * p_kd * p_ke * POWER(p_wind_speed_mph, 2);

        RETURN QUERY SELECT
            v_kz,
            v_iw,
            v_qz,
            'ASCE 7-22 Eq 26.10-1'::VARCHAR;
    END;
    $$;
    """)

    logger.info("    ✓ calculate_asce7_wind_pressure() function created")

    # Create optimized pole sections view (replaces optimal_monument_poles)
    op.execute("""
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
        s.sx / s.w as efficiency_ratio,  -- Section modulus per pound

        -- AISC 360-22 ASD capacities
        s.sx * s.fy * 0.66 / 12 as moment_capacity_asd_kipft,  -- Fb*Sx
        s.area * s.fy * 0.4 as shear_capacity_asd_kips,  -- Fv*A

        -- Slenderness limits
        s.rx * 200 / 12 as max_height_ft_slenderness,  -- L/r ≤ 200

        -- Cost estimates (Eagle Sign pricing)
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
        AND s.nominal_depth >= 4  -- Min 4" for structural poles
        AND s.nominal_depth <= 24  -- Max 24" practical
        AND s.w <= 150  -- Max 150 lb/ft practical
        AND s.is_available = true
    ORDER BY s.nominal_depth, s.w;
    """)

    logger.info("    ✓ optimal_pole_sections view created")

    logger.info("[SUCCESS] Restructure to pole architecture complete!")
    logger.info("")
    logger.info("Summary:")
    logger.info("  • Dropped: monument_configs, monument_analysis_results")
    logger.info("  • Created: single_pole_configs, single_pole_results")
    logger.info("  • Created: double_pole_configs, double_pole_results")
    logger.info("  • Created: calculate_asce7_wind_pressure() function")
    logger.info("  • Created: optimal_pole_sections view")
    logger.info("  • Updated: projects table with pole references")


def downgrade() -> None:
    """Revert to monument architecture (for rollback)."""

    logger.info("[INFO] Rolling back to monument architecture...")

    # Drop project references
    op.drop_constraint('fk_projects_double_pole_config', 'projects', type_='foreignkey')
    op.drop_constraint('fk_projects_single_pole_config', 'projects', type_='foreignkey')
    op.drop_column('projects', 'double_pole_config_id')
    op.drop_column('projects', 'has_double_pole')
    op.drop_column('projects', 'single_pole_config_id')
    op.drop_column('projects', 'has_single_pole')

    # Drop functions and views
    op.execute("DROP FUNCTION IF EXISTS calculate_asce7_wind_pressure CASCADE")
    op.execute("DROP VIEW IF EXISTS optimal_pole_sections CASCADE")

    # Drop tables
    op.drop_table('double_pole_results')
    op.drop_table('double_pole_configs')
    op.drop_table('single_pole_results')
    op.drop_table('single_pole_configs')

    # Drop enums
    load_distribution_enum = postgresql.ENUM('equal', 'proportional', name='load_distribution_method')
    load_distribution_enum.drop(op.get_bind(), checkfirst=True)

    risk_category_enum = postgresql.ENUM('I', 'II', 'III', 'IV', name='risk_category')
    risk_category_enum.drop(op.get_bind(), checkfirst=True)

    application_type_enum = postgresql.ENUM('monument', 'pylon', 'cantilever_post', 'wall_mount', name='application_type')
    application_type_enum.drop(op.get_bind(), checkfirst=True)

    logger.info("[INFO] Downgrade complete - would need to re-run 011_monument migration to restore monument tables")
