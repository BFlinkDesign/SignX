"""Project model for tracking cost data sources."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
import enum

from signx_intel.storage.database import Base


class ProjectSource(str, enum.Enum):
    """Source system for project data."""
    SIGNX_STUDIO = "signx-studio"
    CRM = "crm"
    MANUAL = "manual"
    PDF_IMPORT = "pdf_import"
    QUICKBOOKS = "quickbooks"
    OTHER = "other"


class ProjectStatus(str, enum.Enum):
    """Project lifecycle status."""
    DRAFT = "draft"
    QUOTED = "quoted"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Project(Base):
    """Project record linking to cost data."""
    
    __tablename__ = "projects"
    
    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Metadata
    source: Mapped[ProjectSource] = mapped_column(
        SQLEnum(ProjectSource),
        nullable=False,
        default=ProjectSource.MANUAL
    )
    status: Mapped[ProjectStatus] = mapped_column(
        SQLEnum(ProjectStatus),
        nullable=False,
        default=ProjectStatus.DRAFT
    )
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Project details
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Flexible metadata
    metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    
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
    project_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    def __repr__(self) -> str:
        return f"<Project {self.name} ({self.id})>"

