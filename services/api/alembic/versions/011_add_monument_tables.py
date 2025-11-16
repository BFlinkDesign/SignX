"""Add monument pole tables

Revision ID: 011_monument
Revises: 010_add_cantilever_tables
Create Date: 2025-11-01

Monument sign pole calculations - references AISC foundation catalog.
Supports single-pole monument signs with wind load analysis and foundation design.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '011_monument'
down_revision: Union[str, None] = '010_add_cantilever_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add monument pole configuration and analysis tables."""
    
    # Create exposure category enum for wind analysis
    exposure_enum = postgresql.ENUM(
        'B', 'C', 'D',
        name='exposure_category',
        create_type=True
    )
    exposure_enum.create(op.get_bind(), checkfirst=True)
    
    # Create importance factor enum
    importance_enum = postgresql.ENUM(
        'I', 'II', 'III', 'IV',
        name='importance_factor',
        create_type=True
    )
    importance_enum.create(op.get_bind(), checkfirst=True)
    
    # Monument pole configurations table
    op.create_table(
        'monument_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        
        # Pole geometry
        sa.Column('pole_height_ft', sa.Float(), nullable=False),
        sa.Column('pole_section', sa.String(), nullable=False),  # References aisc_manual_label
        sa.Column('base_plate_size_in', sa.Float()),
        sa.Column('embedment_depth_ft', sa.Float()),
        
        # Sign geometry  
        sa.Column('sign_width_ft', sa.Float(), nullable=False),
        sa.Column('sign_height_ft', sa.Float(), nullable=False),
        sa.Column('sign_area_sqft', sa.Float(), nullable=False),
        sa.Column('sign_thickness_in', sa.Float(), server_default='0.125'),  # 1/8" aluminum typical
        sa.Column('clearance_to_grade_ft', sa.Float(), server_default='8.0'),
        
        # Environmental loads
        sa.Column('basic_wind_speed_mph', sa.Float(), nullable=False),
        sa.Column('exposure_category', exposure_enum, nullable=False),
        sa.Column('importance_factor', importance_enum, server_default='II'),
        sa.Column('gust_factor', sa.Float(), server_default='0.85'),
        sa.Column('force_coefficient', sa.Float(), server_default='1.2'),  # Cf for flat signs
        
        # Site conditions
        sa.Column('ground_snow_load_psf', sa.Float(), server_default='0'),
        sa.Column('ice_thickness_in', sa.Float(), server_default='0'),
        sa.Column('seismic_sds', sa.Float(), server_default='0'),
        sa.Column('soil_bearing_capacity_psf', sa.Float(), server_default='2000'),
        
        # Design preferences
        sa.Column('deflection_limit_ratio', sa.Float(), server_default='200'),  # L/200
        sa.Column('stress_ratio_limit', sa.Float(), server_default='0.9'),
        sa.Column('foundation_type', sa.String(), server_default='spread_footing'),
        
        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pole_section'], ['aisc_shapes_v16.aisc_manual_label'], ondelete='RESTRICT'),
        
        # Constraints
        sa.CheckConstraint('pole_height_ft > 0 AND pole_height_ft <= 50', name='ck_monument_pole_height'),
        sa.CheckConstraint('sign_area_sqft > 0 AND sign_area_sqft <= 500', name='ck_monument_sign_area'),
        sa.CheckConstraint('basic_wind_speed_mph >= 85 AND basic_wind_speed_mph <= 200', name='ck_monument_wind_speed'),
        sa.CheckConstraint('soil_bearing_capacity_psf >= 1000', name='ck_monument_soil_bearing'),
    )
    
    # Monument analysis results table
    op.create_table(
        'monument_analysis_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('config_id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        
        # Wind load analysis
        sa.Column('design_wind_pressure_psf', sa.Float(), nullable=False),
        sa.Column('gust_effect_factor', sa.Float(), nullable=False),
        sa.Column('velocity_pressure_qz_psf', sa.Float(), nullable=False),
        sa.Column('total_wind_force_lbs', sa.Float(), nullable=False),
        sa.Column('wind_moment_at_base_kipft', sa.Float(), nullable=False),
        
        # Additional loads
        sa.Column('dead_load_lbs', sa.Float(), nullable=False),
        sa.Column('snow_load_lbs', sa.Float(), server_default='0'),
        sa.Column('ice_load_lbs', sa.Float(), server_default='0'),
        sa.Column('seismic_force_lbs', sa.Float(), server_default='0'),
        
        # Pole stress analysis
        sa.Column('max_bending_stress_ksi', sa.Float(), nullable=False),
        sa.Column('max_shear_stress_ksi', sa.Float(), nullable=False),
        sa.Column('combined_stress_ratio', sa.Float(), nullable=False),
        sa.Column('max_deflection_in', sa.Float(), nullable=False),
        sa.Column('deflection_ratio', sa.Float(), nullable=False),  # L/deflection
        
        # Foundation analysis
        sa.Column('overturning_moment_kipft', sa.Float(), nullable=False),
        sa.Column('resisting_moment_kipft', sa.Float(), nullable=False),
        sa.Column('overturning_safety_factor', sa.Float(), nullable=False),
        sa.Column('max_soil_pressure_psf', sa.Float(), nullable=False),
        sa.Column('foundation_width_ft', sa.Float()),
        sa.Column('foundation_length_ft', sa.Float()),
        sa.Column('foundation_thickness_ft', sa.Float()),
        
        # Design status
        sa.Column('pole_adequate', sa.Boolean(), nullable=False),
        sa.Column('foundation_adequate', sa.Boolean(), nullable=False),
        sa.Column('overall_passes', sa.Boolean(), nullable=False),
        
        # Warnings and notes
        sa.Column('warnings', postgresql.JSONB, server_default='[]'),
        sa.Column('design_notes', postgresql.JSONB, server_default='[]'),
        sa.Column('assumptions', postgresql.JSONB, server_default='[]'),
        
        # Calculation metadata
        sa.Column('analysis_method', sa.String(), server_default='ASCE7-22'),
        sa.Column('calculation_engine', sa.String(), server_default='APEX_v1.0'),
        sa.Column('content_sha256', sa.String()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['config_id'], ['monument_configs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),
        
        # Constraints
        sa.CheckConstraint('combined_stress_ratio >= 0', name='ck_monument_stress_positive'),
        sa.CheckConstraint('overturning_safety_factor >= 0', name='ck_monument_safety_positive'),
        sa.CheckConstraint('max_soil_pressure_psf >= 0', name='ck_monument_soil_pressure_positive'),
    )
    
    # Create performance indexes
    op.create_index('ix_monument_configs_project_id', 'monument_configs', ['project_id'])
    op.create_index('ix_monument_configs_pole_section', 'monument_configs', ['pole_section'])
    op.create_index('ix_monument_configs_wind_speed', 'monument_configs', ['basic_wind_speed_mph'])
    op.create_index('ix_monument_analysis_project_id', 'monument_analysis_results', ['project_id'])
    op.create_index('ix_monument_analysis_config_id', 'monument_analysis_results', ['config_id'])
    op.create_index('ix_monument_analysis_passes', 'monument_analysis_results', ['overall_passes'])
    op.create_index('ix_monument_analysis_sha256', 'monument_analysis_results', ['content_sha256'])
    
    # Add monument reference to projects table
    op.add_column('projects', sa.Column('has_monument', sa.Boolean(), server_default='false'))
    op.add_column('projects', sa.Column('monument_config_id', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_projects_monument_config',
        'projects',
        'monument_configs',
        ['monument_config_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Create view for optimal monument pole selection
    op.execute("""
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
        s.sx / s.w as efficiency_ratio,  -- Sx per pound
        
        -- Wind capacity estimates (simplified)
        s.sx * 50 * 0.9 / 12 as moment_capacity_kipft,  -- φMn
        
        -- Max recommended height (L/r = 200)
        s.rx * 200 / 12 as max_height_ft,
        
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
        AND s.nominal_depth >= 6  -- Min 6" for monuments
        AND s.nominal_depth <= 16  -- Max 16" practical
        AND s.w <= 100  -- Max 100 lb/ft practical
        AND s.is_available = true
    ORDER BY s.nominal_depth, s.w;
    """)
    
    # Create function for monument pole selection
    op.execute("""
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
        cost_per_ft NUMERIC,
        is_a1085 BOOLEAN,
        status VARCHAR
    )
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_required_sx FLOAT;
        v_max_slenderness FLOAT := 200;  -- L/r <= 200
    BEGIN
        -- Calculate required section modulus
        v_required_sx := p_wind_moment_kipft * 12 / (50 * 0.9);  -- Mu/(Fy*phi)
        
        RETURN QUERY
        SELECT 
            s.aisc_manual_label,
            s.type,
            s.nominal_depth,
            s.w,
            s.sx * 50 * 0.9 / 12 as moment_cap,
            (p_wind_moment_kipft * 12) / (s.sx * 50 * 0.9) as stress_ratio,
            (p_height_ft * 12) / s.rx as slenderness,
            (s.w * 0.90)::NUMERIC(10,2) as cost,
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
            AND s.sx >= v_required_sx * 0.8  -- Allow some margin
            AND s.rx >= (p_height_ft * 12) / v_max_slenderness * 0.9  -- Slenderness check
            AND (NOT p_prefer_a1085 OR s.is_astm_a1085 = true)
            AND s.is_available = true
        ORDER BY 
            CASE WHEN p_prefer_a1085 AND s.is_astm_a1085 THEN 0 ELSE 1 END,
            (p_wind_moment_kipft * 12) / (s.sx * 50 * 0.9),  -- Stress ratio
            s.w  -- Weight
        LIMIT 10;
    END;
    $$;
    """)
    
    logger.info("[OK] Created monument_configs table")
    logger.info("[OK] Created monument_analysis_results table")
    logger.info("[OK] Added monument references to projects table")
    logger.info("[OK] Created optimal_monument_poles view")
    logger.info("[OK] Created select_monument_pole function")
    logger.info("[OK] Created indexes for performance")


def downgrade() -> None:
    """Remove monument pole tables."""
    
    # Drop foreign key from projects
    op.drop_constraint('fk_projects_monument_config', 'projects', type_='foreignkey')
    op.drop_column('projects', 'monument_config_id')
    op.drop_column('projects', 'has_monument')
    
    # Drop function and view
    op.execute("DROP FUNCTION IF EXISTS select_monument_pole CASCADE")
    op.execute("DROP VIEW IF EXISTS optimal_monument_poles CASCADE")
    
    # Drop indexes
    op.drop_index('ix_monument_analysis_sha256', 'monument_analysis_results')
    op.drop_index('ix_monument_analysis_passes', 'monument_analysis_results')
    op.drop_index('ix_monument_analysis_config_id', 'monument_analysis_results')
    op.drop_index('ix_monument_analysis_project_id', 'monument_analysis_results')
    op.drop_index('ix_monument_configs_wind_speed', 'monument_configs')
    op.drop_index('ix_monument_configs_pole_section', 'monument_configs')
    op.drop_index('ix_monument_configs_project_id', 'monument_configs')
    
    # Drop tables
    op.drop_table('monument_analysis_results')
    op.drop_table('monument_configs')
    
    # Drop enums
    importance_enum = postgresql.ENUM('I', 'II', 'III', 'IV', name='importance_factor')
    importance_enum.drop(op.get_bind(), checkfirst=True)
    
    exposure_enum = postgresql.ENUM('B', 'C', 'D', name='exposure_category')
    exposure_enum.drop(op.get_bind(), checkfirst=True)