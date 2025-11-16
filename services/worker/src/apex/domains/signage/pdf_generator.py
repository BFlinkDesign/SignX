"""PDF report generation using ReportLab."""

import hashlib
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table


def generate_project_pdf(project_data: dict[str, Any]) -> tuple[bytes, str]:
    """Generate a 4-page project report PDF.
    
    Args:
        project_data: Project data dictionary with:
            - project_id: Project identifier
            - site: Site information dict
            - design: Design parameters dict
            - cost_estimate: Cost breakdown dict
    
    Returns:
        Tuple of (PDF bytes, SHA256 hexdigest)
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#1a472a"),
        spaceAfter=30,
    )
    
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=16,
        textColor=colors.HexColor("#2d5016"),
        spaceAfter=12,
    )
    
    story = []
    
    # Page 1: Cover
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph("CalcuSign Project Report", title_style))
    story.append(Spacer(1, 0.5 * inch))
    
    project_id = project_data.get("project_id", "N/A")
    story.append(Paragraph(f"Project ID: {project_id}", styles["Normal"]))
    story.append(PageBreak())
    
    # Page 2: Site Information
    story.append(Paragraph("Site Information", heading_style))
    story.append(Spacer(1, 0.3 * inch))
    
    site = project_data.get("site", {})
    summary_data = [
        ["Property", "Value"],
        ["Project ID", project_id],
        ["Address", site.get("address", "N/A")],
        ["Wind Speed", f"{site.get('wind_speed_mph', 0)} mph"],
        ["Exposure", site.get("exposure", "N/A")],
        ["Snow Load", f"{site.get('snow_load_psf', 0)} psf"],
    ]
    
    summary_table = Table(summary_data, colWidths=[2 * inch, 4 * inch])
    summary_table.setStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
    ])
    story.append(summary_table)
    story.append(PageBreak())
    
    # Page 3: Design Summary
    story.append(Paragraph("Design Summary", heading_style))
    story.append(Spacer(1, 0.3 * inch))
    
    design = project_data.get("design", {})
    design_data = [
        ["Parameter", "Value"],
        ["Foundation Type", design.get("foundation_type", "N/A")],
        ["Pole Type", design.get("pole_type", "N/A")],
        ["Sign Area", f"{design.get('sign_area_sqft', 0)} sq ft"],
    ]
    
    design_table = Table(design_data, colWidths=[2 * inch, 4 * inch])
    design_table.setStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
    ])
    story.append(design_table)
    story.append(PageBreak())
    
    # Page 4: Cost Estimate
    story.append(Paragraph("Cost Estimate", heading_style))
    story.append(Spacer(1, 0.3 * inch))
    
    cost = project_data.get("cost_estimate", {})
    cost_data = [
        ["Item", "Unit Cost", "Quantity", "Total"],
        ["Materials", f"${cost.get('materials', 0)}", "1", f"${cost.get('materials', 0)}"],
        ["Labor", f"${cost.get('labor', 0)}", "1", f"${cost.get('labor', 0)}"],
        ["Equipment", f"${cost.get('equipment', 0)}", "1", f"${cost.get('equipment', 0)}"],
    ]
    
    total = sum([cost.get("materials", 0), cost.get("labor", 0), cost.get("equipment", 0)])
    cost_data.append(["TOTAL", "", "", f"${total}"])
    
    cost_table = Table(cost_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch, 1 * inch])
    cost_table.setStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -2), colors.beige),
        ("BACKGROUND", (0, -1), (-1, -1), colors.lightblue),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
    ])
    story.append(cost_table)
    story.append(Spacer(1, 0.5 * inch))
    
    # Footer note
    story.append(Paragraph(
        "This report was generated automatically by CalcuSign.<br/>"
        "All calculations are based on current engineering standards.",
        styles["Normal"]
    ))
    
    # Build PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, sha256_hash

