"""add_calib_pricing_tables

Revision ID: 003
Revises: 002
Create Date: 2025-01-27 14:00:00.000000

Adds calibration constants and pricing tables for versioned configurations.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Calibration constants table (versioned engineering constants)
    op.create_table(
        "calibration_constants",
        sa.Column("constant_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),  # e.g., "v1", "footing_v2"
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(255), nullable=True),  # ASCE 7-16, AISC 360, etc.
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_calib_name_version", "calibration_constants", ["name", "version"], unique=True)
    op.create_index("ix_calib_version", "calibration_constants", ["version"])
    
    # Pricing table (versioned pricing configurations)
    op.create_table(
        "pricing_configs",
        sa.Column("price_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("item_code", sa.String(100), nullable=False),  # e.g., "calc_packet", "hard_copies"
        sa.Column("version", sa.String(50), nullable=False),  # e.g., "v1"
        sa.Column("price_usd", sa.Numeric(10, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),  # addon, base, permit
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_pricing_item_version", "pricing_configs", ["item_code", "version"], unique=True)
    op.create_index("ix_pricing_effective", "pricing_configs", ["effective_from", "effective_to"])
    
    # AISC/ASCE catalog stubs (material properties and code references)
    op.create_table(
        "material_catalog",
        sa.Column("material_id", sa.String(50), primary_key=True),  # e.g., "AISC_99_A36"
        sa.Column("standard", sa.String(50), nullable=False),  # AISC, ASTM, etc.
        sa.Column("grade", sa.String(50), nullable=False),  # A36, A572_50, etc.
        sa.Column("shape", sa.String(50), nullable=False),  # HSS, pipe, round, etc.
        sa.Column("properties", postgresql.JSON(astext_type=sa.Text()), nullable=False),  # f_y, E, etc.
        sa.Column("dimensions", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("source_table", sa.String(100), nullable=True),  # Reference to source
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_mat_standard_grade", "material_catalog", ["standard", "grade"])
    op.create_index("ix_mat_shape", "material_catalog", ["shape"])
    
    # Engineering code references table
    op.create_table(
        "code_references",
        sa.Column("ref_id", sa.String(100), primary_key=True),  # e.g., "ASCE_7_16_26_10_1"
        sa.Column("code", sa.String(50), nullable=False),  # ASCE 7-16, AISC 360, etc.
        sa.Column("section", sa.String(100), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("formula", sa.Text(), nullable=True),  # JSON encoded formula or reference
        sa.Column("application", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_code_section", "code_references", ["code", "section"])


def downgrade() -> None:
    op.drop_table("code_references")
    op.drop_table("material_catalog")
    op.drop_table("pricing_configs")
    op.drop_table("calibration_constants")

