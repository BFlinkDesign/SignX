"""add_partitioning

Revision ID: 007
Revises: 006
Create Date: 2025-01-27 22:00:00.000000

Implements partitioning infrastructure and documentation for scale.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create partition metadata tracking table
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
    
    # Note: Full table partitioning requires offline migration
    # See scripts/create_monthly_partition.sh for production implementation


def downgrade() -> None:
    op.drop_table("partition_metadata")
