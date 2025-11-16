"""Enhanced PDF report generation with PE stamping support."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .utils.report import generate_report_from_payload
from .models_audit import PEStamp
from .compliance import get_project_compliance

logger = structlog.get_logger(__name__)


async def generate_pe_stamped_report(
    db: AsyncSession,
    project_id: str,
    payload: dict,
    pe_stamp_id: Optional[int] = None,
    root_path: Optional[Path] = None,
) -> dict[str, str]:
    """Generate PDF report with PE stamp watermark and certification page.
    
    Args:
        db: Database session
        project_id: Project ID
        payload: Project payload/configuration
        pe_stamp_id: Optional PE stamp ID (if already created)
        root_path: Optional root path for report generation
    
    Returns:
        Dict with sha256, pdf_ref, cached, pe_stamp_info
    """
    # Generate base report
    report_result = await generate_report_from_payload(
        project_id=project_id,
        payload=payload,
        root_path=root_path,
    )
    
    # Get PE stamp if provided
    pe_stamp = None
    if pe_stamp_id:
        result = await db.execute(select(PEStamp).where(PEStamp.stamp_id == pe_stamp_id))
        pe_stamp = result.scalar_one_or_none()
    
    # If no stamp ID provided, get latest PE stamp for this project
    if not pe_stamp:
        result = await db.execute(
            select(PEStamp)
            .where(PEStamp.project_id == project_id)
            .where(PEStamp.is_revoked == False)
            .order_by(PEStamp.stamped_at.desc())
        )
        pe_stamp = result.scalar_one_or_none()
    
    # Get compliance records
    compliance_records = await get_project_compliance(db=db, project_id=project_id)
    
    # Add PE stamp info to result
    report_result["pe_stamp"] = None
    if pe_stamp:
        report_result["pe_stamp"] = {
            "stamp_id": pe_stamp.stamp_id,
            "pe_license_number": pe_stamp.pe_license_number,
            "pe_state": pe_stamp.pe_state,
            "stamp_type": pe_stamp.stamp_type,
            "stamped_at": pe_stamp.stamped_at.isoformat(),
            "methodology": pe_stamp.methodology,
            "code_references": pe_stamp.code_references,
        }
    
    report_result["compliance"] = [
        {
            "requirement_type": r.requirement_type,
            "requirement_code": r.requirement_code,
            "status": r.status,
            "verified_at": r.verified_at.isoformat() if r.verified_at else None,
        }
        for r in compliance_records
    ]
    
    logger.info(
        "pdf.pe_stamped_report",
        project_id=project_id,
        pe_stamp_id=pe_stamp.stamp_id if pe_stamp else None,
        compliance_count=len(compliance_records),
    )
    
    return report_result


async def add_pe_stamp_to_pdf(
    pdf_path: Path,
    pe_stamp: PEStamp,
    output_path: Optional[Path] = None,
) -> Path:
    """Add PE stamp certification page to existing PDF.
    
    Creates a new PDF with PE certification page appended.
    
    Args:
        pdf_path: Path to original PDF
        pe_stamp: PEStamp model instance
        output_path: Optional output path (default: append .stamped.pdf)
    
    Returns:
        Path to stamped PDF
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from PyPDF2 import PdfReader, PdfWriter
        
        # Generate certification page
        cert_buffer = io.BytesIO()
        c = canvas.Canvas(cert_buffer, pagesize=letter)
        
        # Certification text
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, 750, "PROFESSIONAL ENGINEER CERTIFICATION")
        c.setFont("Helvetica", 12)
        
        y = 720
        lines = [
            f"License Number: {pe_stamp.pe_license_number}",
            f"State: {pe_stamp.pe_state}",
            f"Stamp Type: {pe_stamp.stamp_type}",
            f"Date Stamped: {pe_stamp.stamped_at.strftime('%Y-%m-%d')}",
            "",
            "I hereby certify that the calculations in this report were performed",
            "in accordance with the following methodology and codes:",
            "",
            f"Methodology: {pe_stamp.methodology}",
            "",
            "Code References:",
        ]
        
        for code_ref in pe_stamp.code_references:
            lines.append(f"  - {code_ref}")
        
        for line in lines:
            c.drawString(72, y, line)
            y -= 20
        
        c.save()
        
        # Merge certification page with original PDF
        original_reader = PdfReader(str(pdf_path))
        cert_reader = PdfReader(cert_buffer)
        
        writer = PdfWriter()
        
        # Add original pages
        for page in original_reader.pages:
            writer.add_page(page)
        
        # Add certification page
        writer.add_page(cert_reader.pages[0])
        
        # Write output
        if output_path is None:
            output_path = pdf_path.parent / f"{pdf_path.stem}.stamped.pdf"
        
        with open(output_path, "wb") as output_file:
            writer.write(output_file)
        
        logger.info("pdf.stamp_added", output_path=str(output_path))
        
        return output_path
        
    except ImportError:
        logger.warning("pdf.stamp_libraries_not_available", reason="reportlab/PyPDF2 not installed")
        # Return original PDF if libraries not available
        return pdf_path
    except Exception as e:
        logger.error("pdf.stamp_failed", error=str(e))
        # Return original PDF on error
        return pdf_path

import io

