"""Add monument pole calculation tables

Revision ID: 011_monument_poles
Revises: 010_cantilever
Create Date: 2025-11-01

Monument sign pole structural calculations - references AISC foundation catalog.
Handles single-pole vertical structures from 6'-16' heights typical for Eagle Sign projects.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '011_monument_poles'
down_revision: Union[str, None] = '010_cantilever'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE exposure_category AS ENUM ('B', 'C', 'D');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE risk_category AS ENUM ('I', 'II', 'III', 'IV');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
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

    # Monument Pole Configurations
    op.create_table(
        'monument_configs',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('project_id', sa.String(255), nullable=False),
        sa.Column('config_name', sa.String(255)),
        
        # Sign Geometry
        sa.Column('pole_height_ft', sa.Float, nullable=False),
        sa.Column('sign_area_sqft', sa.Float, nullable=False),
        sa.Column('sign_width_ft', sa.Float, nullable=False),
        sa.Column('sign_height_ft', sa.Float, nullable=False),
        sa.Column('sign_clearance_ft', sa.Float, nullable=False),  # Ground to sign bottom
        sa.Column('sign_thickness_in', sa.Float, nullable=True),
        
        # Wind Parameters (ASCE 7-22)
        sa.Column('wind_speed_mph', sa.Float, nullable=False),
        sa.Column('exposure_category', sa.Enum('B', 'C', 'D', name='exposure_category'), nullable=False),
        sa.Column('risk_category', sa.Enum('I', 'II', 'III', 'IV', name='risk_category'), nullable=False, server_default='II'),
        sa.Column('topographic_factor', sa.Float, nullable=False, server_default='1.0'),
        sa.Column('gust_factor', sa.Float, nullable=False, server_default='0.85'),
        sa.Column('importance_factor', sa.Float, nullable=False, server_default='1.0'),
        
        # Pole Selection (References AISC catalog)
        sa.Column('pole_section', sa.String(50), nullable=False),  # FK to aisc_shapes_v16
        sa.Column('pole_material', sa.String(20), nullable=False, server_default='A500'),  # A500, A1085, etc
        sa.Column('pole_yield_stress_ksi', sa.Float, nullable=False, server_default='50'),
        sa.Column('pole_embedment_ft', sa.Float, nullable=False),
        
        # Base Plate Design
        sa.Column('base_plate_width_in', sa.Float),
        sa.Column('base_plate_length_in', sa.Float),
        sa.Column('base_plate_thickness_in', sa.Float),
        sa.Column('anchor_bolt_diameter_in', sa.Float),
        sa.Column('anchor_bolt_count', sa.Integer),
        sa.Column('anchor_bolt_circle_dia_in', sa.Float),
        
        # Foundation Parameters
        sa.Column('foundation_type', sa.Enum('drilled_shaft', 'spread_footing', 'concrete_pier', 'helical_anchor', name='foundation_type')),
        sa.Column('foundation_diameter_in', sa.Float),
        sa.Column('foundation_depth_ft', sa.Float),
        sa.Column('soil_bearing_capacity_psf', sa.Float),
        sa.Column('soil_passive_pressure_pcf', sa.Float),
        
        # Metadata
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pole_section'], ['aisc_shapes_v16.aisc_manual_label'], ondelete='RESTRICT'),
        
        # Validation constraints
        sa.CheckConstraint('pole_height_ft > 0 AND pole_height_ft <= 30', name='ck_monument_pole_height'),
        sa.CheckConstraint('sign_area_sqft > 0 AND sign_area_sqft <= 500', name='ck_monument_sign_area'),
        sa.CheckConstraint('wind_speed_mph >= 85 AND wind_speed_mph <= 200', name='ck_monument_wind_speed'),
        sa.CheckConstraint('pole_embedment_ft >= 3 AND pole_embedment_ft <= 12', name='ck_monument_embedment'),
        sa.CheckConstraint('pole_yield_stress_ksi >= 36 AND pole_yield_stress_ksi <= 70', name='ck_monument_yield_stress'),
    )

    # Monument Pole Analysis Results
    op.create_table(
        'monument_results',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('config_id', sa.String(255), nullable=False),
        sa.Column('project_id', sa.String(255), nullable=False),
        
        # Wind Load Analysis
        sa.Column('wind_pressure_psf', sa.Float, nullable=False),
        sa.Column('design_wind_force_lbs', sa.Float, nullable=False),
        sa.Column('wind_moment_arm_ft', sa.Float, nullable=False),
        
        # Pole Structural Analysis
        sa.Column('moment_at_base_kipft', sa.Float, nullable=False),
        sa.Column('shear_at_base_kip', sa.Float, nullable=False),
        sa.Column('axial_load_kip', sa.Float, nullable=False),
        sa.Column('torsion_kipft', sa.Float, nullable=False, server_default='0'),
        
        # Stress Analysis
        sa.Column('bending_stress_ksi', sa.Float, nullable=False),
        sa.Column('allowable_bending_ksi', sa.Float, nullable=False),
        sa.Column('stress_ratio', sa.Float, nullable=False),
        sa.Column('shear_stress_ksi', sa.Float),
        sa.Column('combined_stress_ratio', sa.Float),
        
        # Deflection Analysis
        sa.Column('tip_deflection_in', sa.Float, nullable=False),
        sa.Column('deflection_ratio', sa.Float, nullable=False),  # Deflection / Height
        sa.Column('max_deflection_limit_in', sa.Float, nullable=False),
        
        # Foundation Analysis
        sa.Column('overturning_moment_kipft', sa.Float, nullable=False),
        sa.Column('resisting_moment_kipft', sa.Float, nullable=False),
        sa.Column('overturning_safety_factor', sa.Float, nullable=False),
        sa.Column('soil_bearing_pressure_psf', sa.Float),
        sa.Column('bearing_safety_factor', sa.Float),
        
        # Base Plate Analysis
        sa.Column('base_plate_bending_stress_ksi', sa.Float),
        sa.Column('anchor_bolt_tension_kip', sa.Float),
        sa.Column('anchor_bolt_utilization', sa.Float),
        
        # Code Compliance
        sa.Column('passes_strength', sa.Boolean, nullable=False),
        sa.Column('passes_deflection', sa.Boolean, nullable=False),
        sa.Column('passes_overturning', sa.Boolean, nullable=False),
        sa.Column('passes_bearing', sa.Boolean, nullable=False),
        sa.Column('passes_all_checks', sa.Boolean, nullable=False),
        
        # Fatigue (if applicable)
        sa.Column('fatigue_cycles', sa.Integer),
        sa.Column('fatigue_stress_range_ksi', sa.Float),
        sa.Column('fatigue_category', sa.String(10)),
        
        # Metadata
        sa.Column('analysis_timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('analysis_version', sa.String(20)),
        sa.Column('warnings', sa.JSON),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['config_id'], ['monument_configs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),
        
        sa.CheckConstraint('stress_ratio >= 0', name='ck_monument_stress_positive'),
        sa.CheckConstraint('overturning_safety_factor >= 0', name='ck_monument_overturning_positive'),
    )

    # Create indexes for performance
    op.create_index('idx_monument_configs_project', 'monument_configs', ['project_id'])
    op.create_index('idx_monument_configs_pole', 'monument_configs', ['pole_section'])
    op.create_index('idx_monument_results_config', 'monument_results', ['config_id'])
    op.create_index('idx_monument_results_project', 'monument_results', ['project_id'])
    op.create_index('idx_monument_results_passes', 'monument_results', ['passes_all_checks'])


def downgrade() -> None:
    op.drop_index('idx_monument_results_passes')
    op.drop_index('idx_monument_results_project')
    op.drop_index('idx_monument_results_config')
    op.drop_index('idx_monument_configs_pole')
    op.drop_index('idx_monument_configs_project')
    
    op.drop_table('monument_results')
    op.drop_table('monument_configs')
    
    op.execute('DROP TYPE IF EXISTS foundation_type')
    op.execute('DROP TYPE IF EXISTS risk_category')
    op.execute('DROP TYPE IF EXISTS exposure_category')
