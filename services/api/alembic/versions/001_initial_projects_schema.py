"""initial_projects_schema

Revision ID: 001
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
    )

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


def downgrade() -> None:
    op.drop_table("project_events")
    op.drop_table("project_payloads")
    op.drop_table("projects")

