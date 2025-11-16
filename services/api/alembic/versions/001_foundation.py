"""Foundation schema - consolidated base migration

Revision ID: 001_foundation
Revises:
Create Date: 2025-11-01 12:00:00

This consolidated migration contains:
- Projects tables (projects, project_payloads, project_events)
- AISC Shapes Database v16.0 (W, C, MC, L, WT, HSS, PIPE sections)
- Material cost tracking (steel, aluminum, concrete, coatings)
- Sign-specific database views and optimization functions
- Calibration constants and pricing configs
- Material catalog and code references
- Audit logging, RBAC, compliance, and file management
- Performance indexes and materialized views
- PostgreSQL function: calculate_asce7_wind_pressure()

SOURCES (squashed from):
- 001_initial_projects_schema
- 002_add_enums_and_indexes
- 003_add_calib_pricing_tables
- 004_seed_calib_pricing_data
- 005_performance_indexes_query_timeout
- 006_envelope_support_indexes
- 007_add_partitioning
- 008_add_pole_sections_table (DEPRECATED - replaced by aisc_shapes_v16)
- 009_add_audit_rbac_compliance_tables
- 001a_create_aisc_foundation
- 001b_create_material_costs
- 001c_create_sign_views
"""
from __future__ import annotations

from typing import Sequence, Union
from datetime import date

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import logging

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "001_foundation"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create foundation schema with all base tables."""

    logger.info("[INFO] Creating foundation schema...")

    # =========================================================================
    # PART 1: PROJECTS TABLES
    # =========================================================================

    logger.info("[1/12] Creating projects core tables...")

    # Projects table
    op.create_table(
        "projects",
        sa.Column("project_id", sa.String(255), primary_key=True),
        sa.Column("account_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("customer", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("site_name", sa.String(255), nullable=True),
        sa.Column("street", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("etag", sa.String(64), nullable=True),
        # Envelope support columns (from 006)
        sa.Column("constants_version", sa.String(500), nullable=True),
        sa.Column("content_sha256", sa.String(64), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
    )

    # Add CHECK constraints for status values
    op.execute("""
        ALTER TABLE projects ADD CONSTRAINT projects_status_check
        CHECK (status IN ('draft','estimating','submitted','accepted','rejected'))
    """)

    op.execute("""
        ALTER TABLE projects ADD CONSTRAINT chk_confidence
        CHECK (confidence >= 0.0 AND confidence <= 1.0 OR confidence IS NULL)
    """)

    # Project payloads table
    op.create_table(
        "project_payloads",
        sa.Column("payload_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.String(255), nullable=False, index=True),
        sa.Column("module", sa.String(255), nullable=False),
        sa.Column("config", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("files", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("cost_snapshot", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Add CHECK constraint for module
    op.execute("""
        ALTER TABLE project_payloads ADD CONSTRAINT project_payloads_module_check
        CHECK (module IN ('signage.single_pole.direct_burial','signage.single_pole.base_plate','signage.two_pole.direct_burial'))
    """)

    # Project events table
    op.create_table(
        "project_events",
        sa.Column("event_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.String(255), nullable=False, index=True),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("data", postgresql.JSON(astext_type=sa.Text()), nullable=False),
    )

    # Foreign key constraints
    op.execute("""
        ALTER TABLE project_payloads
        ADD CONSTRAINT fk_payloads_project_id
        FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
    """)

    op.execute("""
        ALTER TABLE project_events
        ADD CONSTRAINT fk_events_project_id
        FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
    """)

    logger.info("    ✓ Projects tables created")

    # =========================================================================
    # PART 2: PERFORMANCE INDEXES (from 002, 005, 006)
    # =========================================================================

    logger.info("[2/12] Creating performance indexes...")

    # Projects indexes
    op.create_index("ix_projects_status_created", "projects", ["status", sa.text("created_at DESC")])
    op.create_index("ix_projects_account_status", "projects", ["account_id", "status"])
    op.create_index("ix_projects_account_status_created", "projects", ["account_id", "status", sa.text("created_at DESC")])
    op.create_index("ix_projects_content_sha", "projects", ["content_sha256"])
    op.create_index("ix_projects_etag", "projects", ["etag"])

    # Partial indexes
    op.execute("""
        CREATE INDEX ix_projects_non_draft_status
        ON projects(status) WHERE status != 'draft'
    """)

    op.execute("""
        CREATE INDEX ix_projects_active_status
        ON projects(status, created_at DESC)
        WHERE status IN ('draft', 'estimating')
    """)

    op.execute("""
        CREATE UNIQUE INDEX uq_projects_etag ON projects(etag)
        WHERE etag IS NOT NULL
    """)

    # Project payloads indexes
    op.create_index("ix_project_payloads_project_module_created", "project_payloads",
                    ["project_id", "module", sa.text("created_at DESC")])
    op.create_index("ix_payloads_project_created", "project_payloads",
                    ["project_id", sa.text("created_at DESC")])
    op.create_index("ix_payloads_project_sha256", "project_payloads",
                    ["project_id", "sha256"])
    op.create_index("ix_payloads_project_module", "project_payloads",
                    ["project_id", "module"])

    # Project events indexes
    op.create_index("ix_project_events_event_type", "project_events", ["event_type"])
    op.create_index("ix_events_project_timestamp", "project_events",
                    ["project_id", sa.text("timestamp DESC")])

    logger.info("    ✓ Performance indexes created")

    # =========================================================================
    # PART 3: CALIBRATION & PRICING TABLES (from 003, 004)
    # =========================================================================

    logger.info("[3/12] Creating calibration and pricing tables...")

    # Calibration constants table
    op.create_table(
        "calibration_constants",
        sa.Column("constant_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_calib_name_version", "calibration_constants", ["name", "version"], unique=True)
    op.create_index("ix_calib_version", "calibration_constants", ["version"])

    # Pricing table
    op.create_table(
        "pricing_configs",
        sa.Column("price_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("item_code", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("price_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_pricing_item_version", "pricing_configs", ["item_code", "version"], unique=True)
    op.create_index("ix_pricing_effective", "pricing_configs", ["effective_from", "effective_to"])

    # Material catalog stubs
    op.create_table(
        "material_catalog",
        sa.Column("material_id", sa.String(50), primary_key=True),
        sa.Column("standard", sa.String(50), nullable=False),
        sa.Column("grade", sa.String(50), nullable=False),
        sa.Column("shape", sa.String(50), nullable=False),
        sa.Column("properties", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("dimensions", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("source_table", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_mat_standard_grade", "material_catalog", ["standard", "grade"])
    op.create_index("ix_mat_shape", "material_catalog", ["shape"])

    # Engineering code references table
    op.create_table(
        "code_references",
        sa.Column("ref_id", sa.String(100), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("section", sa.String(100), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("formula", sa.Text(), nullable=True),
        sa.Column("application", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_code_section", "code_references", ["code", "section"])

    # Seed calibration constants
    op.execute("""
        INSERT INTO calibration_constants (name, version, value, unit, description, source, effective_from) VALUES
        ('K_FACTOR', 'footing_v1', 0.15, 'unitless', 'Calibrated K factor for direct burial depth calculation', 'ASCE 7-16 + calibration', '2025-01-01'),
        ('SOIL_BEARING_DEFAULT', 'footing_v1', 3000.0, 'psf', 'Default allowable soil bearing pressure', 'ASCE 7-16 12.7.1', '2025-01-01'),
        ('CONCRETE_DENSITY', 'material_v1', 150.0, 'pcf', 'Normal weight concrete density', 'ACI 318', '2025-01-01'),
        ('STEEL_YIELD_A36', 'material_v1', 36.0, 'ksi', 'A36 steel yield strength', 'AISC 360', '2025-01-01'),
        ('STEEL_YIELD_A572', 'material_v1', 50.0, 'ksi', 'A572 Grade 50 yield strength', 'AISC 360', '2025-01-01'),
        ('STEEL_MODULUS', 'material_v1', 29000.0, 'ksi', 'Steel modulus of elasticity', 'AISC 360', '2025-01-01')
        ON CONFLICT (name, version) DO NOTHING
    """)

    # Seed pricing configurations
    op.execute("""
        INSERT INTO pricing_configs (item_code, version, price_usd, description, category, effective_from) VALUES
        ('base_est', 'v1', 150.00, 'Base estimation service', 'base', '2025-01-01'),
        ('calc_packet', 'v1', 35.00, 'Calculation packet add-on', 'addon', '2025-01-01'),
        ('hard_copies', 'v1', 50.00, 'Hard copies shipping', 'addon', '2025-01-01'),
        ('expedited', 'v1', 100.00, 'Expedited processing (3-day)', 'addon', '2025-01-01'),
        ('permit_pkg', 'v1', 250.00, 'Permit package preparation', 'permit', '2025-01-01')
        ON CONFLICT (item_code, version) DO NOTHING
    """)

    # Seed material catalog stubs
    op.execute("""
        INSERT INTO material_catalog (material_id, standard, grade, shape, properties, dimensions, source_table) VALUES
        ('AISC_99_A36', 'AISC', 'A36', 'HSS',
         '{"fy_ksi": 36.0, "E_ksi": 29000.0, "G_ksi": 11200.0, "nu": 0.30}',
         '{"A_in2": 1.54, "Ix_in4": 0.811, "Iy_in4": 0.811, "r_in": 0.726}',
         'AISC Manual Table 1-12'),
        ('AISC_99_A572', 'AISC', 'A572_50', 'HSS',
         '{"fy_ksi": 50.0, "E_ksi": 29000.0, "G_ksi": 11200.0, "nu": 0.30}',
         '{"A_in2": 2.65, "Ix_in4": 1.39, "Iy_in4": 1.39, "r_in": 0.724}',
         'AISC Manual Table 1-12'),
        ('ASTM_A53_A36', 'ASTM', 'A36', 'Pipe',
         '{"fy_ksi": 36.0, "E_ksi": 29000.0, "t_min_in": 0.237}',
         '{"OD_in": 3.5, "A_in2": 2.43, "I_in4": 3.02, "r_in": 1.114}',
         'ASTM A53 Grade A'),
        ('ASTM_A53_A53B', 'ASTM', 'A53_B', 'Pipe',
         '{"fy_ksi": 35.0, "E_ksi": 29000.0, "t_min_in": 0.237}',
         '{"OD_in": 4.0, "A_in2": 2.81, "I_in4": 4.79, "r_in": 1.305}',
         'ASTM A53 Grade B')
        ON CONFLICT (material_id) DO NOTHING
    """)

    # Seed code references
    op.execute("""
        INSERT INTO code_references (ref_id, code, section, title, formula, application) VALUES
        ('ASCE_7_16_26_10_1', 'ASCE 7-16', '26.10.1', 'Basic wind speed V mapping',
         '{"type": "lookup_table", "ref": "Figure 26.5-1"}',
         'Wind speed map determination by location'),
        ('ASCE_7_16_29_5', 'ASCE 7-16', '29.5', 'Sign wind loads',
         '{"type": "formula", "expr": "qp * GCp"}',
         'Net design wind pressure for signs'),
        ('AISC_360_F2_2', 'AISC 360', 'F2.2', 'Nominal flexural strength Mn',
         '{"type": "formula", "expr": "Mp = Fy * Zx"}',
         'Plastic moment for compact sections'),
        ('ACI_318_22_2_2', 'ACI 318-19', '22.2.2', 'Nominal shear strength',
         '{"type": "formula", "expr": "Vn = Vc + Vs"}',
         'Shear strength for concrete members'),
        ('BROMS_1964', 'Broms', '1964', 'Lateral capacity of piles',
         '{"type": "empirical", "ref": "soil-pile interaction"}',
         'Direct burial foundation design')
        ON CONFLICT (ref_id) DO NOTHING
    """)

    logger.info("    ✓ Calibration and pricing tables created with seed data")

    # =========================================================================
    # PART 4: PARTITIONING INFRASTRUCTURE (from 007)
    # =========================================================================

    logger.info("[4/12] Creating partitioning metadata table...")

    op.create_table(
        "partition_metadata",
        sa.Column("partition_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("table_name", sa.String(100), nullable=False),
        sa.Column("partition_name", sa.String(100), nullable=False),
        sa.Column("partition_type", sa.String(50), nullable=False),
        sa.Column("partition_key", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_partition_metadata_table", "partition_metadata", ["table_name", "is_active"])

    logger.info("    ✓ Partitioning metadata table created")

    # =========================================================================
    # PART 5: AUDIT LOGGING & RBAC (from 009)
    # =========================================================================

    logger.info("[5/12] Creating audit logging and RBAC tables...")

    # Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('log_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('account_id', sa.String(length=255), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('before_state', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('after_state', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_id', sa.String(length=100), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('error_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('log_id'),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_account_id', 'audit_logs', ['account_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('ix_audit_logs_resource_id', 'audit_logs', ['resource_id'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_request_id', 'audit_logs', ['request_id'])

    # RBAC: Roles
    op.create_table(
        'roles',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('role_id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_roles_name', 'roles', ['name'])

    # RBAC: Permissions
    op.create_table(
        'permissions',
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.Column('resource', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('permission_id'),
    )
    op.create_index('ix_permissions_resource', 'permissions', ['resource'])
    op.create_index('ix_permissions_action', 'permissions', ['action'])

    # RBAC: Role-Permission association
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.permission_id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.role_id'], ),
        sa.PrimaryKeyConstraint('role_id', 'permission_id'),
    )

    # RBAC: User-Role assignments
    op.create_table(
        'user_roles',
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('account_id', sa.String(length=255), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('assigned_by', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['role_id'], ['roles.role_id'], ),
        sa.PrimaryKeyConstraint('assignment_id'),
    )
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'])
    op.create_index('ix_user_roles_account_id', 'user_roles', ['account_id'])
    op.create_index('ix_user_roles_role_id', 'user_roles', ['role_id'])

    logger.info("    ✓ Audit logging and RBAC tables created")

    # =========================================================================
    # PART 6: FILE UPLOADS & CRM (from 009)
    # =========================================================================

    logger.info("[6/12] Creating file uploads and CRM tables...")

    # File Uploads
    op.create_table(
        'file_uploads',
        sa.Column('upload_id', sa.Integer(), nullable=False),
        sa.Column('file_key', sa.String(length=500), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('virus_scan_status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('virus_scan_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('thumbnail_key', sa.String(length=500), nullable=True),
        sa.Column('project_id', sa.String(length=255), nullable=True),
        sa.Column('uploaded_by', sa.String(length=255), nullable=False),
        sa.Column('account_id', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('upload_id'),
        sa.UniqueConstraint('file_key'),
    )
    op.create_index('ix_file_uploads_file_key', 'file_uploads', ['file_key'])
    op.create_index('ix_file_uploads_sha256', 'file_uploads', ['sha256'])
    op.create_index('ix_file_uploads_project_id', 'file_uploads', ['project_id'])
    op.create_index('ix_file_uploads_uploaded_by', 'file_uploads', ['uploaded_by'])
    op.create_index('ix_file_uploads_account_id', 'file_uploads', ['account_id'])

    # CRM Webhooks
    op.create_table(
        'crm_webhooks',
        sa.Column('webhook_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('direction', sa.String(length=20), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('response_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('webhook_id'),
    )
    op.create_index('ix_crm_webhooks_event_type', 'crm_webhooks', ['event_type'])
    op.create_index('ix_crm_webhooks_direction', 'crm_webhooks', ['direction'])
    op.create_index('ix_crm_webhooks_created_at', 'crm_webhooks', ['created_at'])

    logger.info("    ✓ File uploads and CRM tables created")

    # =========================================================================
    # PART 7: COMPLIANCE & PE STAMPS (from 009)
    # =========================================================================

    logger.info("[7/12] Creating compliance and PE stamp tables...")

    # Compliance Records
    op.create_table(
        'compliance_records',
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.String(length=255), nullable=False),
        sa.Column('requirement_type', sa.String(length=100), nullable=False),
        sa.Column('requirement_code', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('compliance_data', postgresql.JSON(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('verified_by', sa.String(length=255), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('record_id'),
    )
    op.create_index('ix_compliance_records_project_id', 'compliance_records', ['project_id'])
    op.create_index('ix_compliance_records_requirement_type', 'compliance_records', ['requirement_type'])

    # PE Stamps
    op.create_table(
        'pe_stamps',
        sa.Column('stamp_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.String(length=255), nullable=False),
        sa.Column('calculation_id', sa.String(length=255), nullable=True),
        sa.Column('pe_user_id', sa.String(length=255), nullable=False),
        sa.Column('pe_license_number', sa.String(length=100), nullable=False),
        sa.Column('pe_state', sa.String(length=2), nullable=False),
        sa.Column('stamp_type', sa.String(length=50), nullable=False),
        sa.Column('methodology', sa.Text(), nullable=False),
        sa.Column('code_references', postgresql.JSON(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('stamped_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('pdf_url', sa.String(length=500), nullable=True),
        sa.Column('is_revoked', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_reason', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('stamp_id'),
    )
    op.create_index('ix_pe_stamps_project_id', 'pe_stamps', ['project_id'])
    op.create_index('ix_pe_stamps_calculation_id', 'pe_stamps', ['calculation_id'])
    op.create_index('ix_pe_stamps_pe_user_id', 'pe_stamps', ['pe_user_id'])
    op.create_index('ix_pe_stamps_stamped_at', 'pe_stamps', ['stamped_at'])

    logger.info("    ✓ Compliance and PE stamp tables created")

    # =========================================================================
    # PART 8: MATERIALIZED VIEWS & EXTENSIONS (from 005)
    # =========================================================================

    logger.info("[8/12] Creating materialized views and extensions...")

    # Enable extensions for monitoring
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")

    # Create materialized view for project stats
    op.execute("""
        CREATE MATERIALIZED VIEW project_stats AS
        SELECT
            account_id,
            status,
            COUNT(*) as project_count,
            AVG(EXTRACT(EPOCH FROM (updated_at - created_at))/3600) as avg_duration_hours
        FROM projects
        WHERE status != 'draft'
        GROUP BY account_id, status
    """)

    op.execute("""
        CREATE UNIQUE INDEX ix_project_stats_unique
        ON project_stats(account_id, status)
    """)

    logger.info("    ✓ Materialized views and extensions created")

    # =========================================================================
    # PART 9: AISC SHAPES DATABASE V16.0 (from 001a)
    # =========================================================================

    logger.info("[9/12] Creating AISC shapes foundation catalog...")

    # Create shape type enum
    shape_type_enum = postgresql.ENUM(
        'W', 'S', 'HP', 'M', 'C', 'MC', 'L', '2L', 'WT', 'ST',
        'HSS', 'PIPE', 'TUBE', 'CUSTOM',
        name='shape_type_enum',
        create_type=True
    )
    shape_type_enum.create(op.get_bind(), checkfirst=True)

    # Create the main AISC shapes catalog table
    op.create_table(
        'aisc_shapes_v16',
        # Primary identification
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('edi_std_nomenclature', sa.String(100)),
        sa.Column('aisc_manual_label', sa.String(100), nullable=False, unique=True),

        # Material specifications
        sa.Column('t_f', sa.String(10)),
        sa.Column('is_astm_a1085', sa.Boolean(), server_default='false'),
        sa.Column('fy_ksi', sa.Float(), server_default='50'),
        sa.Column('fu_ksi', sa.Float(), server_default='65'),

        # Weight and area
        sa.Column('w', sa.Float()),
        sa.Column('area', sa.Float()),

        # Primary dimensions
        sa.Column('d', sa.Float()),
        sa.Column('d_det', sa.Float()),
        sa.Column('ht', sa.Float()),
        sa.Column('h', sa.Float()),
        sa.Column('od', sa.Float()),
        sa.Column('id_dim', sa.Float()),

        # Width dimensions
        sa.Column('bf', sa.Float()),
        sa.Column('bf_det', sa.Float()),
        sa.Column('b', sa.Float()),

        # Thickness dimensions
        sa.Column('tw', sa.Float()),
        sa.Column('tw_det', sa.Float()),
        sa.Column('tf', sa.Float()),
        sa.Column('tf_det', sa.Float()),
        sa.Column('tnom', sa.Float()),
        sa.Column('tdes', sa.Float()),

        # Section properties - Strong axis (x-x)
        sa.Column('ix', sa.Float()),
        sa.Column('sx', sa.Float()),
        sa.Column('rx', sa.Float()),
        sa.Column('zx', sa.Float()),

        # Section properties - Weak axis (y-y)
        sa.Column('iy', sa.Float()),
        sa.Column('sy', sa.Float()),
        sa.Column('ry', sa.Float()),
        sa.Column('zy', sa.Float()),

        # Torsional and warping properties
        sa.Column('j', sa.Float()),
        sa.Column('cw', sa.Float()),
        sa.Column('rts', sa.Float()),
        sa.Column('ho', sa.Float()),

        # Shear properties
        sa.Column('aw', sa.Float()),
        sa.Column('ag', sa.Float()),
        sa.Column('an', sa.Float()),

        # Slenderness ratios
        sa.Column('bf_2tf', sa.Float()),
        sa.Column('h_tw', sa.Float()),
        sa.Column('d_t', sa.Float()),
        sa.Column('b_t', sa.Float()),

        # For angles (L shapes)
        sa.Column('x_bar', sa.Float()),
        sa.Column('y_bar', sa.Float()),
        sa.Column('ro', sa.Float()),
        sa.Column('h_bar', sa.Float()),
        sa.Column('tan_alpha', sa.Float()),

        # Classification and availability
        sa.Column('wt_class', sa.String(20)),
        sa.Column('is_available', sa.Boolean(), server_default='true'),
        sa.Column('is_slender', sa.Boolean(), server_default='false'),

        # Search optimization
        sa.Column('nominal_depth', sa.Integer()),
        sa.Column('nominal_weight', sa.Integer()),

        # Metadata
        sa.Column('source', sa.String(50), server_default='AISC_v16.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id')
    )

    # Create comprehensive indexes for performance
    op.create_index('ix_aisc_type', 'aisc_shapes_v16', ['type'])
    op.create_index('ix_aisc_weight', 'aisc_shapes_v16', ['w'])
    op.create_index('ix_aisc_sx', 'aisc_shapes_v16', ['sx'])
    op.create_index('ix_aisc_ix', 'aisc_shapes_v16', ['ix'])
    op.create_index('ix_aisc_rx', 'aisc_shapes_v16', ['rx'])
    op.create_index('ix_aisc_ry', 'aisc_shapes_v16', ['ry'])
    op.create_index('ix_aisc_label', 'aisc_shapes_v16', ['aisc_manual_label'])
    op.create_index('ix_aisc_nominal', 'aisc_shapes_v16', ['nominal_depth', 'nominal_weight'])
    op.create_index('ix_aisc_type_sx', 'aisc_shapes_v16', ['type', 'sx'])
    op.create_index('ix_aisc_type_w', 'aisc_shapes_v16', ['type', 'w'])
    op.create_index('ix_aisc_a1085', 'aisc_shapes_v16', ['is_astm_a1085'])

    logger.info("    ✓ AISC shapes v16 table created")

    # =========================================================================
    # PART 10: MATERIAL COST TRACKING (from 001b)
    # =========================================================================

    logger.info("[10/12] Creating material cost tracking tables...")

    # Create material type enum
    material_enum = postgresql.ENUM(
        'STEEL_STRUCTURAL', 'STEEL_PLATE', 'STEEL_REBAR',
        'ALUMINUM_6061', 'ALUMINUM_6063', 'ALUMINUM_CAST',
        'STAINLESS_304', 'STAINLESS_316',
        'CONCRETE', 'GROUT', 'ANCHOR_BOLTS',
        'GALVANIZING', 'POWDER_COATING', 'PAINT',
        name='material_type_enum',
        create_type=True
    )
    material_enum.create(op.get_bind(), checkfirst=True)

    # Main material cost tracking table
    op.create_table(
        'material_cost_indices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('material', sa.Enum('STEEL_STRUCTURAL', 'STEEL_PLATE', 'STEEL_REBAR',
                                       'ALUMINUM_6061', 'ALUMINUM_6063', 'ALUMINUM_CAST',
                                       'STAINLESS_304', 'STAINLESS_316',
                                       'CONCRETE', 'GROUT', 'ANCHOR_BOLTS',
                                       'GALVANIZING', 'POWDER_COATING', 'PAINT',
                                       name='material_type_enum'), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer()),

        # Pricing data
        sa.Column('index_value', sa.Float(), nullable=False),
        sa.Column('price_per_lb', sa.Numeric(10, 4)),
        sa.Column('price_per_cy', sa.Numeric(10, 2)),
        sa.Column('price_per_sqft', sa.Numeric(10, 2)),
        sa.Column('price_per_unit', sa.Numeric(10, 2)),

        # Additional cost factors
        sa.Column('fabrication_multiplier', sa.Float(), server_default='1.75'),
        sa.Column('installation_multiplier', sa.Float(), server_default='1.5'),
        sa.Column('transportation_per_lb', sa.Numeric(10, 4)),

        # Source and metadata
        sa.Column('source', sa.String(100)),
        sa.Column('region', sa.String(50), server_default='US_NATIONAL'),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('material', 'year', 'month', name='uq_material_year_month')
    )

    op.create_index('ix_cost_material', 'material_cost_indices', ['material'])
    op.create_index('ix_cost_year_month', 'material_cost_indices', ['year', 'month'])
    op.create_index('ix_cost_material_date', 'material_cost_indices', ['material', 'year', 'month'])

    # Regional cost adjustments table
    op.create_table(
        'regional_cost_factors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('state', sa.String(2), nullable=False),
        sa.Column('city', sa.String(100)),
        sa.Column('county', sa.String(100)),
        sa.Column('zip_code', sa.String(10)),

        # Regional multipliers
        sa.Column('material_factor', sa.Float(), server_default='1.0'),
        sa.Column('labor_factor', sa.Float(), server_default='1.0'),
        sa.Column('equipment_factor', sa.Float(), server_default='1.0'),
        sa.Column('overall_factor', sa.Float(), server_default='1.0'),

        # Specific adjustments
        sa.Column('steel_adjustment', sa.Float(), server_default='1.0'),
        sa.Column('concrete_adjustment', sa.Float(), server_default='1.0'),
        sa.Column('transportation_adjustment', sa.Float(), server_default='1.0'),

        sa.Column('effective_date', sa.Date()),
        sa.Column('source', sa.String(100)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_regional_state', 'regional_cost_factors', ['state'])
    op.create_index('ix_regional_city_state', 'regional_cost_factors', ['city', 'state'])
    op.create_index('ix_regional_zip', 'regional_cost_factors', ['zip_code'])

    # Material suppliers table
    op.create_table(
        'material_suppliers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('supplier_name', sa.String(200), nullable=False),
        sa.Column('supplier_code', sa.String(50), unique=True),
        sa.Column('material_type', sa.Enum('STEEL_STRUCTURAL', 'STEEL_PLATE', 'STEEL_REBAR',
                                            'ALUMINUM_6061', 'ALUMINUM_6063', 'ALUMINUM_CAST',
                                            'STAINLESS_304', 'STAINLESS_316',
                                            'CONCRETE', 'GROUT', 'ANCHOR_BOLTS',
                                            'GALVANIZING', 'POWDER_COATING', 'PAINT',
                                            name='material_type_enum')),

        # Pricing tiers
        sa.Column('base_price_per_lb', sa.Numeric(10, 4)),
        sa.Column('volume_discount_1000lb', sa.Float()),
        sa.Column('volume_discount_5000lb', sa.Float()),
        sa.Column('volume_discount_10000lb', sa.Float()),

        # Lead times
        sa.Column('standard_lead_days', sa.Integer()),
        sa.Column('expedited_lead_days', sa.Integer()),
        sa.Column('expedite_surcharge', sa.Float()),

        # Contact and location
        sa.Column('contact_email', sa.String(200)),
        sa.Column('contact_phone', sa.String(50)),
        sa.Column('address', sa.Text()),
        sa.Column('delivery_radius_miles', sa.Integer()),

        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('ix_supplier_material', 'material_suppliers', ['material_type'])
    op.create_index('ix_supplier_active', 'material_suppliers', ['is_active'])

    # Insert baseline cost indices
    op.execute("""
    INSERT INTO material_cost_indices
    (material, year, month, quarter, index_value, price_per_lb, source)
    VALUES
    -- Steel structural indices
    ('STEEL_STRUCTURAL', 2020, 1, 1, 100.0, 0.65, 'ENR'),
    ('STEEL_STRUCTURAL', 2021, 1, 1, 115.2, 0.75, 'ENR'),
    ('STEEL_STRUCTURAL', 2022, 1, 1, 142.8, 0.93, 'ENR'),
    ('STEEL_STRUCTURAL', 2023, 1, 1, 128.5, 0.84, 'ENR'),
    ('STEEL_STRUCTURAL', 2024, 1, 1, 135.2, 0.88, 'ENR'),
    ('STEEL_STRUCTURAL', 2025, 1, 1, 138.7, 0.90, 'ENR'),
    ('STEEL_STRUCTURAL', 2025, 11, 4, 140.2, 0.91, 'ENR'),

    -- Aluminum indices
    ('ALUMINUM_6061', 2020, 1, 1, 100.0, 1.85, 'LME'),
    ('ALUMINUM_6061', 2021, 1, 1, 108.5, 2.01, 'LME'),
    ('ALUMINUM_6061', 2022, 1, 1, 125.3, 2.32, 'LME'),
    ('ALUMINUM_6061', 2023, 1, 1, 118.2, 2.19, 'LME'),
    ('ALUMINUM_6061', 2024, 1, 1, 122.5, 2.27, 'LME'),
    ('ALUMINUM_6061', 2025, 1, 1, 124.8, 2.31, 'LME'),
    ('ALUMINUM_6061', 2025, 11, 4, 126.1, 2.33, 'LME'),

    -- Galvanizing costs
    ('GALVANIZING', 2025, 11, 4, 100.0, 0.35, 'Industry Average'),

    -- Concrete prices
    ('CONCRETE', 2025, 11, 4, 145.0, NULL, 'Local Average')
    ON CONFLICT (material, year, month) DO NOTHING
    """)

    # Insert regional factors
    op.execute("""
    INSERT INTO regional_cost_factors
    (state, city, material_factor, labor_factor, overall_factor)
    VALUES
    ('TX', 'Houston', 0.95, 0.90, 0.93),
    ('TX', 'Dallas', 0.96, 0.92, 0.94),
    ('CA', 'Los Angeles', 1.12, 1.35, 1.24),
    ('CA', 'San Francisco', 1.15, 1.45, 1.30),
    ('NY', 'New York', 1.18, 1.42, 1.30),
    ('FL', 'Miami', 1.02, 0.95, 0.99),
    ('IL', 'Chicago', 1.05, 1.20, 1.13),
    ('AZ', 'Phoenix', 0.98, 0.88, 0.93),
    ('GA', 'Atlanta', 0.97, 0.93, 0.95),
    ('WA', 'Seattle', 1.08, 1.25, 1.17)
    """)

    logger.info("    ✓ Material cost tracking tables created with baseline data")

    # =========================================================================
    # PART 11: SIGN-SPECIFIC VIEWS & FUNCTIONS (from 001c)
    # =========================================================================

    logger.info("[11/12] Creating sign-specific views and calculation functions...")

    # Create materialized view for HSS sections
    op.execute("""
    CREATE MATERIALIZED VIEW hss_sections AS
    SELECT
        aisc_manual_label as designation,
        w as weight_plf,
        area as area_in2,
        b as width,
        d as height,
        tnom as wall_nominal,
        tdes as wall_design,
        ix as ix_in4,
        sx as sx_in3,
        rx as rx_in,
        iy as iy_in4,
        sy as sy_in3,
        ry as ry_in,
        j as j_in4,
        is_astm_a1085,
        b_t as width_thickness_ratio,
        CASE
            WHEN b_t <= 35 THEN 'Compact'
            WHEN b_t <= 42 THEN 'Noncompact'
            ELSE 'Slender'
        END as classification,
        CASE
            WHEN is_astm_a1085 THEN 0.93
            ELSE 0.86
        END as design_thickness_factor
    FROM aisc_shapes_v16
    WHERE type = 'HSS'
    ORDER BY w
    """)

    op.execute("CREATE INDEX ix_hss_weight ON hss_sections(weight_plf)")
    op.execute("CREATE INDEX ix_hss_sx ON hss_sections(sx_in3)")

    # Create function to get current material price
    op.execute("""
    CREATE OR REPLACE FUNCTION get_current_material_price(
        p_material material_type_enum,
        p_weight_lb FLOAT DEFAULT 1.0,
        p_state VARCHAR DEFAULT NULL
    )
    RETURNS TABLE (
        base_price NUMERIC,
        regional_factor FLOAT,
        total_price NUMERIC,
        price_date DATE
    )
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_price_per_lb NUMERIC;
        v_regional_factor FLOAT;
        v_year INT;
        v_month INT;
    BEGIN
        -- Get latest price
        SELECT price_per_lb, year, month INTO v_price_per_lb, v_year, v_month
        FROM material_cost_indices
        WHERE material = p_material
        ORDER BY year DESC, month DESC
        LIMIT 1;

        -- Get regional factor
        IF p_state IS NOT NULL THEN
            SELECT COALESCE(overall_factor, 1.0) INTO v_regional_factor
            FROM regional_cost_factors
            WHERE state = p_state
            LIMIT 1;
        ELSE
            v_regional_factor := 1.0;
        END IF;

        RETURN QUERY
        SELECT
            v_price_per_lb * p_weight_lb AS base_price,
            v_regional_factor AS regional_factor,
            v_price_per_lb * p_weight_lb * v_regional_factor AS total_price,
            make_date(v_year, v_month, 1) AS price_date;
    END;
    $$
    """)

    # Create view for current prices
    op.execute("""
    CREATE OR REPLACE VIEW current_material_prices AS
    WITH latest_prices AS (
        SELECT DISTINCT ON (material)
            material,
            year,
            month,
            index_value,
            price_per_lb,
            price_per_cy,
            price_per_sqft,
            fabrication_multiplier,
            installation_multiplier
        FROM material_cost_indices
        ORDER BY material, year DESC, month DESC
    )
    SELECT
        material,
        make_date(year, month, 1) as price_date,
        index_value,
        price_per_lb,
        price_per_cy,
        price_per_sqft,
        price_per_lb * fabrication_multiplier as fabricated_price_per_lb,
        price_per_lb * (1 + fabrication_multiplier + installation_multiplier) as installed_price_per_lb
    FROM latest_prices
    """)

    logger.info("    ✓ Material pricing views and functions created")

    # =========================================================================
    # PART 12: ASCE 7-22 WIND PRESSURE FUNCTION
    # =========================================================================

    logger.info("[12/12] Creating ASCE 7-22 wind pressure calculation function...")

    # Create exposure category enum (if not exists)
    exposure_enum = postgresql.ENUM(
        'B', 'C', 'D',
        name='exposure_category',
        create_type=True
    )
    exposure_enum.create(op.get_bind(), checkfirst=True)

    # Create risk category enum (if not exists)
    risk_category_enum = postgresql.ENUM(
        'I', 'II', 'III', 'IV',
        name='risk_category',
        create_type=True
    )
    risk_category_enum.create(op.get_bind(), checkfirst=True)

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
        v_height_ft FLOAT := GREATEST(p_height_ft, 15);
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
            v_kz := 0.85;
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
    $$
    """)

    logger.info("    ✓ ASCE 7-22 wind pressure function created")

    logger.info("")
    logger.info("[SUCCESS] Foundation schema complete!")
    logger.info("")
    logger.info("Summary:")
    logger.info("  • Projects core tables (projects, payloads, events)")
    logger.info("  • AISC Shapes Database v16.0 (all steel sections)")
    logger.info("  • Material cost tracking with regional factors")
    logger.info("  • Calibration constants and pricing configs")
    logger.info("  • Audit logging, RBAC, compliance, and PE stamps")
    logger.info("  • File uploads and CRM webhook infrastructure")
    logger.info("  • Performance indexes and materialized views")
    logger.info("  • ASCE 7-22 wind pressure calculation function")
    logger.info("  • Sign-specific optimization views")


def downgrade() -> None:
    """Drop all foundation tables."""

    logger.info("[INFO] Dropping foundation schema...")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS calculate_asce7_wind_pressure CASCADE")
    op.execute("DROP FUNCTION IF EXISTS get_current_material_price CASCADE")

    # Drop views
    op.execute("DROP VIEW IF EXISTS current_material_prices CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS hss_sections CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS project_stats CASCADE")

    # Drop extensions
    op.execute("DROP EXTENSION IF EXISTS pg_stat_statements CASCADE")

    # Drop tables (reverse order of creation)
    op.drop_table('pe_stamps')
    op.drop_table('compliance_records')
    op.drop_table('crm_webhooks')
    op.drop_table('file_uploads')
    op.drop_table('user_roles')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_table('audit_logs')
    op.drop_table('partition_metadata')
    op.drop_table('material_suppliers')
    op.drop_table('regional_cost_factors')
    op.drop_table('material_cost_indices')
    op.drop_table('aisc_shapes_v16')
    op.drop_table('code_references')
    op.drop_table('material_catalog')
    op.drop_table('pricing_configs')
    op.drop_table('calibration_constants')
    op.drop_table('project_events')
    op.drop_table('project_payloads')
    op.drop_table('projects')

    # Drop enums
    risk_category_enum = postgresql.ENUM('I', 'II', 'III', 'IV', name='risk_category')
    risk_category_enum.drop(op.get_bind(), checkfirst=True)

    exposure_enum = postgresql.ENUM('B', 'C', 'D', name='exposure_category')
    exposure_enum.drop(op.get_bind(), checkfirst=True)

    material_enum = postgresql.ENUM(
        'STEEL_STRUCTURAL', 'STEEL_PLATE', 'STEEL_REBAR',
        'ALUMINUM_6061', 'ALUMINUM_6063', 'ALUMINUM_CAST',
        'STAINLESS_304', 'STAINLESS_316',
        'CONCRETE', 'GROUT', 'ANCHOR_BOLTS',
        'GALVANIZING', 'POWDER_COATING', 'PAINT',
        name='material_type_enum'
    )
    material_enum.drop(op.get_bind(), checkfirst=True)

    shape_type_enum = postgresql.ENUM(
        'W', 'S', 'HP', 'M', 'C', 'MC', 'L', '2L', 'WT', 'ST',
        'HSS', 'PIPE', 'TUBE', 'CUSTOM',
        name='shape_type_enum'
    )
    shape_type_enum.drop(op.get_bind(), checkfirst=True)

    logger.info("[SUCCESS] Foundation schema dropped")
