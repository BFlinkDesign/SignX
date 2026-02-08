"""Audit logging and RBAC database models."""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, int_pk, str_255, str_text


class AuditLog(Base):
    """Immutable audit log table for compliance and liability tracking.
    
    Critical for engineering liability - all actions must be logged.
    Retention: 7 years minimum.
    Append-only (immutable) by design - no UPDATE or DELETE operations.
    """

    __tablename__ = "audit_logs"

    log_id: Mapped[int_pk]
    user_id: Mapped[str_255] = mapped_column(String(255), index=True)
    account_id: Mapped[str_255] = mapped_column(String(255), index=True)
    action: Mapped[str_255] = mapped_column(String(100), index=True)  # e.g., "project.created", "calculation.approved"
    resource_type: Mapped[str_255] = mapped_column(String(100), index=True)  # e.g., "project", "calculation", "file"
    resource_id: Mapped[str_255 | None] = mapped_column(String(255), nullable=True, index=True)
    before_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # State before change
    after_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # State after change
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), index=True)
    ip_address: Mapped[str_255 | None] = mapped_column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent: Mapped[str_text | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str_255 | None] = mapped_column(String(100), nullable=True, index=True)  # Correlation ID
    confidence: Mapped[float | None] = mapped_column(sa.Float, nullable=True)  # For calculation actions
    error_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # For error logging


# RBAC Models

class Role(Base):
    """User roles (e.g., admin, engineer, viewer, approver)."""

    __tablename__ = "roles"

    role_id: Mapped[int_pk]
    name: Mapped[str_255] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[str_text | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())

    # Relationships
    permissions: Mapped[list[Permission]] = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
    )


class Permission(Base):
    """Fine-grained permissions (e.g., calculation.approve, project.delete)."""

    __tablename__ = "permissions"

    permission_id: Mapped[int_pk]
    resource: Mapped[str_255] = mapped_column(String(100), index=True)  # e.g., "calculation", "project"
    action: Mapped[str_255] = mapped_column(String(100), index=True)  # e.g., "approve", "delete", "read"
    description: Mapped[str_text | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())

    # Relationships
    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
    )


# Association table for many-to-many relationship
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.role_id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.permission_id"), primary_key=True),
)


class UserRole(Base):
    """User-role assignments per account."""

    __tablename__ = "user_roles"

    assignment_id: Mapped[int_pk]
    user_id: Mapped[str_255] = mapped_column(String(255), index=True)
    account_id: Mapped[str_255] = mapped_column(String(255), index=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.role_id"), index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())
    assigned_by: Mapped[str_255 | None] = mapped_column(String(255), nullable=True)

    # Relationships
    role: Mapped[Role] = relationship("Role")


# File Upload Models

class FileUpload(Base):
    """File upload metadata with virus scanning and access control."""

    __tablename__ = "file_uploads"

    upload_id: Mapped[int_pk]
    file_key: Mapped[str_255] = mapped_column(String(500), unique=True, index=True)  # Storage key (R2/S3)
    filename: Mapped[str_255]
    content_type: Mapped[str_255] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str_255] = mapped_column(String(64), index=True)  # File integrity hash
    virus_scan_status: Mapped[str_255] = mapped_column(String(50), default="pending")  # pending, clean, infected, error
    virus_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    thumbnail_key: Mapped[str_255 | None] = mapped_column(String(500), nullable=True)  # Generated thumbnail
    project_id: Mapped[str_255 | None] = mapped_column(String(255), nullable=True, index=True)
    uploaded_by: Mapped[str_255] = mapped_column(String(255), index=True)
    account_id: Mapped[str_255] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # Optional expiration


# CRM Integration Models

class CRMWebhook(Base):
    """CRM webhook events for syncing with KeyedIn CRM."""

    __tablename__ = "crm_webhooks"

    webhook_id: Mapped[int_pk]
    event_type: Mapped[str_255] = mapped_column(String(100), index=True)  # project.created, calculation.completed
    direction: Mapped[str_255] = mapped_column(String(20), index=True)  # inbound, outbound
    source: Mapped[str_255] = mapped_column(String(100))  # keyedin, calcusign
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str_255] = mapped_column(String(50), default="pending")  # pending, sent, delivered, failed
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str_text | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), index=True)


# Compliance Tracking Models

class ComplianceRecord(Base):
    """FAA and airport signage compliance tracking."""

    __tablename__ = "compliance_records"

    record_id: Mapped[int_pk]
    project_id: Mapped[str_255] = mapped_column(String(255), index=True)
    requirement_type: Mapped[str_255] = mapped_column(String(100), index=True)  # faa_breakaway, wind_load, material_cert
    requirement_code: Mapped[str_255] = mapped_column(String(50))  # e.g., "FAA-AC-70/7460-1L"
    status: Mapped[str_255] = mapped_column(String(50), default="pending")  # pending, compliant, non_compliant, exempt
    compliance_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # Detailed compliance data
    verified_by: Mapped[str_255 | None] = mapped_column(String(255), nullable=True)  # PE stamp user_id
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str_text | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())


class PEStamp(Base):
    """Professional Engineer stamp/certification for calculations."""

    __tablename__ = "pe_stamps"

    stamp_id: Mapped[int_pk]
    project_id: Mapped[str_255] = mapped_column(String(255), index=True)
    calculation_id: Mapped[str_255 | None] = mapped_column(String(255), nullable=True, index=True)
    pe_user_id: Mapped[str_255] = mapped_column(String(255), index=True)  # Licensed PE user
    pe_license_number: Mapped[str_255] = mapped_column(String(100))
    pe_state: Mapped[str_255] = mapped_column(String(2))  # Two-letter state code
    stamp_type: Mapped[str_255] = mapped_column(String(50))  # structural, foundation, electrical
    methodology: Mapped[str_text] = mapped_column(Text)  # Calculation methodology used
    code_references: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)  # ASCE, AISC, etc.
    stamped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), index=True)
    pdf_url: Mapped[str_255 | None] = mapped_column(String(500), nullable=True)  # Link to stamped PDF
    is_revoked: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str_text | None] = mapped_column(Text, nullable=True)

