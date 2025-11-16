"""Compliance and PE stamping endpoints."""

from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..auth import get_current_user, TokenData
from ..rbac import require_permission
from ..compliance import (
    check_compliance,
    get_project_compliance,
    verify_breakaway_compliance,
    verify_wind_load_compliance,
    create_pe_stamp,
)
from ..schemas import ResponseEnvelope
from ..common.models import make_envelope
from ..deps import get_code_version, get_model_config

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])


class ComplianceCheckRequest(BaseModel):
    """Request for compliance check."""
    requirement_type: str = Field(..., description="Type: breakaway, wind_load, material_cert, foundation")
    compliance_data: dict = Field(..., description="Detailed compliance data")
    notes: Optional[str] = None


class BreakawayCheckRequest(BaseModel):
    """Request for breakaway compliance check."""
    pole_height_ft: float
    base_diameter_in: float
    material: str


class WindLoadCheckRequest(BaseModel):
    """Request for wind load compliance check."""
    wind_speed_mph: float
    exposure: str = Field(..., description="B, C, or D")
    calculated_load_psf: float
    code_reference: str = Field(default="ASCE-7")


class PEStampRequest(BaseModel):
    """Request for PE stamp."""
    pe_license_number: str
    pe_state: str = Field(..., min_length=2, max_length=2, description="Two-letter state code")
    stamp_type: str = Field(..., description="structural, foundation, electrical")
    methodology: str
    code_references: list[str]
    calculation_id: Optional[str] = None
    pdf_url: Optional[str] = None


@router.post("/projects/{project_id}/check", response_model=ResponseEnvelope)
@require_permission("compliance.check")
async def check_project_compliance(
    project_id: str,
    req: ComplianceCheckRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Check compliance with FAA/airport requirements."""
    record = await check_compliance(
        db=db,
        project_id=project_id,
        requirement_type=req.requirement_type,
        compliance_data=req.compliance_data,
        verified_by=current_user.user_id,
        notes=req.notes,
    )
    
    return make_envelope(
        result={
            "record_id": record.record_id,
            "project_id": record.project_id,
            "requirement_type": record.requirement_type,
            "requirement_code": record.requirement_code,
            "status": record.status,
            "verified_at": record.verified_at.isoformat() if record.verified_at else None,
        },
        assumptions=[],
        confidence=0.95,
        inputs={"project_id": project_id, "requirement_type": req.requirement_type},
        outputs={"status": record.status},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.post("/projects/{project_id}/breakaway", response_model=ResponseEnvelope)
@require_permission("compliance.check")
async def check_breakaway(
    project_id: str,
    req: BreakawayCheckRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Verify breakaway compliance per FAA-AC-70/7460-1L."""
    record = await verify_breakaway_compliance(
        db=db,
        project_id=project_id,
        pole_height_ft=req.pole_height_ft,
        base_diameter_in=req.base_diameter_in,
        material=req.material,
        verified_by=current_user.user_id,
    )
    
    return make_envelope(
        result={
            "record_id": record.record_id,
            "status": record.status,
            "compliance_data": record.compliance_data,
        },
        assumptions=["Breakaway check per FAA-AC-70/7460-1L"],
        confidence=0.95,
        inputs={
            "pole_height_ft": req.pole_height_ft,
            "material": req.material,
        },
        outputs={"status": record.status},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.post("/projects/{project_id}/wind-load", response_model=ResponseEnvelope)
@require_permission("compliance.check")
async def check_wind_load(
    project_id: str,
    req: WindLoadCheckRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Verify wind load compliance per ASCE 7."""
    record = await verify_wind_load_compliance(
        db=db,
        project_id=project_id,
        wind_speed_mph=req.wind_speed_mph,
        exposure=req.exposure,
        calculated_load_psf=req.calculated_load_psf,
        code_reference=req.code_reference,
        verified_by=current_user.user_id,
    )
    
    return make_envelope(
        result={
            "record_id": record.record_id,
            "status": record.status,
            "compliance_data": record.compliance_data,
        },
        assumptions=[f"Wind load check per {req.code_reference}"],
        confidence=0.95,
        inputs={
            "wind_speed_mph": req.wind_speed_mph,
            "exposure": req.exposure,
        },
        outputs={"status": record.status},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.get("/projects/{project_id}", response_model=ResponseEnvelope)
async def get_project_compliance_records(
    project_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Get all compliance records for a project."""
    records = await get_project_compliance(db=db, project_id=project_id)
    
    return make_envelope(
        result=[
            {
                "record_id": r.record_id,
                "requirement_type": r.requirement_type,
                "requirement_code": r.requirement_code,
                "status": r.status,
                "verified_at": r.verified_at.isoformat() if r.verified_at else None,
                "notes": r.notes,
            }
            for r in records
        ],
        assumptions=[],
        confidence=1.0,
        inputs={"project_id": project_id},
        outputs={"count": len(records)},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.post("/projects/{project_id}/pe-stamp", response_model=ResponseEnvelope)
@require_permission("calculation.stamp")
async def create_pe_stamp_endpoint(
    project_id: str,
    req: PEStampRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Create Professional Engineer stamp for calculation.
    
    Requires: calculation.stamp permission (PE role)
    """
    stamp = await create_pe_stamp(
        db=db,
        project_id=project_id,
        pe_user_id=current_user.user_id,
        pe_license_number=req.pe_license_number,
        pe_state=req.pe_state,
        stamp_type=req.stamp_type,
        methodology=req.methodology,
        code_references=req.code_references,
        calculation_id=req.calculation_id,
        pdf_url=req.pdf_url,
    )
    
    return make_envelope(
        result={
            "stamp_id": stamp.stamp_id,
            "project_id": stamp.project_id,
            "pe_state": stamp.pe_state,
            "pe_license_number": stamp.pe_license_number,
            "stamp_type": stamp.stamp_type,
            "stamped_at": stamp.stamped_at.isoformat(),
            "pdf_url": stamp.pdf_url,
        },
        assumptions=["PE stamp created per state licensing requirements"],
        confidence=1.0,
        inputs={
            "project_id": project_id,
            "pe_state": req.pe_state,
            "stamp_type": req.stamp_type,
        },
        outputs={"stamp_id": stamp.stamp_id},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )

