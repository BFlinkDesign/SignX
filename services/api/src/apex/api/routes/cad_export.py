"""CAD export routes for fabrication drawings.

Exports foundation plans, rebar schedules, and anchor bolt layouts
in multiple formats (DXF, DWG, AI, CDR).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..common.models import make_envelope
from ..deps import get_code_version, get_model_config
from ..schemas import ResponseEnvelope, add_assumption
from ...domains.signage.services.cad_export_service import (
    CADExportService,
    CADExportOptions,
    CADFormat,
    DrawingScale,
)
from ...domains.signage.services.concrete_rebar_service import (
    ConcreteRebarService,
    RebarScheduleInput,
    FoundationType,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/cad", tags=["cad-export"])


# Request/Response Schemas
class CADFormatEnum(str, Enum):
    """Supported CAD export format (DXF only)."""
    DXF = "dxf"


class DrawingScaleEnum(str, Enum):
    """Architectural drawing scales."""
    QUARTER_INCH = "1/4\"=1'-0\""
    HALF_INCH = "1/2\"=1'-0\""
    ONE_INCH = "1\"=1'-0\""
    THREE_INCH = "3\"=1'-0\""


class AnchorBoltLayoutRequest(BaseModel):
    """Anchor bolt layout specification."""
    num_bolts: int = Field(..., ge=4, le=12, description="Number of anchor bolts (4-12)")
    bolt_diameter_in: float = Field(..., gt=0, le=3, description="Bolt diameter in inches")
    bolt_circle_diameter_ft: float = Field(..., gt=0, description="Bolt circle diameter in feet")
    projection_in: float = Field(..., gt=0, description="Projection above concrete in inches")
    embedment_in: float = Field(..., gt=0, description="Embedment depth in inches")


class FoundationPlanRequest(BaseModel):
    """Request for foundation plan CAD export."""

    # Foundation geometry
    foundation_type: str = Field(..., description="Foundation type (direct_burial, pier_and_grade_beam, etc.)")
    diameter_ft: float = Field(..., gt=0, le=10, description="Foundation diameter in feet")
    depth_ft: float = Field(..., gt=0, le=20, description="Foundation depth in feet")

    # Concrete properties
    fc_ksi: float = Field(3.0, gt=0, le=10, description="Concrete compressive strength (ksi)")

    # Rebar design
    fy_ksi: float = Field(60.0, gt=0, description="Rebar yield strength (ksi)")
    cover_in: float = Field(3.0, gt=0, description="Concrete cover (inches)")

    # Anchor bolts (optional)
    anchor_layout: Optional[AnchorBoltLayoutRequest] = Field(None, description="Anchor bolt layout")

    # Export options
    format: CADFormatEnum = Field(CADFormatEnum.DXF, description="Export format (DXF only)")
    scale: DrawingScaleEnum = Field(DrawingScaleEnum.QUARTER_INCH, description="Drawing scale")

    # Title block
    project_name: str = Field("Untitled Project", description="Project name for title block")
    drawing_number: str = Field("FND-001", description="Drawing number")
    engineer: Optional[str] = Field(None, description="Engineer name/stamp")


class CADExportResponse(BaseModel):
    """Metadata about generated CAD file."""
    filename: str = Field(..., description="Generated filename")
    format: str = Field(..., description="CAD format (dxf, dwg, ai, cdr)")
    file_size_bytes: int = Field(..., description="File size in bytes")
    num_entities: int = Field(..., description="Number of CAD entities")
    layers: list[str] = Field(..., description="Layer names in drawing")
    warnings: list[str] = Field(default_factory=list, description="Export warnings")


# Helper to convert Pydantic enums to service enums
def _to_cad_format(fmt: CADFormatEnum) -> CADFormat:
    """Convert API enum to service enum."""
    mapping = {
        CADFormatEnum.DXF: CADFormat.DXF,
        CADFormatEnum.DWG: CADFormat.DWG,
        CADFormatEnum.AI: CADFormat.AI,
        CADFormatEnum.CDR: CADFormat.CDR,
    }
    return mapping[fmt]


def _to_drawing_scale(scale: DrawingScaleEnum) -> DrawingScale:
    """Convert API enum to service enum."""
    mapping = {
        DrawingScaleEnum.QUARTER_INCH: DrawingScale.QUARTER_INCH,
        DrawingScaleEnum.HALF_INCH: DrawingScale.HALF_INCH,
        DrawingScaleEnum.ONE_INCH: DrawingScale.ONE_INCH,
        DrawingScaleEnum.THREE_INCH: DrawingScale.THREE_INCH,
    }
    return mapping[scale]


@router.post("/export/foundation", response_model=ResponseEnvelope)
async def export_foundation_plan(
    req: FoundationPlanRequest,
    model_config=Depends(get_model_config),
    code_version=Depends(get_code_version),
) -> ResponseEnvelope:
    """Generate CAD drawing for foundation plan with rebar schedule.

    This endpoint generates fabrication-ready CAD drawings including:
    - Foundation plan view (top)
    - Foundation section view (side cut)
    - Rebar schedule table with bar marks, sizes, quantities
    - Anchor bolt layout (if provided)
    - Dimensions and annotations
    - Title block with project metadata

    The drawing follows AIA standard layer conventions and includes
    all necessary details for shop fabrication.

    Returns:
        Envelope containing CADExportResponse with metadata.
        The actual CAD file bytes are in the trace.data.artifacts field.
    """
    logger.info(
        "cad_export.foundation",
        diameter_ft=req.diameter_ft,
        depth_ft=req.depth_ft,
        format=req.format,
    )

    assumptions: list[str] = []
    warnings: list[str] = []

    try:
        # Step 1: Design rebar schedule using ConcreteRebarService
        rebar_service = ConcreteRebarService()

        # Convert foundation type string to enum
        try:
            foundation_type = FoundationType[req.foundation_type.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid foundation type: {req.foundation_type}. "
                f"Valid types: {[t.value for t in FoundationType]}"
            )

        rebar_input = RebarScheduleInput(
            foundation_type=foundation_type,
            diameter_ft=req.diameter_ft,
            depth_ft=req.depth_ft,
            fc_ksi=req.fc_ksi,
            fy_ksi=req.fy_ksi,
            cover_in=req.cover_in,
        )

        rebar_result = rebar_service.design_rebar_schedule(rebar_input)
        add_assumption(
            assumptions,
            f"Rebar design per ACI 318-19: {len(rebar_result.vertical_bars)} vertical bars, "
            f"{len(rebar_result.horizontal_bars)} horizontal bars"
        )

        # Step 2: Prepare anchor bolt layout (if provided)
        anchor_layout_data = None
        if req.anchor_layout:
            anchor_layout_data = {
                "num_bolts": req.anchor_layout.num_bolts,
                "bolt_diameter_in": req.anchor_layout.bolt_diameter_in,
                "bolt_circle_diameter_ft": req.anchor_layout.bolt_circle_diameter_ft,
                "projection_in": req.anchor_layout.projection_in,
                "embedment_in": req.anchor_layout.embedment_in,
            }
            add_assumption(
                assumptions,
                f"Anchor bolts: {req.anchor_layout.num_bolts} × ∅{req.anchor_layout.bolt_diameter_in}\" "
                f"on {req.anchor_layout.bolt_circle_diameter_ft}' BC"
            )

        # Step 3: Prepare export options
        cad_options = CADExportOptions(
            format=_to_cad_format(req.format),
            scale=_to_drawing_scale(req.scale),
            include_dimensions=True,
            include_rebar_schedule=True,
            include_title_block=True,
            title_block_data={
                "project_name": req.project_name,
                "drawing_number": req.drawing_number,
                "engineer": req.engineer or "Not Specified",
                "title": "Foundation Plan with Rebar Schedule",
            },
        )

        # Step 4: Generate CAD file
        cad_service = CADExportService()

        file_bytes, export_result = cad_service.export_foundation_plan(
            rebar_schedule=rebar_result,
            diameter_ft=req.diameter_ft,
            depth_ft=req.depth_ft,
            anchor_layout=anchor_layout_data,
            options=cad_options,
        )

        # Check for warnings from export
        if export_result.warnings:
            warnings.extend(export_result.warnings)
            for warning in export_result.warnings:
                add_assumption(assumptions, f"Warning: {warning}")

        # Step 5: Build response
        response_data = CADExportResponse(
            filename=export_result.filename,
            format=export_result.format.value,
            file_size_bytes=export_result.file_size_bytes,
            num_entities=export_result.num_entities,
            layers=export_result.layers,
            warnings=warnings,
        )

        add_assumption(assumptions, f"Drawing scale: {req.scale.value}")
        add_assumption(assumptions, f"Export format: {req.format.value.upper()}")
        add_assumption(assumptions, f"AIA standard layers used: {len(export_result.layers)}")

        # Return envelope with metadata (file bytes in artifacts)
        return make_envelope(
            result=response_data.model_dump(),
            assumptions=assumptions,
            confidence=1.0 if not warnings else 0.95,
            inputs={
                "foundation_type": req.foundation_type,
                "diameter_ft": req.diameter_ft,
                "depth_ft": req.depth_ft,
                "format": req.format.value,
            },
            intermediates={
                "rebar_schedule": {
                    "vertical_bars": len(rebar_result.vertical_bars),
                    "horizontal_bars": len(rebar_result.horizontal_bars),
                    "total_weight_lb": rebar_result.total_rebar_weight_lb,
                },
            },
            outputs={
                "filename": export_result.filename,
                "file_size_bytes": export_result.file_size_bytes,
                "num_entities": export_result.num_entities,
            },
            artifacts=[
                {
                    "type": "cad_drawing",
                    "format": req.format.value,
                    "filename": export_result.filename,
                    "size_bytes": export_result.file_size_bytes,
                    "base64_data": file_bytes.hex(),  # Hex encoding for binary data
                }
            ],
            code_version=code_version,
            model_config=model_config,
        )

    except ValueError as e:
        logger.error("cad_export.validation_error", error=str(e))
        raise HTTPException(status_code=400, detail=f"Validation error: {e}")

    except Exception as e:
        logger.error("cad_export.unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"CAD export failed: {e}")


@router.post("/download/foundation")
async def download_foundation_plan(
    req: FoundationPlanRequest,
) -> Response:
    """Download foundation plan CAD file directly (no envelope).

    This endpoint generates and returns the raw CAD file for direct download.
    Use this when you want the CAD file directly instead of JSON metadata.

    Returns:
        Binary CAD file with appropriate Content-Disposition header.
    """
    logger.info(
        "cad_download.foundation",
        diameter_ft=req.diameter_ft,
        format=req.format,
    )

    try:
        # Design rebar schedule
        rebar_service = ConcreteRebarService()
        foundation_type = FoundationType[req.foundation_type.upper()]

        rebar_input = RebarScheduleInput(
            foundation_type=foundation_type,
            diameter_ft=req.diameter_ft,
            depth_ft=req.depth_ft,
            fc_ksi=req.fc_ksi,
            fy_ksi=req.fy_ksi,
            cover_in=req.cover_in,
        )

        rebar_result = rebar_service.design_rebar_schedule(rebar_input)

        # Prepare anchor layout
        anchor_layout_data = None
        if req.anchor_layout:
            anchor_layout_data = {
                "num_bolts": req.anchor_layout.num_bolts,
                "bolt_diameter_in": req.anchor_layout.bolt_diameter_in,
                "bolt_circle_diameter_ft": req.anchor_layout.bolt_circle_diameter_ft,
                "projection_in": req.anchor_layout.projection_in,
                "embedment_in": req.anchor_layout.embedment_in,
            }

        # Export options
        cad_options = CADExportOptions(
            format=_to_cad_format(req.format),
            scale=_to_drawing_scale(req.scale),
            include_dimensions=True,
            include_rebar_schedule=True,
            include_title_block=True,
            title_block_data={
                "project_name": req.project_name,
                "drawing_number": req.drawing_number,
                "engineer": req.engineer or "Not Specified",
                "title": "Foundation Plan with Rebar Schedule",
            },
        )

        # Generate CAD file
        cad_service = CADExportService()
        file_bytes, export_result = cad_service.export_foundation_plan(
            rebar_schedule=rebar_result,
            diameter_ft=req.diameter_ft,
            depth_ft=req.depth_ft,
            anchor_layout=anchor_layout_data,
            options=cad_options,
        )

        # DXF MIME type
        mime_type = "application/dxf"

        # Return raw file with download headers
        return Response(
            content=file_bytes,
            media_type=mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{export_result.filename}"',
                "X-File-Size": str(export_result.file_size_bytes),
                "X-CAD-Format": req.format.value.upper(),
                "X-Num-Entities": str(export_result.num_entities),
            }
        )

    except ValueError as e:
        logger.error("cad_download.validation_error", error=str(e))
        raise HTTPException(status_code=400, detail=f"Validation error: {e}")

    except Exception as e:
        logger.error("cad_download.unexpected_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"CAD download failed: {e}")
