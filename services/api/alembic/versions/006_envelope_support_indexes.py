"""envelope_support_indexes

Revision ID: 006
Revises: 005
Create Date: 2025-01-27 20:00:00.000000

Adds envelope support columns, performance indexes, GIN indexes, and integrity constraints.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add envelope support columns to projects
    op.add_column("projects", sa.Column("constants_version", sa.String(500), nullable=True))
    op.add_column("projects", sa.Column("content_sha256", sa.String(64), nullable=True))
    op.add_column("projects", sa.Column("confidence", sa.Float(), nullable=True))
    
    # Performance indexes
    op.create_index("ix_projects_content_sha", "projects", ["content_sha256"], if_not_exists=True)
    op.create_index("ix_projects_etag", "projects", ["etag"], if_not_exists=True)
    op.create_index("ix_projects_account_status_created", "projects", 
                    ["account_id", "status", sa.text("created_at DESC")], if_not_exists=True)
    op.create_index("ix_payloads_project_module", "project_payloads", 
                    ["project_id", "module"], if_not_exists=True)
    op.create_index("ix_events_project_timestamp", "project_events", 
                    ["project_id", sa.text("timestamp DESC")], if_not_exists=True)
    
    # Partial index for active projects (smaller, faster)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_projects_active_status 
        ON projects(status, created_at DESC) 
        WHERE status IN ('draft', 'estimating')
        """
    )
    
    # GIN index for JSONB queries (requires JSONB column; skip if using JSON)
    # Note: PostgreSQL JSON type doesn't support GIN; convert to JSONB first if needed
    # op.execute(
    #     """
    #     CREATE INDEX IF NOT EXISTS idx_payloads_config_gin 
    #     ON project_payloads USING GIN(config)
    #     """
    # )
    
    # Add CHECK constraints for envelope integrity
    op.execute(
        """
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'chk_confidence'
            ) THEN
                ALTER TABLE projects ADD CONSTRAINT chk_confidence 
                CHECK (confidence >= 0.0 AND confidence <= 1.0 OR confidence IS NULL);
            END IF;
        END $$;
        """
    )
    
    # Add UNIQUE constraint on etag (for optimistic locking)
    op.execute(
        """
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_projects_etag'
            ) THEN
                CREATE UNIQUE INDEX IF NOT EXISTS uq_projects_etag ON projects(etag) 
                WHERE etag IS NOT NULL;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_index("uq_projects_etag", table_name="projects", if_exists=True)
    op.drop_constraint("chk_confidence", table_name="projects", if_exists=True)
    op.drop_index("ix_projects_active_status", table_name="projects", if_exists=True)
    op.drop_index("ix_events_project_timestamp", table_name="project_events", if_exists=True)
    op.drop_index("ix_payloads_project_module", table_name="project_payloads", if_exists=True)
    op.drop_index("ix_projects_account_status_created", table_name="projects", if_exists=True)
    op.drop_index("ix_projects_etag", table_name="projects", if_exists=True)
    op.drop_index("ix_projects_content_sha", table_name="projects", if_exists=True)
    op.drop_column("projects", "confidence")
    op.drop_column("projects", "content_sha256")
    op.drop_column("projects", "constants_version")

