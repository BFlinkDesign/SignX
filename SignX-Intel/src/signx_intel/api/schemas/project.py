"""Project schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from signx_intel.storage.models.project import ProjectSource, ProjectStatus


class ProjectBase(BaseModel):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    customer_name: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=500)
    metadata: dict = Field(default_factory=dict)
    source: ProjectSource = ProjectSource.MANUAL
    status: ProjectStatus = ProjectStatus.DRAFT
    external_id: Optional[str] = Field(None, max_length=255)
    project_date: Optional[datetime] = None


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    customer_name: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=500)
    metadata: Optional[dict] = None
    status: Optional[ProjectStatus] = None
    project_date: Optional[datetime] = None


class ProjectResponse(ProjectBase):
    """Schema for project response."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    """Schema for paginated project list."""
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

