"""
DEC-002: Drawing Model Abstraction
===================================

Design Philosophy
-----------------
Describe geometry as data. Let renderers decide how to draw it.

A DrawingSheet is a pure-data description of what a drawing contains:
lines, circles, arcs, rectangles, text, dimensions, leaders, and hatches
grouped into named ViewPorts. Nothing in this module touches a file, a
canvas, or a DXF entity. That work belongs to the renderer layer.

Benefits of this separation:

    1. Single source of truth.  Foundation drawings, shop drawings, and
       detail sheets all share the same model.  The caisson-capacity
       calculator builds a DrawingSheet; the ezdxf renderer writes DXF;
       a future SVG renderer previews it in the browser — same model,
       different outputs.

    2. Testability.  Because everything is a plain dataclass, you can
       assert on drawing content without touching any file I/O.  Verify
       that a 48-inch caisson produces a circle of radius 24.0 in the
       FRONT ELEVATION viewport without running ezdxf at all.

    3. Caching.  Dataclasses are serializable.  A DrawingSheet can be
       converted to a dict / JSON and stored in Redis or on disk.  If
       the inputs haven't changed, skip re-computation entirely and hand
       the cached model to the renderer.

    4. Template-driven vs computed geometry.  A template can pre-populate
       note blocks, title blocks, and standard details.  The calculator
       fills in the geometry.  Both paths produce the same DrawingSheet
       type.

ASME Compliance (2026)
---------------------
- Hatch patterns: ANSI31 (concrete), ANSI32 (steel) per ASME Y14.3
- Line weights: 0.25mm min for annotations per ASME Y14.2-2023
- Text heights: 0.09" min for notes, 0.10" for dimensions per ASME Y14.100
- Dimension terminators: tick marks per ASME Y14.2 (structural convention)
- Leaders: 30-60 degree angle recommended per ASME Y14.2 Section 4

Coordinate system
-----------------
All coordinates are in drawing units.  For the sign industry the default
unit is **inches**.  A 36" × 24" ANSI-D sheet is therefore (36.0, 24.0).
The renderer is responsible for any unit conversion before writing to
the target format.

Layer conventions
-----------------
Layer names follow Eagle Sign Co DXF conventions.  The canonical set is
defined in DrawingSheet.layers.  Every spec dataclass carries a `layer`
field so individual entities can be placed on non-default layers when
needed (e.g. REBAR lines inside a CONCRETE viewport).

Usage
-----
    from apex_signcalc.drawing_model import new_sheet, ViewPort, CircleSpec

    sheet = new_sheet(project="MAIN ST PYLON", title="CAISSON PLAN", dwg_no="C-001")
    vp = ViewPort(name="PLAN VIEW", origin=(2.0, 4.0), scale=0.5)
    vp.circles.append(CircleSpec(center=(0.0, 0.0), radius=24.0, layer="CONCRETE"))
    sheet.viewports.append(vp)
    # Hand `sheet` to the ezdxf renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Primitive type alias
# ---------------------------------------------------------------------------

#: A 2-D point in drawing-unit space (x, y).
Point = Tuple[float, float]


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class LineType(Enum):
    """Standard DXF line-type names understood by the renderer."""

    CONTINUOUS = "CONTINUOUS"
    DASHED = "DASHED"
    CENTER = "CENTER"
    HIDDEN = "HIDDEN"
    PHANTOM = "PHANTOM"


class DimSide(Enum):
    """Which side of the measured geometry the dimension line sits on."""

    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


class HatchPattern(Enum):
    """DXF/AutoCAD hatch pattern identifiers per ASME Y14.3 Section 5."""

    CONCRETE = "ANSI31"    # 45° diagonal — concrete/masonry (ASME Y14.3)
    STEEL = "ANSI32"       # Double diagonal — steel sections (ASME Y14.3)
    EARTH = "EARTH"        # Soil/earth fill pattern
    GRAVEL = "GRAVEL"      # Gravel/aggregate fill
    NONE = "NONE"          # No fill (sentinel)


# ---------------------------------------------------------------------------
# Geometry specs
# ---------------------------------------------------------------------------


@dataclass
class LineSpec:
    """A line segment on the drawing."""

    start: Point
    end: Point
    layer: str = "0"
    linetype: LineType = LineType.CONTINUOUS
    color: int = 7          # DXF ACI color index (7 = white/black)
    lineweight: int = -1    # -1 = inherit from layer


@dataclass
class CircleSpec:
    """A circle on the drawing."""

    center: Point
    radius: float
    layer: str = "0"
    color: int = 7
    filled: bool = False    # hint to renderer (e.g. solid fill vs outline)


@dataclass
class ArcSpec:
    """An arc on the drawing."""

    center: Point
    radius: float
    start_angle: float      # degrees, measured CCW from positive X
    end_angle: float        # degrees, measured CCW from positive X
    layer: str = "0"
    color: int = 7


@dataclass
class RectSpec:
    """A rectangle — rendered as four lines or a closed LWPolyline."""

    origin: Point           # bottom-left corner in drawing units
    width: float
    height: float
    layer: str = "0"
    color: int = 7
    hatch: HatchPattern = HatchPattern.NONE
    hatch_scale: float = 1.0


# ---------------------------------------------------------------------------
# Annotation specs
# ---------------------------------------------------------------------------


@dataclass
class TextSpec:
    """A single text annotation."""

    insert: Point           # insertion point
    text: str
    height: float = 0.1    # text height in drawing units
    rotation: float = 0.0  # degrees CCW from positive X
    layer: str = "NOTES"
    color: int = 7
    halign: str = "LEFT"        # LEFT | CENTER | RIGHT
    valign: str = "BASELINE"    # BASELINE | BOTTOM | MIDDLE | TOP


@dataclass
class DimensionSpec:
    """A linear dimension with extension lines and a dimension line."""

    p1: Point               # first extension-line origin (on geometry)
    p2: Point               # second extension-line origin (on geometry)
    side: DimSide = DimSide.TOP
    offset: float = 0.5    # perpendicular distance from geometry to dim line
    layer: str = "DIMENSIONS"
    text_override: Optional[str] = None     # None = auto-measure distance
    dimpost: Optional[str] = None          # suffix/prefix, e.g. '<>" REVEAL'
    dimdec: int = 0                        # decimal places
    dimlfac: float = 1.0                   # linear scale factor (unit conversion)
    dimstyle: str = "SIGNX"                # named dimstyle (tick marks, text above)


@dataclass
class LeaderSpec:
    """A leader line: arrowhead touching geometry → shelf line → stacked text."""

    arrow_point: Point      # where the arrow touches the geometry
    landing_point: Point    # start of horizontal shelf line
    text_lines: List[str] = field(default_factory=list)
    layer: str = "NOTES"
    color: int = 7
    text_height: float = 0.09    # ASME Y14.100 min for annotation text
    has_arrow: bool = True


@dataclass
class HatchSpec:
    """A hatched closed region."""

    boundary_points: List[Point]            # closed polygon vertices (last != first)
    pattern: HatchPattern = HatchPattern.CONCRETE
    scale: float = 1.0
    angle: float = 0.0
    layer: str = "HATCH"
    color: int = 8          # DXF ACI 8 = dark gray


# ---------------------------------------------------------------------------
# Sheet-level containers
# ---------------------------------------------------------------------------


@dataclass
class ViewPort:
    """A named view or detail on the drawing sheet.

    Coordinates stored in each child spec are in *model space* relative to
    the ViewPort's own origin.  The renderer translates them to sheet space
    by applying `origin` and `scale`.

    Examples of typical viewport names:
        "FRONT ELEVATION", "SECTION A-A", "PLAN VIEW", "MOUNTING DETAIL"
    """

    name: str
    origin: Point           # bottom-left of this viewport in sheet space (inches)
    scale: float = 1.0     # drawing scale applied when placing on sheet

    lines: List[LineSpec] = field(default_factory=list)
    circles: List[CircleSpec] = field(default_factory=list)
    arcs: List[ArcSpec] = field(default_factory=list)
    rects: List[RectSpec] = field(default_factory=list)
    texts: List[TextSpec] = field(default_factory=list)
    dimensions: List[DimensionSpec] = field(default_factory=list)
    leaders: List[LeaderSpec] = field(default_factory=list)
    hatches: List[HatchSpec] = field(default_factory=list)

    # View label rendered as underlined text at the bottom of the viewport.
    label: Optional[str] = None
    label_scale: Optional[str] = None  # e.g. 'SCALE: 1" = 1\'-0"'


@dataclass
class NoteBlock:
    """A block of sequentially numbered notes."""

    origin: Point
    title: str = "NOTES"
    notes: List[str] = field(default_factory=list)
    text_height: float = 0.09    # ASME Y14.100 min for ANSI D sheets
    line_spacing: float = 0.18  # 2x text_height for readability
    layer: str = "NOTES"


@dataclass
class TitleBlock:
    """Drawing title block — typically a strip across the bottom of the sheet."""

    company: str = "EAGLE SIGN CO."
    project: str = ""
    drawing_title: str = ""
    drawing_number: str = ""
    revision: str = "0"
    date: str = ""
    drawn_by: str = "SIGNX"
    checked_by: str = ""
    scale: str = "AS NOTED"
    sheet: str = "1 OF 1"

    # Position in sheet space
    origin: Point = (0.0, 0.0)
    width: float = 36.0
    height: float = 1.5


@dataclass
class DrawingSheet:
    """Complete drawing sheet — the top-level container consumed by renderers.

    A DrawingSheet is the authoritative description of one page of output.
    It carries:

    - ``viewports``    — one or more named views (elevations, plans, details)
    - ``note_blocks``  — numbered note lists placed anywhere on the sheet
    - ``title_block``  — company / project metadata strip
    - ``layers``       — layer definitions the renderer must create
    - ``dimstyle_config`` — SIGNX dimstyle parameters (tick marks, text above)

    Sheet sizes follow ANSI conventions (units = inches):
        A = 8.5 × 11,  B = 11 × 17,  C = 17 × 22,  D = 22 × 34,
        E = 34 × 44

    The default is ANSI D at 36 × 24 (landscape).  Eagle Sign Co
    historically uses 36 × 24 for permit / fabrication packages.
    """

    # Sheet geometry
    size: str = "D"             # ANSI sheet size label
    width: float = 36.0        # sheet width in inches
    height: float = 24.0       # sheet height in inches
    units: str = "inches"

    # Content
    viewports: List[ViewPort] = field(default_factory=list)
    note_blocks: List[NoteBlock] = field(default_factory=list)
    title_block: Optional[TitleBlock] = None

    # Drawing-level metadata
    dimstyle_name: str = "SIGNX"
    dimstyle_config: Dict[str, object] = field(default_factory=lambda: {
        "dimtih": 1,       # force horizontal text on all dimensions
        "dimtad": 1,       # text above dimension line
        "dimtsz": 0.05,    # tick mark size (oblique strokes, not arrows)
        "dimtxt": 0.1,     # text height
        "dimexe": 0.05,    # extension beyond dim line
        "dimexo": 0.02,    # extension-line offset from origin point
        "dimasz": 0.0,     # arrow size = 0 (tick marks are used instead)
        "dimdec": 0,       # default decimal places
        "dimlfac": 1.0,    # default linear scale factor
    })

    # Layer table: name -> (ACI color, linetype name, lineweight in hundredths of mm)
    layers: Dict[str, Tuple[int, str, int]] = field(default_factory=lambda: {
        "CONCRETE":   (8,  "CONTINUOUS", 25),   # gray, standard weight
        "STEEL":      (1,  "CONTINUOUS", 35),   # red, heavy
        "REBAR":      (3,  "CONTINUOUS", 25),   # green
        "DIMENSIONS": (2,  "CONTINUOUS", 25),   # yellow, 0.25mm per ASME Y14.2
        "NOTES":      (7,  "CONTINUOUS", 25),   # white/black, 0.25mm per ASME Y14.2
        "HATCH":      (8,  "CONTINUOUS", -1),   # gray, default
        "CENTERLINE": (1,  "CENTER",     25),   # red, 0.25mm per ASME Y14.2
        "HIDDEN":     (8,  "DASHED",     25),   # gray, 0.25mm per ASME Y14.2
        "BORDER":     (7,  "CONTINUOUS", 50),   # white/black, heavy
        "TITLEBLOCK": (7,  "CONTINUOUS", 25),   # white/black
    })


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------


def new_sheet(
    project: str = "",
    title: str = "",
    dwg_no: str = "",
    size: str = "D",
) -> DrawingSheet:
    """Create a new DrawingSheet pre-populated with Eagle Sign Co defaults.

    Parameters
    ----------
    project:
        Project name or address (printed in title block).
    title:
        Drawing title, e.g. ``"CAISSON FOUNDATION PLAN"``.
    dwg_no:
        Drawing number, e.g. ``"C-001"``.
    size:
        ANSI sheet size (``"A"`` through ``"E"``).  Defaults to ``"D"``
        (36 × 24 inches, landscape).

    Returns
    -------
    DrawingSheet
        A blank sheet with title block filled in and SIGNX dimstyle config
        applied.  Add ViewPorts and NoteBlocks to build out the drawing.

    Example
    -------
    ::

        sheet = new_sheet(
            project="123 MAIN ST",
            title="CAISSON PLAN",
            dwg_no="C-001",
        )
        vp = ViewPort(name="PLAN VIEW", origin=(2.0, 4.0))
        sheet.viewports.append(vp)
        # Pass `sheet` to the ezdxf renderer.
    """
    sheet = DrawingSheet(size=size)
    sheet.title_block = TitleBlock(
        project=project,
        drawing_title=title,
        drawing_number=dwg_no,
    )
    return sheet
