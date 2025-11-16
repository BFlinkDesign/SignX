"""add_enums_and_indexes

Revision ID: 002
Revises: 001
Create Date: 2025-01-27 12:00:00.000000

Adds ENUM constraints for status/module/event_type and composite indexes for performance.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add CHECK constraints for status values (idempotent via DO block)
    op.execute(
        """
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'projects_status_check'
            ) THEN
                ALTER TABLE projects ADD CONSTRAINT projects_status_check 
                CHECK (status IN ('draft','estimating','submitted','accepted','rejected'));
            END IF;
        END $$;
        """
    )
    
    # Add CHECK constraint for module (via app validation, but enforce at DB)
    op.execute(
        """
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'project_payloads_module_check'
            ) THEN
                ALTER TABLE project_payloads ADD CONSTRAINT project_payloads_module_check 
                CHECK (module IN ('signage.single_pole.direct_burial','signage.single_pole.base_plate','signage.two_pole.direct_burial'));
            END IF;
        END $$;
        """
    )
    
    # Add composite index for payload history queries (project_id, module, created_at DESC)
    op.create_index(
        "ix_project_payloads_project_module_created",
        "project_payloads",
        ["project_id", "module", sa.text("created_at DESC")],
        unique=False,
        if_not_exists=True,
    )
    
    # Add index on event_type for auditing queries
    op.create_index(
        "ix_project_events_event_type",
        "project_events",
        ["event_type"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_project_events_event_type", table_name="project_events", if_exists=True)
    op.drop_index("ix_project_payloads_project_module_created", table_name="project_payloads", if_exists=True)
    op.execute("ALTER TABLE project_payloads DROP CONSTRAINT IF EXISTS project_payloads_module_check")
    op.execute("ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_status_check")

