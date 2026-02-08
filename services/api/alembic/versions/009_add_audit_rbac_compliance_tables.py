"""Add audit logging, RBAC, compliance, and CRM tables.

Revision ID: 009
Revises: 008
Create Date: 2025-01-01 12:00:00
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Audit Logs (immutable, append-only)
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


def downgrade() -> None:
    op.drop_index('ix_pe_stamps_stamped_at', table_name='pe_stamps')
    op.drop_index('ix_pe_stamps_pe_user_id', table_name='pe_stamps')
    op.drop_index('ix_pe_stamps_calculation_id', table_name='pe_stamps')
    op.drop_index('ix_pe_stamps_project_id', table_name='pe_stamps')
    op.drop_table('pe_stamps')
    
    op.drop_index('ix_compliance_records_requirement_type', table_name='compliance_records')
    op.drop_index('ix_compliance_records_project_id', table_name='compliance_records')
    op.drop_table('compliance_records')
    
    op.drop_index('ix_crm_webhooks_created_at', table_name='crm_webhooks')
    op.drop_index('ix_crm_webhooks_direction', table_name='crm_webhooks')
    op.drop_index('ix_crm_webhooks_event_type', table_name='crm_webhooks')
    op.drop_table('crm_webhooks')
    
    op.drop_index('ix_file_uploads_account_id', table_name='file_uploads')
    op.drop_index('ix_file_uploads_uploaded_by', table_name='file_uploads')
    op.drop_index('ix_file_uploads_project_id', table_name='file_uploads')
    op.drop_index('ix_file_uploads_sha256', table_name='file_uploads')
    op.drop_index('ix_file_uploads_file_key', table_name='file_uploads')
    op.drop_table('file_uploads')
    
    op.drop_index('ix_user_roles_role_id', table_name='user_roles')
    op.drop_index('ix_user_roles_account_id', table_name='user_roles')
    op.drop_index('ix_user_roles_user_id', table_name='user_roles')
    op.drop_table('user_roles')
    
    op.drop_table('role_permissions')
    
    op.drop_index('ix_permissions_action', table_name='permissions')
    op.drop_index('ix_permissions_resource', table_name='permissions')
    op.drop_table('permissions')
    
    op.drop_index('ix_roles_name', table_name='roles')
    op.drop_table('roles')
    
    op.drop_index('ix_audit_logs_request_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_timestamp', table_name='audit_logs')
    op.drop_index('ix_audit_logs_resource_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_resource_type', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action', table_name='audit_logs')
    op.drop_index('ix_audit_logs_account_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')
    op.drop_table('audit_logs')

