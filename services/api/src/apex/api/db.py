"""Database session and models for projects."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

import sqlalchemy as sa
from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .deps import settings


class Base(DeclarativeBase):
    """Base class for database models."""


# Type aliases
int_pk = Annotated[int, mapped_column(primary_key=True)]
str_pk = Annotated[str, mapped_column(String(50), primary_key=True)]
str_255 = Annotated[str, mapped_column(String(255))]
str_text = Annotated[str, mapped_column(Text)]


class Project(Base):
    """Project metadata table with envelope support."""

    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    account_id: Mapped[str_255]
    name: Mapped[str_255]
    customer: Mapped[str_255 | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str_text | None] = mapped_column(Text, nullable=True)
    site_name: Mapped[str_255 | None] = mapped_column(String(255), nullable=True)
    street: Mapped[str_255 | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str_255] = mapped_column(String(50))  # draft, estimating, submitted, accepted, rejected
    created_by: Mapped[str_255]
    updated_by: Mapped[str_255]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    etag: Mapped[str_255 | None] = mapped_column(String(64), nullable=True)  # For optimistic locking
    # Envelope support columns
    constants_version: Mapped[str_255 | None] = mapped_column(String(500), nullable=True)  # Tracks pack versions used
    content_sha256: Mapped[str_255 | None] = mapped_column(String(64), nullable=True)  # Deterministic caching key
    confidence: Mapped[float | None] = mapped_column(sa.Float, nullable=True)  # Last confidence score
    
    # Relationships (eager loading for performance)
    payloads: Mapped[list[ProjectPayload]] = relationship(
        "ProjectPayload",
        foreign_keys="ProjectPayload.project_id",
        lazy="selectin",
        back_populates="project",
    )
    events: Mapped[list[ProjectEvent]] = relationship(
        "ProjectEvent",
        foreign_keys="ProjectEvent.project_id",
        lazy="selectin",
        back_populates="project",
        order_by="ProjectEvent.timestamp.desc()",
    )


class ProjectPayload(Base):
    """Project design payload and configuration."""

    __tablename__ = "project_payloads"

    payload_id: Mapped[int_pk]
    project_id: Mapped[str_255] = mapped_column(String(255), ForeignKey("projects.project_id", ondelete="CASCADE"), index=True)
    module: Mapped[str_255]  # signage.single_pole, signage.baseplate, etc.
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    files: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    cost_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    sha256: Mapped[str_255 | None] = mapped_column(String(64), nullable=True, index=True)  # Deterministic snapshot hash
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())
    
    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="payloads")


class ProjectEvent(Base):
    """Immutable audit log events."""

    __tablename__ = "project_events"

    event_id: Mapped[int_pk]
    project_id: Mapped[str_255] = mapped_column(String(255), ForeignKey("projects.project_id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str_255]  # project.created, file.attached, site.resolved, etc.
    actor: Mapped[str_255]
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), index=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="events")


class CalibrationConstant(Base):
    """Versioned calibration constants for engineering calculations."""

    __tablename__ = "calibration_constants"

    constant_id: Mapped[int_pk]
    name: Mapped[str_255]
    version: Mapped[str_255]
    value: Mapped[float]
    unit: Mapped[str_255 | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str_text | None]
    source: Mapped[str_255 | None]
    effective_from: Mapped[date]
    effective_to: Mapped[date | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())


class PricingConfig(Base):
    """Versioned pricing configurations for add-ons and services."""

    __tablename__ = "pricing_configs"

    price_id: Mapped[int_pk]
    item_code: Mapped[str_255] = mapped_column(String(100))
    version: Mapped[str_255]
    price_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    description: Mapped[str_text | None]
    category: Mapped[str_255 | None] = mapped_column(String(100), nullable=True)
    effective_from: Mapped[date]
    effective_to: Mapped[date | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())


class MaterialCatalog(Base):
    """AISC/ASTM material catalog with properties and dimensions."""

    __tablename__ = "material_catalog"

    material_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    standard: Mapped[str_255]
    grade: Mapped[str_255]
    shape: Mapped[str_255]
    properties: Mapped[dict] = mapped_column(JSON)
    dimensions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_table: Mapped[str_255 | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())


class CodeReference(Base):
    """Engineering code references (ASCE, AISC, etc.) for traceability."""

    __tablename__ = "code_references"

    ref_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    code: Mapped[str_255]
    section: Mapped[str_255]
    title: Mapped[str_text]
    formula: Mapped[str_text | None]
    application: Mapped[str_text | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())


class PoleSection(Base):
    """AISC pole sections for structural analysis."""

    __tablename__ = "pole_sections"

    section_id: Mapped[int_pk]
    designation: Mapped[str_255]
    shape_type: Mapped[str_255]  # HSS, PIPE, W, etc.
    weight_lbs_per_ft: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    area_in2: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    ix_in4: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    sx_in3: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    fy_ksi: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    edition: Mapped[str_255 | None] = mapped_column(String(20), nullable=True)
    source_sha256: Mapped[str_255 | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())


# Engine and session factory
_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    """Dependency for FastAPI to get database session."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables (for migrations, use Alembic instead)."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
