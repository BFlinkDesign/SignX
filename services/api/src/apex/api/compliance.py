"""FAA and airport signage compliance tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .models_audit import ComplianceRecord, PEStamp
from .audit import log_audit

logger = structlog.get_logger(__name__)


# FAA Requirements
FAA_REQUIREMENTS = {
    "breakaway": {
        "code": "FAA-AC-70/7460-1L",
        "title": "Breakaway Sign Support Structures",
        "description": "Sign supports must break away upon impact without causing injury",
        "validation_required": True,
    },
    "wind_load": {
        "code": "ASCE-7",
        "title": "Minimum Design Loads",
        "description": "Wind load calculations per ASCE 7 standards",
        "validation_required": True,
    },
    "material_cert": {
        "code": "ASTM-A36",
        "title": "Material Certification",
        "description": "Materials must be certified per ASTM/AISC standards",
        "validation_required": False,
    },
    "foundation": {
        "code": "ACI-318",
        "title": "Foundation Design",
        "description": "Foundation design per ACI 318 building code",
        "validation_required": True,
    },
}


async def check_compliance(
    db: AsyncSession,
    project_id: str,
    requirement_type: str,
    compliance_data: dict,
    verified_by: Optional[str] = None,
    notes: Optional[str] = None,
) -> ComplianceRecord:
    """Check and record compliance with FAA/airport requirements.
    
    Args:
        db: Database session
        project_id: Project ID
        requirement_type: Type of requirement (e.g., "breakaway", "wind_load")
        compliance_data: Detailed compliance data
        verified_by: User ID of verifier (PE for stamped calculations)
        notes: Optional compliance notes
    
    Returns:
        ComplianceRecord instance
    """
    requirement = FAA_REQUIREMENTS.get(requirement_type)
    if not requirement:
        raise ValueError(f"Unknown requirement type: {requirement_type}")
    
    # Determine compliance status
    status = compliance_data.get("status", "pending")
    if status not in ["pending", "compliant", "non_compliant", "exempt"]:
        status = "pending"
    
    # Check if record already exists
    existing = await db.execute(
        select(ComplianceRecord).where(
            ComplianceRecord.project_id == project_id,
            ComplianceRecord.requirement_type == requirement_type,
        )
    )
    record = existing.scalar_one_or_none()
    
    if record:
        # Update existing record
        record.status = status
        record.compliance_data = compliance_data
        record.verified_by = verified_by
        record.verified_at = datetime.now(timezone.utc) if verified_by else None
        record.notes = notes
        await db.commit()
        await db.refresh(record)
    else:
        # Create new record
        record = ComplianceRecord(
            project_id=project_id,
            requirement_type=requirement_type,
            requirement_code=requirement["code"],
            status=status,
            compliance_data=compliance_data,
            verified_by=verified_by,
            verified_at=datetime.now(timezone.utc) if verified_by else None,
            notes=notes,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
    
    # Log audit
    await log_audit(
        db=db,
        action="compliance.checked",
        resource_type="compliance",
        resource_id=str(record.record_id),
        after_state={
            "requirement_type": requirement_type,
            "status": status,
            "verified_by": verified_by,
        },
        user_id=verified_by or "system",
        account_id="unknown",  # Should be extracted from project
    )
    
    logger.info(
        "compliance.recorded",
        project_id=project_id,
        requirement_type=requirement_type,
        status=status,
    )
    
    return record


async def get_project_compliance(
    db: AsyncSession,
    project_id: str,
) -> list[ComplianceRecord]:
    """Get all compliance records for a project."""
    result = await db.execute(
        select(ComplianceRecord).where(ComplianceRecord.project_id == project_id)
    )
    return list(result.scalars().all())


async def verify_breakaway_compliance(
    db: AsyncSession,
    project_id: str,
    pole_height_ft: float,
    base_diameter_in: float,
    material: str,
    verified_by: Optional[str] = None,
) -> ComplianceRecord:
    """Verify breakaway compliance per FAA-AC-70/7460-1L.
    
    Breakaway requirement: Sign support must break away upon impact
    without causing injury to vehicle occupants.
    
    Simplified check: Pole height > 40ft requires breakaway design.
    """
    is_compliant = pole_height_ft <= 40.0 or material in ["breakaway", "frangible"]
    
    compliance_data = {
        "pole_height_ft": pole_height_ft,
        "base_diameter_in": base_diameter_in,
        "material": material,
        "requires_breakaway": pole_height_ft > 40.0,
        "is_compliant": is_compliant,
        "check_date": datetime.now(timezone.utc).isoformat(),
    }
    
    status = "compliant" if is_compliant else "non_compliant"
    
    return await check_compliance(
        db=db,
        project_id=project_id,
        requirement_type="breakaway",
        compliance_data=compliance_data,
        verified_by=verified_by,
        notes=f"Breakaway check: Pole height {pole_height_ft}ft, Material: {material}",
    )


async def verify_wind_load_compliance(
    db: AsyncSession,
    project_id: str,
    wind_speed_mph: float,
    exposure: str,
    calculated_load_psf: float,
    code_reference: str = "ASCE-7",
    verified_by: Optional[str] = None,
) -> ComplianceRecord:
    """Verify wind load compliance per ASCE 7.
    
    Checks that calculated wind loads meet minimum design requirements.
    """
    # Simplified: Check if wind load calculation is reasonable
    # In production, this would validate against ASCE 7 tables
    is_compliant = calculated_load_psf > 0 and calculated_load_psf <= 200  # Reasonable range
    
    compliance_data = {
        "wind_speed_mph": wind_speed_mph,
        "exposure": exposure,
        "calculated_load_psf": calculated_load_psf,
        "code_reference": code_reference,
        "is_compliant": is_compliant,
        "check_date": datetime.now(timezone.utc).isoformat(),
    }
    
    status = "compliant" if is_compliant else "non_compliant"
    
    return await check_compliance(
        db=db,
        project_id=project_id,
        requirement_type="wind_load",
        compliance_data=compliance_data,
        verified_by=verified_by,
        notes=f"Wind load: {calculated_load_psf} psf at {wind_speed_mph} mph, Exposure: {exposure}",
    )


async def create_pe_stamp(
    db: AsyncSession,
    project_id: str,
    pe_user_id: str,
    pe_license_number: str,
    pe_state: str,
    stamp_type: str,
    methodology: str,
    code_references: list[str],
    calculation_id: Optional[str] = None,
    pdf_url: Optional[str] = None,
) -> PEStamp:
    """Create Professional Engineer stamp for calculation.
    
    Args:
        db: Database session
        project_id: Project ID
        pe_user_id: User ID of licensed PE
        pe_license_number: PE license number
        pe_state: Two-letter state code
        stamp_type: Type of stamp (structural, foundation, electrical)
        methodology: Calculation methodology used
        code_references: List of code references (ASCE, AISC, etc.)
        calculation_id: Optional specific calculation ID
        pdf_url: Optional link to stamped PDF
    
    Returns:
        PEStamp instance
    """
    stamp = PEStamp(
        project_id=project_id,
        calculation_id=calculation_id,
        pe_user_id=pe_user_id,
        pe_license_number=pe_license_number,
        pe_state=pe_state,
        stamp_type=stamp_type,
        methodology=methodology,
        code_references=code_references,
        pdf_url=pdf_url,
    )
    
    db.add(stamp)
    await db.commit()
    await db.refresh(stamp)
    
    # Log audit
    await log_audit(
        db=db,
        action="calculation.pe_stamped",
        resource_type="calculation",
        resource_id=calculation_id or project_id,
        after_state={
            "pe_license_number": pe_license_number,
            "pe_state": pe_state,
            "stamp_type": stamp_type,
        },
        user_id=pe_user_id,
        account_id="unknown",
    )
    
    logger.info(
        "pe.stamp_created",
        stamp_id=stamp.stamp_id,
        project_id=project_id,
        pe_state=pe_state,
    )
    
    return stamp

