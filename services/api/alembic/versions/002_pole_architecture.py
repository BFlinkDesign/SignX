"""Pole architecture - single and double pole structural design

Revision ID: 002_pole_architecture
Revises: 001_foundation
Create Date: 2025-11-01 13:00:00

Implements single-pole and double-pole sign structural design framework:
- Single pole configurations (monuments, pylons, cantilever posts)
- Double pole configurations (for larger signs)
- Cantilever arm configurations
- Full ASCE 7-22 / IBC 2024 compliance
- Analysis results tables with code compliance checks
- References AISC shapes foundation catalog

SOURCES (from 012_restructure_to_pole_architecture):
- Single pole tables (configs and results)
- Double pole tables (configs and results)
- Cantilever tables (from 010_cantilever)
- Application type and load distribution enums
- Pole-optimized views and functions
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "002_pole_architecture"
down_revision: Union[str, None] = "001_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create pole architecture tables."""

    logger.info("[INFO] Creating pole architecture schema...")

    # =========================================================================
    # PART 1: CREATE ENUMS
    # =========================================================================

    logger.info("[1/8] Creating enums for pole architecture...")

    # Application type enum (universal framework)
    application_type_enum = postgresql.ENUM(
        'monument', 'pylon', 'cantilever_post', 'wall_mount',
        name='application_type',
        create_type=True
    )
    application_type_enum.create(op.get_bind(), checkfirst=True)

    # Load distribution method for double-pole
    load_distribution_enum = postgresql.ENUM(
        'equal', 'proportional',
        name='load_distribution_method',
        create_type=True
    )
    load_distribution_enum.create(op.get_bind(), checkfirst=True)

    # Cantilever type enum
    cantilever_type_enum = postgresql.ENUM(
        'single', 'double', 'truss', 'cable',
        name='cantilever_type',
        create_type=True
    )
    cantilever_type_enum.create(op.get_bind(), checkfirst=True)

    # Connection type enum
    connection_type_enum = postgresql.ENUM(
        'bolted_flange', 'welded', 'pinned', 'clamped',
        name='connection_type',
        create_type=True
    )
    connection_type_enum.create(op.get_bind(), checkfirst=True)

    logger.info("    ✓ Enums created")

    # =========================================================================
    # PART 2: SINGLE POLE TABLES
    # =========================================================================

    logger.info("[2/8] Creating single_pole_configs table...")

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
        sa.Column('sign_weight_psf', sa.Float(), server_default='3.0'),
        sa.Column('clearance_to_grade_ft', sa.Float(), server_default='8.0'),

        # Wind loads per ASCE 7-22 Chapter 26
        sa.Column('basic_wind_speed_mph', sa.Float(), nullable=False),
        sa.Column('risk_category', postgresql.ENUM('I', 'II', 'III', 'IV', name='risk_category'), server_default='II'),
        sa.Column('exposure_category', postgresql.ENUM('B', 'C', 'D', name='exposure_category'), nullable=False),
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

        # Additional loads
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
        sa.CheckConstraint('pole_height_ft > 0 AND pole_height_ft <= 100', name='ck_single_pole_height'),
        sa.CheckConstraint('embedment_depth_ft >= 3 AND embedment_depth_ft <= 25', name='ck_single_embedment'),
        sa.CheckConstraint('sign_area_sqft > 0 AND sign_area_sqft <= 1000', name='ck_single_sign_area'),
        sa.CheckConstraint('basic_wind_speed_mph >= 85 AND basic_wind_speed_mph <= 200', name='ck_single_wind_speed'),
        sa.CheckConstraint('topographic_factor_kzt >= 1.0 AND topographic_factor_kzt <= 3.0', name='ck_single_kzt'),
        sa.CheckConstraint('wind_directionality_factor_kd > 0 AND wind_directionality_factor_kd <= 1.0', name='ck_single_kd'),
        sa.CheckConstraint('soil_bearing_capacity_psf >= 1000', name='ck_single_soil_bearing'),
    )

    logger.info("    ✓ single_pole_configs table created")

    logger.info("[3/8] Creating single_pole_results table...")

    op.create_table(
        'single_pole_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('config_id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),

        # ASCE 7-22 Wind Load Analysis
        sa.Column('velocity_pressure_exposure_coeff_kz', sa.Float(), nullable=False),
        sa.Column('wind_importance_factor_iw', sa.Float(), nullable=False),
        sa.Column('velocity_pressure_qz_psf', sa.Float(), nullable=False),
        sa.Column('design_wind_pressure_psf', sa.Float(), nullable=False),
        sa.Column('total_wind_force_lbs', sa.Float(), nullable=False),
        sa.Column('wind_moment_at_base_kipft', sa.Float(), nullable=False),

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

        # Foundation analysis
        sa.Column('overturning_moment_kipft', sa.Float(), nullable=False),
        sa.Column('resisting_moment_kipft', sa.Float(), nullable=False),
        sa.Column('safety_factor_overturning', sa.Float(), nullable=False),
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
        sa.ForeignKeyConstraint(['config_id'], ['single_pole_configs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),

        # Constraints
        sa.CheckConstraint('velocity_pressure_qz_psf >= 0', name='ck_single_qz_positive'),
        sa.CheckConstraint('bending_stress_ratio >= 0', name='ck_single_bending_ratio'),
        sa.CheckConstraint('safety_factor_overturning >= 0', name='ck_single_overturning_sf'),
    )

    logger.info("    ✓ single_pole_results table created")

    # =========================================================================
    # PART 3: DOUBLE POLE TABLES
    # =========================================================================

    logger.info("[4/8] Creating double_pole_configs table...")

    op.create_table(
        'double_pole_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),

        # Application classification
        sa.Column('application_type', application_type_enum, server_default='monument'),

        # Pole geometry
        sa.Column('pole_height_ft', sa.Float(), nullable=False),
        sa.Column('pole_section', sa.String(), nullable=False),
        sa.Column('pole_spacing_ft', sa.Float(), nullable=False),
        sa.Column('embedment_depth_ft', sa.Float(), nullable=False),
        sa.Column('base_plate_size_in', sa.Float()),

        # Sign geometry
        sa.Column('sign_width_ft', sa.Float(), nullable=False),
        sa.Column('sign_height_ft', sa.Float(), nullable=False),
        sa.Column('sign_area_sqft', sa.Float(), nullable=False),
        sa.Column('sign_thickness_in', sa.Float(), server_default='0.125'),
        sa.Column('sign_weight_psf', sa.Float(), server_default='3.0'),
        sa.Column('clearance_to_grade_ft', sa.Float(), server_default='8.0'),

        # Load distribution
        sa.Column('load_distribution_method', load_distribution_enum, server_default='equal'),
        sa.Column('lateral_bracing_required', sa.Boolean(), server_default='false'),
        sa.Column('differential_settlement_limit_in', sa.Float(), server_default='0.5'),

        # Wind loads per ASCE 7-22
        sa.Column('basic_wind_speed_mph', sa.Float(), nullable=False),
        sa.Column('risk_category', postgresql.ENUM('I', 'II', 'III', 'IV', name='risk_category'), server_default='II'),
        sa.Column('exposure_category', postgresql.ENUM('B', 'C', 'D', name='exposure_category'), nullable=False),
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

        # Additional loads
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

    logger.info("[5/8] Creating double_pole_results table...")

    op.create_table(
        'double_pole_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('config_id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),

        # Wind load analysis
        sa.Column('velocity_pressure_exposure_coeff_kz', sa.Float(), nullable=False),
        sa.Column('wind_importance_factor_iw', sa.Float(), nullable=False),
        sa.Column('velocity_pressure_qz_psf', sa.Float(), nullable=False),
        sa.Column('design_wind_pressure_psf', sa.Float(), nullable=False),
        sa.Column('total_wind_force_lbs', sa.Float(), nullable=False),
        sa.Column('wind_moment_total_kipft', sa.Float(), nullable=False),

        # Load distribution
        sa.Column('load_per_pole_lbs', sa.Float(), nullable=False),
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

    # =========================================================================
    # PART 4: CANTILEVER TABLES
    # =========================================================================

    logger.info("[6/8] Creating cantilever tables...")

    op.create_table(
        'cantilever_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('cantilever_type', cantilever_type_enum, nullable=False),
        sa.Column('arm_length_ft', sa.Float(), nullable=False),
        sa.Column('arm_angle_deg', sa.Float(), nullable=False, server_default='0'),
        sa.Column('arm_section', sa.String(), nullable=False),
        sa.Column('connection_type', connection_type_enum, nullable=False),
        sa.Column('num_arms', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('arm_spacing_ft', sa.Float(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),
        sa.CheckConstraint('arm_length_ft > 0 AND arm_length_ft <= 30', name='ck_cantilever_arm_length'),
        sa.CheckConstraint('arm_angle_deg >= -15 AND arm_angle_deg <= 15', name='ck_cantilever_arm_angle'),
        sa.CheckConstraint('num_arms >= 1 AND num_arms <= 4', name='ck_cantilever_num_arms'),
    )

    op.create_table(
        'cantilever_analysis_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('config_id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),

        # Moments and forces
        sa.Column('moment_x_kipft', sa.Float(), nullable=False),
        sa.Column('moment_y_kipft', sa.Float(), nullable=False),
        sa.Column('moment_z_kipft', sa.Float(), nullable=False),
        sa.Column('total_moment_kipft', sa.Float(), nullable=False),
        sa.Column('shear_x_kip', sa.Float(), nullable=False),
        sa.Column('shear_y_kip', sa.Float(), nullable=False),
        sa.Column('axial_kip', sa.Float(), nullable=False),

        # Arm stresses
        sa.Column('arm_bending_stress_ksi', sa.Float(), nullable=False),
        sa.Column('arm_shear_stress_ksi', sa.Float(), nullable=False),
        sa.Column('arm_deflection_in', sa.Float(), nullable=False),
        sa.Column('arm_rotation_deg', sa.Float(), nullable=False),

        # Connection forces
        sa.Column('connection_tension_kip', sa.Float(), nullable=False),
        sa.Column('connection_shear_kip', sa.Float(), nullable=False),
        sa.Column('connection_moment_kipft', sa.Float(), nullable=False),

        # Design ratios
        sa.Column('arm_stress_ratio', sa.Float(), nullable=False),
        sa.Column('connection_ratio', sa.Float(), nullable=False),
        sa.Column('deflection_ratio', sa.Float(), nullable=False),

        # Fatigue analysis
        sa.Column('fatigue_cycles', sa.BigInteger(), server_default='0'),
        sa.Column('fatigue_factor', sa.Float(), server_default='1.0'),

        # Metadata
        sa.Column('warnings', postgresql.JSONB, server_default='[]'),
        sa.Column('assumptions', postgresql.JSONB, server_default='[]'),
        sa.Column('analysis_params', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('content_sha256', sa.String()),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['config_id'], ['cantilever_configs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),
        sa.CheckConstraint('arm_stress_ratio >= 0', name='ck_cantilever_stress_positive'),
        sa.CheckConstraint('fatigue_factor >= 0 AND fatigue_factor <= 1', name='ck_cantilever_fatigue_range'),
    )

    logger.info("    ✓ Cantilever tables created")

    # =========================================================================
    # PART 5: CREATE INDEXES
    # =========================================================================

    logger.info("[7/8] Creating performance indexes...")

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

    # Cantilever indexes
    op.create_index('ix_cantilever_configs_project_id', 'cantilever_configs', ['project_id'])
    op.create_index('ix_cantilever_configs_cantilever_type', 'cantilever_configs', ['cantilever_type'])
    op.create_index('ix_cantilever_analysis_project_id', 'cantilever_analysis_results', ['project_id'])
    op.create_index('ix_cantilever_analysis_config_id', 'cantilever_analysis_results', ['config_id'])
    op.create_index('ix_cantilever_analysis_sha256', 'cantilever_analysis_results', ['content_sha256'])

    logger.info("    ✓ Indexes created")

    # =========================================================================
    # PART 6: UPDATE PROJECTS TABLE
    # =========================================================================

    logger.info("[8/8] Updating projects table references...")

    op.add_column('projects', sa.Column('has_single_pole', sa.Boolean(), server_default='false'))
    op.add_column('projects', sa.Column('single_pole_config_id', sa.String(), nullable=True))
    op.add_column('projects', sa.Column('has_double_pole', sa.Boolean(), server_default='false'))
    op.add_column('projects', sa.Column('double_pole_config_id', sa.String(), nullable=True))
    op.add_column('projects', sa.Column('has_cantilever', sa.Boolean(), server_default='false'))
    op.add_column('projects', sa.Column('cantilever_config_id', sa.String(), nullable=True))

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

    op.create_foreign_key(
        'fk_projects_cantilever_config',
        'projects',
        'cantilever_configs',
        ['cantilever_config_id'],
        ['id'],
        ondelete='SET NULL'
    )

    logger.info("    ✓ Projects table updated")

    # Create optimized pole sections view
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
        s.fy_ksi as yield_strength_ksi,
        s.is_astm_a1085,

        -- Performance metrics
        s.sx / s.w as efficiency_ratio,

        -- AISC 360-22 ASD capacities
        s.sx * s.fy_ksi * 0.66 / 12 as moment_capacity_asd_kipft,
        s.area * s.fy_ksi * 0.4 as shear_capacity_asd_kips,

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
    ORDER BY s.nominal_depth, s.w
    """)

    logger.info("")
    logger.info("[SUCCESS] Pole architecture complete!")
    logger.info("")
    logger.info("Summary:")
    logger.info("  • Single pole configs and results tables")
    logger.info("  • Double pole configs and results tables")
    logger.info("  • Cantilever arm configs and analysis tables")
    logger.info("  • optimal_pole_sections view")
    logger.info("  • Projects table updated with pole references")


def downgrade() -> None:
    """Remove pole architecture tables."""

    logger.info("[INFO] Rolling back pole architecture...")

    # Drop project references
    op.drop_constraint('fk_projects_cantilever_config', 'projects', type_='foreignkey')
    op.drop_constraint('fk_projects_double_pole_config', 'projects', type_='foreignkey')
    op.drop_constraint('fk_projects_single_pole_config', 'projects', type_='foreignkey')
    op.drop_column('projects', 'cantilever_config_id')
    op.drop_column('projects', 'has_cantilever')
    op.drop_column('projects', 'double_pole_config_id')
    op.drop_column('projects', 'has_double_pole')
    op.drop_column('projects', 'single_pole_config_id')
    op.drop_column('projects', 'has_single_pole')

    # Drop view
    op.execute("DROP VIEW IF EXISTS optimal_pole_sections CASCADE")

    # Drop tables
    op.drop_table('cantilever_analysis_results')
    op.drop_table('cantilever_configs')
    op.drop_table('double_pole_results')
    op.drop_table('double_pole_configs')
    op.drop_table('single_pole_results')
    op.drop_table('single_pole_configs')

    # Drop enums
    connection_type_enum = postgresql.ENUM('bolted_flange', 'welded', 'pinned', 'clamped', name='connection_type')
    connection_type_enum.drop(op.get_bind(), checkfirst=True)

    cantilever_type_enum = postgresql.ENUM('single', 'double', 'truss', 'cable', name='cantilever_type')
    cantilever_type_enum.drop(op.get_bind(), checkfirst=True)

    load_distribution_enum = postgresql.ENUM('equal', 'proportional', name='load_distribution_method')
    load_distribution_enum.drop(op.get_bind(), checkfirst=True)

    application_type_enum = postgresql.ENUM('monument', 'pylon', 'cantilever_post', 'wall_mount', name='application_type')
    application_type_enum.drop(op.get_bind(), checkfirst=True)

    logger.info("[INFO] Downgrade complete")
