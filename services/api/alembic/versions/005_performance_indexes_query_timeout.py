"""performance_indexes_query_timeout

Revision ID: 005
Revises: 004
Create Date: 2025-01-27 18:00:00.000000

Adds performance indexes, materialized views, query timeout, and monitoring extensions.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Performance indexes for common query patterns
    
    # 1. Projects status filtering (dashboard queries)
    op.create_index(
        "ix_projects_status_created", "projects", ["status", sa.text("created_at DESC")],
        if_not_exists=True
    )
    
    # 2. Projects account filtering (multi-tenant)
    op.create_index(
        "ix_projects_account_status", "projects", ["account_id", "status"],
        if_not_exists=True
    )
    
    # 3. Composite for dashboard: account + status + created_at
    op.create_index(
        "ix_projects_account_status_created", "projects",
        ["account_id", "status", sa.text("created_at DESC")],
        if_not_exists=True
    )
    
    # 4. Payload latest lookup (project_id + created_at DESC)
    op.create_index(
        "ix_payloads_project_created", "project_payloads",
        ["project_id", sa.text("created_at DESC")],
        if_not_exists=True
    )
    
    # 5. Payload dedup lookup (project_id + sha256)
    op.create_index(
        "ix_payloads_project_sha256", "project_payloads",
        ["project_id", "sha256"],
        if_not_exists=True
    )
    
    # 6. Events by project and timestamp (audit queries)
    op.create_index(
        "ix_events_project_timestamp", "project_events",
        ["project_id", sa.text("timestamp DESC")],
        if_not_exists=True
    )
    
    # 7. Partial index for non-draft projects (smaller, faster)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_projects_non_draft_status 
        ON projects(status) WHERE status != 'draft'
        """
    )
    
    # Enable extensions for monitoring and performance
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
    
    # Add foreign key constraint (if not exists pattern via manual SQL)
    op.execute(
        """
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'fk_payloads_project_id'
            ) THEN
                ALTER TABLE project_payloads 
                ADD CONSTRAINT fk_payloads_project_id 
                FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE;
            END IF;
        END $$;
        """
    )
    
    op.execute(
        """
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'fk_events_project_id'
            ) THEN
                ALTER TABLE project_events 
                ADD CONSTRAINT fk_events_project_id 
                FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE;
            END IF;
        END $$;
        """
    )
    
    # Create materialized view for project stats
    op.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS project_stats AS
        SELECT 
            account_id,
            status,
            COUNT(*) as project_count,
            AVG(EXTRACT(EPOCH FROM (updated_at - created_at))/3600) as avg_duration_hours
        FROM projects
        WHERE status != 'draft'
        GROUP BY account_id, status
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_project_stats_unique 
        ON project_stats(account_id, status)
        """
    )
    
    # Set query timeout (30s default, prevents runaway queries)
    # Note: Applied via compose.yaml command args instead
    # op.execute("ALTER DATABASE apex SET statement_timeout = '30s'")


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS project_stats")
    op.execute("DROP INDEX IF EXISTS ix_projects_non_draft_status")
    op.execute("DROP INDEX IF EXISTS ix_events_project_timestamp")
    op.execute("DROP INDEX IF EXISTS ix_payloads_project_sha256")
    op.execute("DROP INDEX IF EXISTS ix_payloads_project_created")
    op.execute("DROP INDEX IF EXISTS ix_projects_account_status_created")
    op.execute("DROP INDEX IF EXISTS ix_projects_account_status")
    op.execute("DROP INDEX IF EXISTS ix_projects_status_created")
    op.execute("DROP CONSTRAINT IF EXISTS fk_events_project_id ON project_events")
    op.execute("DROP CONSTRAINT IF EXISTS fk_payloads_project_id ON project_payloads")
    op.execute("DROP EXTENSION IF EXISTS pg_stat_statements")
    # Note: Cannot rollback statement_timeout via migration (use psql)

