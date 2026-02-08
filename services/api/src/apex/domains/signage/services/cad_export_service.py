"""
CAD Export Service - DXF Drawing Generation

Generates fabrication-ready DXF drawings for foundation plans.

DXF (Drawing Exchange Format) is the universal CAD interchange format
supported by AutoCAD, BricsCAD, QCAD, LibreCAD, and all major CAD systems.

Exports include:
- Rebar schedules with bar marks and placement
- Anchor bolt layouts with tolerances
- Foundation plans with dimensions
- Section details and callouts

Standards:
- AutoCAD DXF R2018 format
- AIA CAD Layer Guidelines (2nd Edition)
- ANSI Y14.5 (Dimensioning and tolerancing)

Author: SignX-Studio Engineering Team
Date: 2025-11-02
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from enum import Enum
from typing import Literal

import ezdxf
import structlog
from ezdxf.enums import TextEntityAlignment
from pydantic import BaseModel, Field

from ..exceptions import ValidationError
from .concrete_rebar_service import ConcreteVolume, RebarScheduleResult

logger = structlog.get_logger(__name__)


# ============================================================================
# Enums and Constants
# ============================================================================

class CADFormat(str, Enum):
    """Supported CAD export format (DXF only)."""
    DXF = "dxf"  # AutoCAD Drawing Exchange Format (universal)

class DrawingScale(str, Enum):
    """Standard architectural/engineering scales."""
    SCALE_1_1 = "1:1"      # Full size
    SCALE_1_2 = "1:2"      # Half size
    SCALE_1_4 = "1:4"      # Quarter size
    SCALE_3_8 = "3/8\"=1'-0\""  # 3/8 inch = 1 foot
    SCALE_1_2_ARCH = "1/2\"=1'-0\""  # Half inch = 1 foot
    SCALE_1_4_ARCH = "1/4\"=1'-0\""  # Quarter inch = 1 foot
    SCALE_1_8_ARCH = "1/8\"=1'-0\""  # Eighth inch = 1 foot

class LineType(str, Enum):
    """Standard line types for technical drawings."""
    CONTINUOUS = "CONTINUOUS"
    DASHED = "DASHED"
    CENTER = "CENTER"
    HIDDEN = "HIDDEN"
    PHANTOM = "PHANTOM"


# CAD layer names (AIA standard)
LAYER_DIMENSIONS = "A-ANNO-DIMS"
LAYER_TEXT = "A-ANNO-TEXT"
LAYER_REBAR = "S-DETL-RBAR"
LAYER_CONCRETE = "S-DETL-CONC"
LAYER_STEEL = "S-DETL-STEE"
LAYER_CENTERLINES = "A-ANNO-CNTR"
LAYER_GRID = "A-GRID"
LAYER_TITLE_BLOCK = "A-ANNO-TTLB"

# Drawing units (inches)
DRAWING_UNIT = "inches"

# Text heights (in drawing units)
TEXT_HEIGHT_TITLE = 0.25        # 1/4"
TEXT_HEIGHT_SUBTITLE = 0.1875   # 3/16"
TEXT_HEIGHT_NORMAL = 0.125      # 1/8"
TEXT_HEIGHT_SMALL = 0.0938      # 3/32"

# Colors (AutoCAD Color Index)
COLOR_RED = 1
COLOR_YELLOW = 2
COLOR_GREEN = 3
COLOR_CYAN = 4
COLOR_BLUE = 5
COLOR_MAGENTA = 6
COLOR_WHITE = 7
COLOR_GRAY = 8


# ============================================================================
# Data Models
# ============================================================================

class CADExportOptions(BaseModel):
    """Options for CAD export."""

    format: CADFormat = Field(
        default=CADFormat.DXF,
        description="Output CAD format (DXF only)"
    )

    scale: DrawingScale = Field(
        default=DrawingScale.SCALE_1_4_ARCH,
        description="Drawing scale (1/4\"=1'-0\" typical for foundations)"
    )

    include_title_block: bool = Field(
        default=True,
        description="Include title block with project info"
    )

    include_rebar_schedule: bool = Field(
        default=True,
        description="Include rebar schedule table"
    )

    include_dimensions: bool = Field(
        default=True,
        description="Include dimension annotations"
    )

    include_notes: bool = Field(
        default=True,
        description="Include general notes and callouts"
    )

    company_name: str | None = Field(
        None,
        description="Company name for title block"
    )

    project_name: str | None = Field(
        None,
        description="Project name for title block"
    )

    drawing_number: str | None = Field(
        None,
        description="Drawing number (e.g., 'S-101')"
    )

    engineer_seal: bool = Field(
        default=False,
        description="Include PE seal placeholder"
    )


@dataclass
class AnchorBoltLayout:
    """Anchor bolt pattern layout for base plates."""
    bolt_size: str  # e.g., "3/4\""
    num_bolts: int
    bolt_circle_diameter_in: float
    projection_in: float  # Above top of concrete
    embedment_in: float   # Into concrete
    edge_distance_in: float
    pattern: Literal["square", "circular", "rectangular"]


class CADExportResult(BaseModel):
    """Result from CAD export operation."""

    format: CADFormat
    filename: str
    file_size_bytes: int
    layers_created: list[str]
    entities_count: int
    drawing_bounds: dict[str, float]  # min_x, max_x, min_y, max_y

    class Config:
        frozen = True


# ============================================================================
# CAD Export Service
# ============================================================================

class CADExportService:
    """
    DXF CAD export service for fabrication drawings.

    Generates shop-ready DXF drawings including:
    - Foundation plans with rebar placement
    - Anchor bolt layouts with tolerances
    - Rebar schedules with bar marks
    - Section details and callouts

    DXF is universally compatible with all CAD systems including
    AutoCAD, BricsCAD, QCAD, LibreCAD, FreeCAD, and sign shop software.

    Examples:
        >>> service = CADExportService()
        >>> result = service.export_foundation_plan(
        ...     rebar_schedule=schedule,
        ...     diameter_ft=3.0,
        ...     depth_ft=6.0,
        ...     options=CADExportOptions(format=CADFormat.DXF)
        ... )
        >>> print(f"Exported to {result.filename}")
        Exported to foundation_plan.dxf
    """

    def __init__(self, dxf_version: str = "R2018"):
        """
        Initialize CAD export service.

        Args:
            dxf_version: DXF version (R2018 is widely compatible)
        """
        self.dxf_version = dxf_version
        logger.info("cad_export.initialized", dxf_version=dxf_version)

    def export_foundation_plan(
        self,
        rebar_schedule: RebarScheduleResult,
        diameter_ft: float,
        depth_ft: float,
        anchor_layout: AnchorBoltLayout | None = None,
        options: CADExportOptions = CADExportOptions(),
    ) -> tuple[bytes, CADExportResult]:
        """
        Export foundation plan with rebar and anchor bolt details.

        Generates:
        - Plan view (top)
        - Section view (side cut)
        - Rebar schedule table
        - Anchor bolt detail
        - Dimensions and notes

        Args:
            rebar_schedule: Complete rebar schedule from concrete service
            diameter_ft: Foundation diameter (feet)
            depth_ft: Foundation depth (feet)
            anchor_layout: Optional anchor bolt pattern
            options: Export options (format, scale, etc.)

        Returns:
            Tuple of (file_bytes, export_result)

        Raises:
            ValidationError: If inputs are invalid
        """
        # Validate inputs
        if diameter_ft <= 0 or depth_ft <= 0:
            raise ValidationError(
                message="Foundation dimensions must be positive",
                diameter_ft=diameter_ft,
                depth_ft=depth_ft,
            )

        # Create new DXF drawing
        doc = ezdxf.new(self.dxf_version)
        msp = doc.modelspace()

        # Setup layers (AIA CAD standard)
        self._setup_layers(doc)

        # Drawing origin and scale
        origin_x, origin_y = 10.0, 10.0  # Inches from sheet corner
        scale_factor = self._get_scale_factor(options.scale)

        # Convert foundation dimensions to drawing units (inches)
        diameter_in = diameter_ft * 12.0
        depth_in = depth_ft * 12.0
        radius_in = diameter_in / 2.0

        # Track drawing bounds
        min_x, max_x = origin_x, origin_x + diameter_in * scale_factor
        min_y, max_y = origin_y, origin_y + depth_in * scale_factor

        # 1. Draw foundation plan view (top)
        plan_center_x = origin_x + radius_in * scale_factor
        plan_center_y = origin_y + diameter_in * scale_factor + 2.0  # Offset above section

        # Concrete outline (circle)
        msp.add_circle(
            center=(plan_center_x, plan_center_y),
            radius=radius_in * scale_factor,
            dxfattribs={"layer": LAYER_CONCRETE, "color": COLOR_GRAY}
        )

        # Centerlines
        msp.add_line(
            start=(plan_center_x - radius_in * scale_factor * 1.2, plan_center_y),
            end=(plan_center_x + radius_in * scale_factor * 1.2, plan_center_y),
            dxfattribs={"layer": LAYER_CENTERLINES, "linetype": "CENTER"}
        )
        msp.add_line(
            start=(plan_center_x, plan_center_y - radius_in * scale_factor * 1.2),
            end=(plan_center_x, plan_center_y + radius_in * scale_factor * 1.2),
            dxfattribs={"layer": LAYER_CENTERLINES, "linetype": "CENTER"}
        )

        # Rebar placement (vertical bars shown as dots)
        if rebar_schedule.vertical_bars:
            vertical_bar = rebar_schedule.vertical_bars[0]
            num_bars = vertical_bar.quantity

            for i in range(num_bars):
                angle = (2 * math.pi * i) / num_bars
                bar_x = plan_center_x + (radius_in * 0.75 * scale_factor) * math.cos(angle)
                bar_y = plan_center_y + (radius_in * 0.75 * scale_factor) * math.sin(angle)

                # Draw rebar symbol (filled circle)
                msp.add_circle(
                    center=(bar_x, bar_y),
                    radius=0.0625,  # 1/16" symbol
                    dxfattribs={"layer": LAYER_REBAR, "color": COLOR_RED}
                )

        # Anchor bolts (if provided)
        if anchor_layout:
            bolt_circle_radius = anchor_layout.bolt_circle_diameter_in / 2.0 * scale_factor

            for i in range(anchor_layout.num_bolts):
                angle = (2 * math.pi * i) / anchor_layout.num_bolts
                bolt_x = plan_center_x + bolt_circle_radius * math.cos(angle)
                bolt_y = plan_center_y + bolt_circle_radius * math.sin(angle)

                # Draw anchor bolt (X symbol)
                size = 0.125
                msp.add_line(
                    start=(bolt_x - size, bolt_y - size),
                    end=(bolt_x + size, bolt_y + size),
                    dxfattribs={"layer": LAYER_STEEL, "color": COLOR_BLUE}
                )
                msp.add_line(
                    start=(bolt_x - size, bolt_y + size),
                    end=(bolt_x + size, bolt_y - size),
                    dxfattribs={"layer": LAYER_STEEL, "color": COLOR_BLUE}
                )

        # 2. Draw section view (side cut)
        section_x = origin_x
        section_y = origin_y

        # Foundation outline (rectangle)
        msp.add_lwpolyline(
            points=[
                (section_x, section_y),
                (section_x + diameter_in * scale_factor, section_y),
                (section_x + diameter_in * scale_factor, section_y + depth_in * scale_factor),
                (section_x, section_y + depth_in * scale_factor),
                (section_x, section_y),  # Close
            ],
            dxfattribs={"layer": LAYER_CONCRETE, "color": COLOR_GRAY}
        )

        # Hatch pattern for concrete
        hatch = msp.add_hatch(color=COLOR_GRAY)
        hatch.set_pattern_fill("ANSI31", scale=0.5)  # Concrete hatch
        hatch.paths.add_polyline_path(
            [
                (section_x, section_y),
                (section_x + diameter_in * scale_factor, section_y),
                (section_x + diameter_in * scale_factor, section_y + depth_in * scale_factor),
                (section_x, section_y + depth_in * scale_factor),
            ],
            is_closed=True
        )

        # Vertical rebar (shown as lines)
        if rebar_schedule.vertical_bars:
            vertical_bar = rebar_schedule.vertical_bars[0]
            bar_length_in = vertical_bar.length_ft * 12.0

            # Show 2 bars on section (one each side)
            for offset_factor in [0.2, 0.8]:
                bar_x = section_x + diameter_in * scale_factor * offset_factor
                bar_y_start = section_y + (depth_in - bar_length_in) * scale_factor / 2.0
                bar_y_end = bar_y_start + bar_length_in * scale_factor

                msp.add_line(
                    start=(bar_x, bar_y_start),
                    end=(bar_x, bar_y_end),
                    dxfattribs={"layer": LAYER_REBAR, "color": COLOR_RED, "lineweight": 35}
                )

        # Anchor bolts (if provided)
        if anchor_layout:
            # Show bolts projecting above foundation
            bolt_x_left = section_x + diameter_in * scale_factor * 0.3
            bolt_x_right = section_x + diameter_in * scale_factor * 0.7

            for bolt_x in [bolt_x_left, bolt_x_right]:
                # Embedded portion
                embed_y = section_y + depth_in * scale_factor
                msp.add_line(
                    start=(bolt_x, embed_y),
                    end=(bolt_x, embed_y - anchor_layout.embedment_in * scale_factor),
                    dxfattribs={"layer": LAYER_STEEL, "color": COLOR_BLUE, "lineweight": 50}
                )

                # Projection above
                msp.add_line(
                    start=(bolt_x, embed_y),
                    end=(bolt_x, embed_y + anchor_layout.projection_in * scale_factor),
                    dxfattribs={"layer": LAYER_STEEL, "color": COLOR_BLUE, "lineweight": 50}
                )

        # 3. Add dimensions (if enabled)
        if options.include_dimensions:
            self._add_dimensions(
                msp, section_x, section_y,
                diameter_in, depth_in,
                scale_factor, options
            )

        # 4. Add rebar schedule table (if enabled)
        entities_count = len(list(msp))

        if options.include_rebar_schedule:
            table_x = origin_x + diameter_in * scale_factor + 2.0
            table_y = origin_y + depth_in * scale_factor

            self._add_rebar_schedule_table(
                msp, table_x, table_y,
                rebar_schedule, options
            )

        # 5. Add title block (if enabled)
        if options.include_title_block:
            self._add_title_block(
                msp, diameter_ft, depth_ft,
                rebar_schedule.concrete, options
            )

        # 6. Add general notes
        if options.include_notes:
            notes_x = origin_x
            notes_y = section_y - 2.0

            self._add_general_notes(msp, notes_x, notes_y, anchor_layout)

        # Update bounds
        max_y = max(max_y, plan_center_y + radius_in * scale_factor + 1.0)

        # Export to bytes based on format
        file_bytes, filename = self._export_to_format(doc, options.format, options)

        # Count entities and layers
        entities_count = len(list(msp))
        layers_created = [layer.dxf.name for layer in doc.layers]

        logger.info(
            "cad_export.foundation_plan_created",
            format=options.format.value,
            entities=entities_count,
            layers=len(layers_created),
        )

        result = CADExportResult(
            format=options.format,
            filename=filename,
            file_size_bytes=len(file_bytes),
            layers_created=layers_created,
            entities_count=entities_count,
            drawing_bounds={
                "min_x": min_x,
                "max_x": max_x,
                "min_y": min_y,
                "max_y": max_y,
            }
        )

        return file_bytes, result

    def _setup_layers(self, doc: ezdxf.document.Drawing):
        """Create standard AIA CAD layers."""
        layers = [
            (LAYER_DIMENSIONS, COLOR_CYAN),
            (LAYER_TEXT, COLOR_WHITE),
            (LAYER_REBAR, COLOR_RED),
            (LAYER_CONCRETE, COLOR_GRAY),
            (LAYER_STEEL, COLOR_BLUE),
            (LAYER_CENTERLINES, COLOR_GREEN),
            (LAYER_GRID, COLOR_MAGENTA),
            (LAYER_TITLE_BLOCK, COLOR_WHITE),
        ]

        for layer_name, color in layers:
            doc.layers.add(layer_name, color=color)

    def _get_scale_factor(self, scale: DrawingScale) -> float:
        """Convert drawing scale to numeric factor."""
        scale_map = {
            DrawingScale.SCALE_1_1: 1.0,
            DrawingScale.SCALE_1_2: 0.5,
            DrawingScale.SCALE_1_4: 0.25,
            DrawingScale.SCALE_3_8: 0.03125,   # 3/8" / 12"
            DrawingScale.SCALE_1_2_ARCH: 0.04167,  # 1/2" / 12"
            DrawingScale.SCALE_1_4_ARCH: 0.02083,  # 1/4" / 12"
            DrawingScale.SCALE_1_8_ARCH: 0.01042,  # 1/8" / 12"
        }
        return scale_map.get(scale, 0.02083)

    def _add_dimensions(
        self, msp, x, y, width_in, height_in, scale_factor, options
    ):
        """Add dimension annotations."""
        # Horizontal dimension (diameter)
        dim_y = y - 0.5
        msp.add_linear_dim(
            base=(x + width_in * scale_factor / 2, dim_y),
            p1=(x, y),
            p2=(x + width_in * scale_factor, y),
            dimstyle="EZDXF",
            dxfattribs={"layer": LAYER_DIMENSIONS}
        ).render()

        # Vertical dimension (depth)
        dim_x = x + width_in * scale_factor + 0.5
        msp.add_linear_dim(
            base=(dim_x, y + height_in * scale_factor / 2),
            p1=(x + width_in * scale_factor, y),
            p2=(x + width_in * scale_factor, y + height_in * scale_factor),
            angle=90,
            dimstyle="EZDXF",
            dxfattribs={"layer": LAYER_DIMENSIONS}
        ).render()

    def _add_rebar_schedule_table(
        self, msp, x, y, rebar_schedule: RebarScheduleResult, options
    ):
        """Add rebar schedule table."""
        # Table header
        row_height = 0.25
        col_widths = [0.75, 1.0, 0.75, 1.25, 2.0]  # Mark, Size, Qty, Length, Location

        # Title
        msp.add_text(
            "REBAR SCHEDULE",
            dxfattribs={
                "layer": LAYER_TEXT,
                "height": TEXT_HEIGHT_SUBTITLE,
                "style": "Standard",
            }
        ).set_placement((x, y), align=TextEntityAlignment.LEFT)

        y -= row_height * 1.5

        # Headers
        headers = ["MARK", "SIZE", "QTY", "LENGTH", "LOCATION"]
        x_offset = x
        for i, header in enumerate(headers):
            msp.add_text(
                header,
                dxfattribs={
                    "layer": LAYER_TEXT,
                    "height": TEXT_HEIGHT_SMALL,
                    "style": "Standard",
                }
            ).set_placement((x_offset, y), align=TextEntityAlignment.LEFT)

            # Draw box
            msp.add_lwpolyline(
                points=[
                    (x_offset, y - row_height),
                    (x_offset + col_widths[i], y - row_height),
                    (x_offset + col_widths[i], y),
                    (x_offset, y),
                    (x_offset, y - row_height),
                ],
                dxfattribs={"layer": LAYER_TEXT}
            )

            x_offset += col_widths[i]

        y -= row_height

        # Data rows
        all_bars = rebar_schedule.vertical_bars + rebar_schedule.horizontal_bars

        for bar in all_bars:
            x_offset = x
            values = [
                bar.mark,
                bar.size.value,
                str(bar.quantity),
                f"{bar.length_ft:.1f}'",
                bar.location[:20],  # Truncate long locations
            ]

            for i, value in enumerate(values):
                msp.add_text(
                    value,
                    dxfattribs={
                        "layer": LAYER_TEXT,
                        "height": TEXT_HEIGHT_SMALL,
                        "style": "Standard",
                    }
                ).set_placement((x_offset + 0.05, y - row_height * 0.75), align=TextEntityAlignment.LEFT)

                # Draw box
                msp.add_lwpolyline(
                    points=[
                        (x_offset, y - row_height),
                        (x_offset + col_widths[i], y - row_height),
                        (x_offset + col_widths[i], y),
                        (x_offset, y),
                        (x_offset, y - row_height),
                    ],
                    dxfattribs={"layer": LAYER_TEXT}
                )

                x_offset += col_widths[i]

            y -= row_height

    def _add_title_block(
        self, msp, diameter_ft, depth_ft, concrete: ConcreteVolume, options
    ):
        """Add title block with project information."""
        # Title block position (lower right corner of sheet)
        tb_x = 20.0
        tb_y = 1.0
        tb_width = 6.0
        tb_height = 2.5

        # Border
        msp.add_lwpolyline(
            points=[
                (tb_x, tb_y),
                (tb_x + tb_width, tb_y),
                (tb_x + tb_width, tb_y + tb_height),
                (tb_x, tb_y + tb_height),
                (tb_x, tb_y),
            ],
            dxfattribs={"layer": LAYER_TITLE_BLOCK, "lineweight": 50}
        )

        # Project info
        y_offset = tb_y + tb_height - 0.3

        if options.company_name:
            msp.add_text(
                options.company_name,
                dxfattribs={"layer": LAYER_TITLE_BLOCK, "height": TEXT_HEIGHT_SUBTITLE}
            ).set_placement((tb_x + 0.2, y_offset), align=TextEntityAlignment.LEFT)
            y_offset -= 0.3

        if options.project_name:
            msp.add_text(
                options.project_name,
                dxfattribs={"layer": LAYER_TITLE_BLOCK, "height": TEXT_HEIGHT_NORMAL}
            ).set_placement((tb_x + 0.2, y_offset), align=TextEntityAlignment.LEFT)
            y_offset -= 0.25

        # Drawing title
        msp.add_text(
            "FOUNDATION PLAN",
            dxfattribs={"layer": LAYER_TITLE_BLOCK, "height": TEXT_HEIGHT_NORMAL}
        ).set_placement((tb_x + 0.2, y_offset), align=TextEntityAlignment.LEFT)
        y_offset -= 0.25

        # Foundation specs
        msp.add_text(
            f"DIA: {diameter_ft:.1f}' DEPTH: {depth_ft:.1f}'",
            dxfattribs={"layer": LAYER_TITLE_BLOCK, "height": TEXT_HEIGHT_SMALL}
        ).set_placement((tb_x + 0.2, y_offset), align=TextEntityAlignment.LEFT)
        y_offset -= 0.2

        # Concrete quantity
        msp.add_text(
            f"CONCRETE: {concrete.order_volume_cy:.2f} CY",
            dxfattribs={"layer": LAYER_TITLE_BLOCK, "height": TEXT_HEIGHT_SMALL}
        ).set_placement((tb_x + 0.2, y_offset), align=TextEntityAlignment.LEFT)
        y_offset -= 0.2

        # Drawing number
        if options.drawing_number:
            msp.add_text(
                f"DWG NO: {options.drawing_number}",
                dxfattribs={"layer": LAYER_TITLE_BLOCK, "height": TEXT_HEIGHT_SMALL}
            ).set_placement((tb_x + 0.2, y_offset), align=TextEntityAlignment.LEFT)

        # Scale
        msp.add_text(
            f"SCALE: {options.scale.value}",
            dxfattribs={"layer": LAYER_TITLE_BLOCK, "height": TEXT_HEIGHT_SMALL}
        ).set_placement((tb_x + 0.2, tb_y + 0.2), align=TextEntityAlignment.LEFT)

    def _add_general_notes(self, msp, x, y, anchor_layout):
        """Add general notes and specifications."""
        notes = [
            "GENERAL NOTES:",
            "1. ALL CONCRETE TO BE 3000 PSI MIN AT 28 DAYS",
            "2. REBAR TO BE GRADE 60 (FY=60 KSI) ASTM A615",
            "3. CONCRETE COVER: 3\" MIN (CAST AGAINST EARTH)",
            "4. VERIFY SOIL BEARING CAPACITY WITH GEOTECHNICAL REPORT",
        ]

        if anchor_layout:
            notes.append(f"5. ANCHOR BOLTS: {anchor_layout.bolt_size} ASTM F1554 GRADE 36")
            notes.append(f"6. BOLT PROJECTION: {anchor_layout.projection_in:.1f}\" ABOVE TOP OF CONCRETE")

        for i, note in enumerate(notes):
            msp.add_text(
                note,
                dxfattribs={
                    "layer": LAYER_TEXT,
                    "height": TEXT_HEIGHT_SMALL,
                }
            ).set_placement((x, y - i * 0.2), align=TextEntityAlignment.LEFT)

    def _export_to_format(
        self, doc: ezdxf.document.Drawing, format: CADFormat, options: CADExportOptions
    ) -> tuple[bytes, str]:
        """
        Export DXF document to bytes.

        Args:
            doc: ezdxf Drawing document
            format: CADFormat (must be DXF)
            options: Export options

        Returns:
            tuple: (file_bytes, filename)
        """
        # DXF export (only supported format)
        buffer = io.BytesIO()
        doc.write(buffer)

        # Generate filename from options
        drawing_num = options.drawing_number or "FND-001"
        filename = f"{drawing_num.replace('/', '_')}_foundation_plan.dxf"

        return buffer.getvalue(), filename
