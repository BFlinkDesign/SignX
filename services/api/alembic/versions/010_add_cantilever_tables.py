"""Add cantilever sign configuration tables

Revision ID: 010_cantilever
Revises: 001c_sign_views
Create Date: 2025-11-01

Adds tables for cantilever sign configurations and analysis results.
References the AISC foundation catalog for structural sections.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '010_cantilever'
down_revision: Union[str, None] = '001c_sign_views'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cantilever configuration tables."""
    
    # Create enum for cantilever types
    cantilever_type_enum = postgresql.ENUM(
        'single', 'double', 'truss', 'cable',
        name='cantilever_type',
        create_type=True
    )
    cantilever_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Create enum for connection types
    connection_type_enum = postgresql.ENUM(
        'bolted_flange', 'welded', 'pinned', 'clamped',
        name='connection_type',
        create_type=True
    )
    connection_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Create cantilever_configs table
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
    
    # Create cantilever_analysis_results table
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
    
    # Create indexes
    op.create_index('ix_cantilever_configs_project_id', 'cantilever_configs', ['project_id'])
    op.create_index('ix_cantilever_configs_cantilever_type', 'cantilever_configs', ['cantilever_type'])
    op.create_index('ix_cantilever_analysis_project_id', 'cantilever_analysis_results', ['project_id'])
    op.create_index('ix_cantilever_analysis_config_id', 'cantilever_analysis_results', ['config_id'])
    op.create_index('ix_cantilever_analysis_sha256', 'cantilever_analysis_results', ['content_sha256'])
    
    # Add cantilever reference to projects table
    op.add_column('projects', sa.Column('has_cantilever', sa.Boolean(), server_default='false'))
    op.add_column('projects', sa.Column('cantilever_config_id', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_projects_cantilever_config',
        'projects',
        'cantilever_configs',
        ['cantilever_config_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Create cantilever_sections catalog table for standard sections
    op.create_table(
        'cantilever_sections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('designation', sa.String(), nullable=False, unique=True),
        sa.Column('shape_type', sa.String(), nullable=False),  # HSS, PIPE, W-SHAPE
        sa.Column('weight_plf', sa.Float(), nullable=False),
        sa.Column('area_in2', sa.Float(), nullable=False),
        sa.Column('ix_in4', sa.Float(), nullable=False),
        sa.Column('sx_in3', sa.Float(), nullable=False),
        sa.Column('rx_in', sa.Float(), nullable=False),
        sa.Column('iy_in4', sa.Float()),
        sa.Column('sy_in3', sa.Float()),
        sa.Column('ry_in', sa.Float()),
        sa.Column('j_in4', sa.Float()),  # Torsional constant
        sa.Column('fy_ksi', sa.Float(), server_default='50'),
        sa.Column('max_span_ft', sa.Float()),  # Maximum recommended cantilever length
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Insert common cantilever sections
    op.execute("""
        INSERT INTO cantilever_sections 
        (designation, shape_type, weight_plf, area_in2, ix_in4, sx_in3, rx_in, j_in4, max_span_ft)
        VALUES 
        ('HSS6x6x3/8', 'HSS', 19.08, 5.59, 39.0, 13.0, 2.64, 60.8, 12.0),
        ('HSS8x8x3/8', 'HSS', 25.78, 7.58, 94.5, 23.6, 3.53, 147.0, 18.0),
        ('HSS8x8x1/2', 'HSS', 33.68, 9.86, 120.0, 30.1, 3.49, 187.0, 20.0),
        ('HSS10x10x3/8', 'HSS', 32.58, 9.58, 192.0, 38.5, 4.48, 300.0, 22.0),
        ('HSS10x10x1/2', 'HSS', 42.68, 12.5, 246.0, 49.3, 4.44, 385.0, 25.0),
        ('HSS12x12x1/2', 'HSS', 52.08, 15.3, 430.0, 71.7, 5.30, 673.0, 30.0),
        ('PIPE8STD', 'PIPE', 28.55, 8.40, 72.5, 16.8, 2.94, 145.0, 15.0),
        ('PIPE10STD', 'PIPE', 40.48, 11.9, 161.0, 29.9, 3.67, 321.0, 20.0),
        ('PIPE12STD', 'PIPE', 49.56, 14.6, 279.0, 43.8, 4.38, 558.0, 25.0)
    """)
    
    logger.info("✓ Created cantilever_configs table")
    logger.info("✓ Created cantilever_analysis_results table")
    logger.info("✓ Created cantilever_sections catalog table")
    logger.info("✓ Added cantilever references to projects table")
    logger.info("✓ Added indexes for performance")


def downgrade() -> None:
    """Remove cantilever configuration tables."""
    
    # Remove foreign key from projects
    op.drop_constraint('fk_projects_cantilever_config', 'projects', type_='foreignkey')
    op.drop_column('projects', 'cantilever_config_id')
    op.drop_column('projects', 'has_cantilever')
    
    # Drop indexes
    op.drop_index('ix_cantilever_analysis_sha256', 'cantilever_analysis_results')
    op.drop_index('ix_cantilever_analysis_config_id', 'cantilever_analysis_results')
    op.drop_index('ix_cantilever_analysis_project_id', 'cantilever_analysis_results')
    op.drop_index('ix_cantilever_configs_cantilever_type', 'cantilever_configs')
    op.drop_index('ix_cantilever_configs_project_id', 'cantilever_configs')
    
    # Drop tables
    op.drop_table('cantilever_sections')
    op.drop_table('cantilever_analysis_results')
    op.drop_table('cantilever_configs')
    
    # Drop enums
    cantilever_type_enum = postgresql.ENUM('single', 'double', 'truss', 'cable', name='cantilever_type')
    cantilever_type_enum.drop(op.get_bind(), checkfirst=True)
    
    connection_type_enum = postgresql.ENUM('bolted_flange', 'welded', 'pinned', 'clamped', name='connection_type')
    connection_type_enum.drop(op.get_bind(), checkfirst=True)