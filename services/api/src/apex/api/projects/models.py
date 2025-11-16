"""Project management models for CalcuSign workflows.

Defines project lifecycle, payloads, and event tracking.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    """Project lifecycle states."""

    draft = "draft"
    estimating = "estimating"
    submitted = "submitted"
    accepted = "accepted"
    rejected = "rejected"


class ProjectMeta(BaseModel):
    """Project metadata and lifecycle state."""

    project_id: str = Field(..., description="Unique project identifier")
    account_id: str = Field(..., description="Account/tenant identifier")
    name: str = Field(..., description="Project name")
    customer: Optional[str] = Field(None, description="Customer name")
    description: Optional[str] = Field(None, description="Project description")
    site_name: Optional[str] = Field(None, description="Site name")
    street: Optional[str] = Field(None, description="Street address")
    status: Literal["draft", "estimating", "submitted", "accepted", "rejected"] = Field(
        "draft", description="Project status"
    )
    created_by: str = Field(..., description="Creator user ID")
    updated_by: str = Field(..., description="Last updater user ID")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 update timestamp")
    etag: Optional[str] = Field(None, description="Optimistic locking token")


class ProjectCreateRequest(BaseModel):
    """Request to create a new project."""

    account_id: str = Field(..., description="Account ID")
    name: str = Field(..., description="Project name")
    customer: Optional[str] = None
    description: Optional[str] = None
    created_by: str = Field(..., description="Creator user ID")


class ProjectUpdateRequest(BaseModel):
    """Request to update a project."""

    name: Optional[str] = None
    customer: Optional[str] = None
    description: Optional[str] = None
    site_name: Optional[str] = None
    street: Optional[str] = None
