"""Universal cost record model."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from signx_intel.storage.database import Base


class CostRecord(Base):
    """Universal cost record that works for any estimating domain."""
    
    __tablename__ = "cost_records"
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Foreign key to project
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Cost breakdown
    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=False
    )
    labor_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=True
    )
    material_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=True
    )
    equipment_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=True
    )
    overhead_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=True
    )
    tax: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=True
    )
    shipping: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=True
    )
    
    # Cost drivers (flexible JSON for different project types)
    # Examples: sign_height_ft, sign_area_sqft, foundation_type, wind_speed_mph, etc.
    drivers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    
    # ML/Intelligence metadata
    predicted_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=True
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    cost_drivers_importance: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    anomaly_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Additional metadata
    notes: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    cost_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_cost_records_cost_date', 'cost_date'),
        Index('ix_cost_records_total_cost', 'total_cost'),
        Index('ix_cost_records_drivers', 'drivers', postgresql_using='gin'),
    )
    
    def __repr__(self) -> str:
        return f"<CostRecord ${self.total_cost} for Project {self.project_id}>"

