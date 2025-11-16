"""add_pole_sections_table

Revision ID: 008
Revises: 007
Create Date: 2025-11-01 00:00:00.000000

Adds pole_sections table for AISC shapes data.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create pole_sections table for AISC shape data
    op.create_table(
        "pole_sections",
        sa.Column("section_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("designation", sa.String(100), nullable=False),  # e.g., "W6x15", "HSS6x6x1/4"
        sa.Column("shape_type", sa.String(50), nullable=False),  # HSS, PIPE, W, etc.
        sa.Column("weight_lbs_per_ft", sa.Float(), nullable=True),
        sa.Column("area_in2", sa.Float(), nullable=True),
        sa.Column("ix_in4", sa.Float(), nullable=True),  # Moment of inertia
        sa.Column("sx_in3", sa.Float(), nullable=True),  # Section modulus
        sa.Column("fy_ksi", sa.Float(), nullable=True),  # Yield strength
        sa.Column("edition", sa.String(20), nullable=True),  # AISC Manual edition
        sa.Column("source_sha256", sa.String(64), nullable=True),  # File provenance
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_pole_sections_type", "pole_sections", ["shape_type"])
    op.create_index("ix_pole_sections_designation", "pole_sections", ["designation"])


def downgrade() -> None:
    op.drop_table("pole_sections")

