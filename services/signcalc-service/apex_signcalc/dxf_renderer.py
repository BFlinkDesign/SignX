"""
dxf_renderer.py -- DEC-002 ezdxf Renderer
==========================================

Consumes a DrawingSheet (drawing_model.py) and produces a DXF file
(R2010 format) suitable for AutoCAD, BricsCAD, and sign-shop plotters.

An optional PNG preview can be rendered via ezdxf's drawing add-on when
matplotlib is available.

Render pipeline
---------------
1. Create ezdxf document (R2010).
2. Install SIGNX dimstyle from sheet.dimstyle_config.
3. Create all layers from sheet.layers.
4. For each ViewPort (in order):
     a. Compute sheet_pt = viewport.origin + model_pt * viewport.scale
     b. Render: hatches -> rects -> lines -> circles -> arcs ->
                dimensions -> leaders -> texts
     c. Draw viewport border (optional) and underlined label.
5. Render NoteBlocks.
6. Render TitleBlock (double-line border, company/project/dwg metadata).
7. Save and return filepath.

Coordinate conventions
-----------------------
All drawing_model coordinates are model-space inches.
Sheet coordinates are inches from the sheet lower-left corner.
Transform: sheet_xy = viewport.origin + model_xy * viewport.scale

Dependencies
------------
Required:  ezdxf >= 1.3
Optional:  matplotlib (for render_preview)
"""

from __future__ import annotations

import logging
import math
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ezdxf guard
# ---------------------------------------------------------------------------

try:
    import ezdxf
    from ezdxf.document import Drawing as _EzdxfDoc
    from ezdxf.layouts import Modelspace as _Msp
except ImportError as _exc:
    raise ImportError(
        "ezdxf is required for DXF rendering. "
        "Install it with: pip install ezdxf"
    ) from _exc

try:
    from .drawing_model import (
        ArcSpec,
        CircleSpec,
        DimSide,
        DimensionSpec,
        DrawingSheet,
        HatchPattern,
        HatchSpec,
        LeaderSpec,
        LineSpec,
        LineType,
        NoteBlock,
        Point,
        RectSpec,
        TextSpec,
        TitleBlock,
        ViewPort,
    )
except ImportError:
    from drawing_model import (
        ArcSpec,
        CircleSpec,
        DimSide,
        DimensionSpec,
        DrawingSheet,
        HatchPattern,
        HatchSpec,
        LeaderSpec,
        LineSpec,
        LineType,
        NoteBlock,
        Point,
        RectSpec,
        TextSpec,
        TitleBlock,
        ViewPort,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_to_dxf(sheet: DrawingSheet, filepath: str) -> str:
    """Render a DrawingSheet to a DXF file on disk.

    Consumes: DrawingSheet (drawing_model.py)

    Parameters
    ----------
    sheet:
        Complete drawing description produced by a calculator or template.
    filepath:
        Path for the output .dxf file.  The parent directory must exist.

    Returns
    -------
    str
        The same filepath (convenient for chaining into blob storage).

    Raises
    ------
    ImportError
        If ezdxf is not installed.
    OSError
        If the file cannot be written.
    """
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    _setup_dimstyle(doc, sheet.dimstyle_config, sheet.dimstyle_name)
    _setup_layers(doc, sheet.layers)
    _ensure_linetypes(doc)

    for vp in sheet.viewports:
        if _vp_empty(vp):
            logger.debug("Skipping empty viewport %r", vp.name)
            continue
        _render_viewport(doc, msp, vp, sheet.dimstyle_name)

    for nb in sheet.note_blocks:
        _render_note_block(msp, nb)

    if sheet.title_block is not None:
        _render_title_block(msp, sheet.title_block)

    doc.saveas(filepath)
    logger.info("DXF saved: %s", filepath)
    return filepath


def render_preview(
    sheet: DrawingSheet,
    filepath: str,
    dpi: int = 150,
) -> Optional[str]:
    """Render a DrawingSheet to a PNG preview using ezdxf's drawing backend.

    Consumes: DrawingSheet (drawing_model.py)

    Degrades gracefully: returns None (does not raise) when matplotlib or
    Pillow are missing.  Callers should handle None and fall back to DXF-only.

    Parameters
    ----------
    sheet:
        The drawing to preview.
    filepath:
        Output path for the .png file.
    dpi:
        Resolution of the PNG in dots per inch (default 150).

    Returns
    -------
    str or None
        filepath on success, None if preview dependencies are missing.
    """
    try:
        import matplotlib  # noqa: F401 -- existence check
        from ezdxf.addons.drawing import Frontend, RenderContext
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning(
            "Preview unavailable -- install matplotlib and Pillow: "
            "pip install matplotlib Pillow"
        )
        return None

    tmp_dxf = filepath.replace(".png", "_tmp_preview.dxf")
    render_to_dxf(sheet, tmp_dxf)

    try:
        doc = ezdxf.readfile(tmp_dxf)
        msp_r = doc.modelspace()
        fig = plt.figure(
            figsize=(sheet.width / 4.0, sheet.height / 4.0), dpi=dpi
        )
        ax = fig.add_axes([0, 0, 1, 1])
        ctx = RenderContext(doc)
        backend = MatplotlibBackend(ax)
        Frontend(ctx, backend).draw_layout(msp_r)
        fig.savefig(filepath, dpi=dpi, bbox_inches="tight", pad_inches=0)
        plt.close(fig)
        logger.info("PNG preview saved: %s", filepath)
        return filepath
    except Exception:
        logger.exception("PNG preview failed")
        return None
    finally:
        try:
            os.remove(tmp_dxf)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------


def _setup_dimstyle(
    doc: _EzdxfDoc,
    config: Dict,
    name: str = "SIGNX",
) -> None:
    """Create or update the SIGNX dimstyle from DrawingSheet.dimstyle_config.

    Consumes: DrawingSheet.dimstyle_config (dict of DXF dimstyle attr names)

    Key DXF dimstyle attribute meanings:
      dimtih  = 1    -- horizontal text inside dimension (not rotated with angle)
      dimtad  = 1    -- text placed above the dimension line
      dimtsz  = 0.05 -- tick mark (oblique stroke) size; non-zero disables arrows
      dimasz  = 0.0  -- arrowhead size; 0 = none when tick marks are used
      dimtxt  = 0.1  -- text height in drawing units
      dimexe  = 0.05 -- extension line length beyond dimension line
      dimexo  = 0.02 -- extension line offset gap from geometry origin point
      dimdec  = 0    -- decimal places for the measured value display
      dimlfac = 1.0  -- linear scale factor multiplied into measured value
    """
    if name in doc.dimstyles:
        ds = doc.dimstyles.get(name)
    else:
        ds = doc.dimstyles.new(name)

    for attr, value in config.items():
        try:
            setattr(ds.dxf, attr, value)
        except Exception:
            logger.debug("dimstyle attr %r not settable: %r", attr, value)


def _setup_layers(doc: _EzdxfDoc, layers: Dict) -> None:
    """Create DXF layers from DrawingSheet.layers.

    Consumes: DrawingSheet.layers -- dict of name -> (color, linetype, lineweight)

    Tuple format: (aci_color: int, linetype: str, lineweight: int)
    ACI color index: 1=red 2=yellow 3=green 4=cyan 5=blue 6=magenta
                     7=white/black  8=dark-grey
    Lineweight (hundredths of mm): -1=default 13=0.13mm 25=0.25mm 50=0.50mm
    """
    for name, spec in layers.items():
        if isinstance(spec, tuple):
            color, linetype, lineweight = spec
        else:
            # Duck-type: accept LayerSpec-like objects for forward-compatibility
            color = getattr(spec, "color", 7)
            linetype = getattr(spec, "linetype", "CONTINUOUS")
            lineweight = getattr(spec, "lineweight", -1)

        if name not in doc.layers:
            try:
                doc.layers.new(
                    name=name,
                    dxfattribs={
                        "color": color,
                        "linetype": linetype,
                        "lineweight": lineweight,
                    },
                )
            except Exception:
                # Linetype may not be loaded yet; create without it
                doc.layers.new(
                    name=name,
                    dxfattribs={"color": color, "lineweight": lineweight},
                )


def _ensure_linetypes(doc: _EzdxfDoc) -> None:
    """Load standard linetypes; silently skip if linetype files not found.

    ezdxf ships with CONTINUOUS by default.  DASHED, CENTER, HIDDEN, and
    PHANTOM are in the AutoCAD linetype files.  If they cannot be loaded the
    entities that request them will fall back to CONTINUOUS automatically.
    """
    for lt in ["DASHED", "CENTER", "HIDDEN", "PHANTOM"]:
        if lt not in doc.linetypes:
            for filename in ["ltypeshp.lin", "acad.lin"]:
                try:
                    doc.linetypes.load_linetype_file(lt, filename)
                    break
                except Exception:
                    pass


def _auto_layer(doc: _EzdxfDoc, name: str) -> None:
    """Create a layer with white/black color if it does not already exist."""
    if name and name not in doc.layers:
        doc.layers.new(name=name, dxfattribs={"color": 7})


# ---------------------------------------------------------------------------
# Viewport rendering
# ---------------------------------------------------------------------------


def _vp_empty(vp: ViewPort) -> bool:
    """Return True when every geometry list in the viewport is empty."""
    return not any([
        vp.lines, vp.circles, vp.arcs, vp.rects,
        vp.texts, vp.dimensions, vp.leaders, vp.hatches,
    ])


def _render_viewport(
    doc: _EzdxfDoc,
    msp: _Msp,
    vp: ViewPort,
    dimstyle_name: str,
) -> None:
    """Render all geometry in a ViewPort into the DXF modelspace.

    Consumes: ViewPort (drawing_model.py)

    Render order: hatches -> rects -> lines -> circles -> arcs ->
                  dimensions -> leaders -> texts -> border -> label.

    Coordinate transform applied to every model-space point:
        sheet_x = vp.origin[0] + model_x * vp.scale
        sheet_y = vp.origin[1] + model_y * vp.scale

    Text height is NOT scaled by vp.scale; annotation text height is a
    sheet-space dimension (e.g. 0.1" = 0.1" on the plotted sheet).
    """
    ox, oy = vp.origin
    scale = vp.scale

    def s(pt: Point) -> Tuple[float, float]:
        """Transform model-space point to sheet-space point."""
        return (ox + pt[0] * scale, oy + pt[1] * scale)

    def sv(v: float) -> float:
        """Scale a scalar model-space value to sheet space."""
        return v * scale

    # Pre-create any referenced layers
    for item_list in [
        vp.lines, vp.circles, vp.arcs, vp.rects,
        vp.texts, vp.dimensions, vp.leaders, vp.hatches,
    ]:
        for item in item_list:
            ln = getattr(item, "layer", None)
            if ln:
                _auto_layer(doc, ln)

    # 1. Hatches (background fill; drawn first so geometry sits on top)
    for h in vp.hatches:
        _render_hatch(msp, h, s)

    # 2. Rectangles
    for r in vp.rects:
        _render_rect(msp, r, s, sv)

    # 3. Lines
    for ln in vp.lines:
        _render_line(msp, ln, s)

    # 4. Circles
    for c in vp.circles:
        _render_circle(msp, c, s, sv)

    # 5. Arcs
    for a in vp.arcs:
        _render_arc(msp, a, s, sv)

    # 6. Dimensions
    for d in vp.dimensions:
        _render_dimension(msp, d, s, sv, dimstyle_name)

    # 7. Leaders
    for ldr in vp.leaders:
        _render_leader(msp, ldr, s, sv)

    # 8. Texts (on top of all geometry)
    for t in vp.texts:
        _render_text(msp, t, s, sv)

    # 9. Optional viewport border rectangle
    if getattr(vp, "border", False):
        ext = getattr(vp, "extents", None)
        if ext:
            bw, bh = ext
            pts = [(ox, oy), (ox + bw, oy), (ox + bw, oy + bh), (ox, oy + bh)]
            _auto_layer(doc, "BORDER")
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "BORDER"})

    # 10. Viewport label: underlined text 1/4" below the viewport origin
    if vp.label:
        lbl_layer = getattr(vp, "label_layer", "NOTES")
        _auto_layer(doc, lbl_layer)
        label_y = oy - 0.25
        # %%u is the DXF TEXT underline control code
        msp.add_text(
            "%%u" + vp.label,
            dxfattribs={"layer": lbl_layer, "color": 7, "height": 0.1},
        ).set_placement((ox, label_y))
        scale_label = getattr(vp, "label_scale", None)
        if scale_label:
            msp.add_text(
                scale_label,
                dxfattribs={"layer": lbl_layer, "color": 7, "height": 0.09},
            ).set_placement((ox, label_y - 0.15))


# ---------------------------------------------------------------------------
# Geometry renderers
# ---------------------------------------------------------------------------


def _render_hatch(msp: _Msp, h: HatchSpec, s) -> None:
    """Render a HatchSpec as a DXF HATCH entity.

    Consumes: HatchSpec (drawing_model.py)

    HatchPattern.NONE produces no output (used as a sentinel for no fill).
    Falls back to ANSI31 if the named pattern is not recognised by ezdxf.
    The boundary polygon is closed automatically by ezdxf.
    """
    if h.pattern == HatchPattern.NONE:
        return

    sheet_pts = [s(p) for p in h.boundary_points]
    hatch = msp.add_hatch(color=h.color, dxfattribs={"layer": h.layer})
    hatch.paths.add_polyline_path(sheet_pts, is_closed=True)

    pattern_name = h.pattern.value
    try:
        hatch.set_pattern_fill(pattern_name, scale=h.scale, angle=h.angle)
    except Exception:
        logger.debug("Hatch pattern %r unknown; falling back to ANSI31", pattern_name)
        try:
            hatch.set_pattern_fill("ANSI31", scale=h.scale, angle=h.angle)
        except Exception:
            hatch.set_solid_fill()  # last resort: solid grey


def _render_rect(msp: _Msp, r: RectSpec, s, sv) -> None:
    """Render a RectSpec as a closed LWPolyline.

    Consumes: RectSpec (drawing_model.py)

    RectSpec.origin is the bottom-left corner; width extends right, height up.
    If the rect carries a hatch pattern, a HATCH entity is also added.
    """
    ox, oy = r.origin
    w, h_val = r.width, r.height
    pts = [
        s((ox, oy)),
        s((ox + w, oy)),
        s((ox + w, oy + h_val)),
        s((ox, oy + h_val)),
    ]
    dxfattribs: Dict = {"layer": r.layer, "color": r.color}
    lw = getattr(r, "lineweight", -1)
    if lw not in (-1, -3):
        dxfattribs["lineweight"] = lw
    msp.add_lwpolyline(pts, close=True, dxfattribs=dxfattribs)

    if r.hatch != HatchPattern.NONE:
        hatch_spec = HatchSpec(
            boundary_points=[
                (ox, oy), (ox + w, oy),
                (ox + w, oy + h_val), (ox, oy + h_val),
            ],
            pattern=r.hatch,
            scale=getattr(r, "hatch_scale", 1.0),
            layer=r.layer,
            color=r.color,
        )
        _render_hatch(msp, hatch_spec, s)


def _render_line(msp: _Msp, ln: LineSpec, s) -> None:
    """Render a LineSpec as a DXF LINE entity.

    Consumes: LineSpec (drawing_model.py)
    """
    dxfattribs: Dict = {"layer": ln.layer, "color": ln.color}
    if ln.linetype != LineType.CONTINUOUS:
        dxfattribs["linetype"] = ln.linetype.value
    if ln.lineweight not in (-1, -3):
        dxfattribs["lineweight"] = ln.lineweight
    msp.add_line(s(ln.start), s(ln.end), dxfattribs=dxfattribs)


def _render_circle(msp: _Msp, c: CircleSpec, s, sv) -> None:
    """Render a CircleSpec as a DXF CIRCLE entity.

    Consumes: CircleSpec (drawing_model.py)

    If CircleSpec.filled is True a solid HATCH fill is also added, using a
    36-point polygon approximation of the circle boundary.
    """
    center_s = s(c.center)
    radius_s = sv(c.radius)
    msp.add_circle(
        center_s, radius_s,
        dxfattribs={"layer": c.layer, "color": c.color},
    )

    if getattr(c, "filled", False):
        n = 36
        ring_pts = [
            (c.center[0] + c.radius * math.cos(2 * math.pi * i / n),
             c.center[1] + c.radius * math.sin(2 * math.pi * i / n))
            for i in range(n)
        ]
        sheet_pts = [s(p) for p in ring_pts]
        hatch = msp.add_hatch(color=c.color, dxfattribs={"layer": c.layer})
        hatch.paths.add_polyline_path(sheet_pts, is_closed=True)
        hatch.set_solid_fill(color=c.color)


def _render_arc(msp: _Msp, a: ArcSpec, s, sv) -> None:
    """Render an ArcSpec as a DXF ARC entity.

    Consumes: ArcSpec (drawing_model.py)

    Angles are in degrees CCW from +X, matching ezdxf convention directly.
    """
    msp.add_arc(
        s(a.center),
        sv(a.radius),
        start_angle=a.start_angle,
        end_angle=a.end_angle,
        dxfattribs={"layer": a.layer, "color": a.color},
    )


# ---------------------------------------------------------------------------
# Dimension rendering
# ---------------------------------------------------------------------------


def _render_dimension(
    msp: _Msp,
    d: DimensionSpec,
    s,
    sv,
    default_dimstyle: str,
) -> None:
    """Render a DimensionSpec as a DXF linear dimension entity.

    Consumes: DimensionSpec (drawing_model.py)

    Dimension line placement per DimSide:
      TOP:    horizontal dim; base Y = max(p1y, p2y) + offset  (above object)
      BOTTOM: horizontal dim; base Y = min(p1y, p2y) - offset  (below object)
      LEFT:   vertical dim;   base X = min(p1x, p2x) - offset  (left)
      RIGHT:  vertical dim;   base X = max(p1x, p2x) + offset  (right)

    Key ezdxf gotcha: dimpost MUST contain "<>" as the measured-value
    placeholder (e.g. '<>" REVEAL').  A literal string without "<>" raises
    DXFValueError.  Use set_text() for a full text override instead.

    dim.render() must be called after set_text() to materialise geometry.
    """
    p1s = s(d.p1)
    p2s = s(d.p2)
    offset_s = sv(d.offset)

    if d.side == DimSide.TOP:
        base_y = max(p1s[1], p2s[1]) + offset_s
        base = ((p1s[0] + p2s[0]) / 2.0, base_y)
        angle = 0
    elif d.side == DimSide.BOTTOM:
        base_y = min(p1s[1], p2s[1]) - offset_s
        base = ((p1s[0] + p2s[0]) / 2.0, base_y)
        angle = 0
    elif d.side == DimSide.LEFT:
        base_x = min(p1s[0], p2s[0]) - offset_s
        base = (base_x, (p1s[1] + p2s[1]) / 2.0)
        angle = 90
    else:  # DimSide.RIGHT
        base_x = max(p1s[0], p2s[0]) + offset_s
        base = (base_x, (p1s[1] + p2s[1]) / 2.0)
        angle = 90

    dimstyle = d.dimstyle if d.dimstyle else default_dimstyle

    # Build per-dimension overrides on top of the named dimstyle
    override: Dict = {}
    if d.dimdec != 0:
        override["dimdec"] = d.dimdec
    if d.dimlfac != 1.0:
        override["dimlfac"] = d.dimlfac
    if d.dimpost is not None:
        if "<>" not in d.dimpost:
            logger.warning(
                "DimensionSpec.dimpost %r is missing the <> placeholder -- "
                "dimpost suppressed to avoid DXFValueError",
                d.dimpost,
            )
        else:
            override["dimpost"] = d.dimpost

    dim = msp.add_linear_dim(
        base=base,
        p1=p1s,
        p2=p2s,
        angle=angle,
        dimstyle=dimstyle,
        dxfattribs={"layer": d.layer},
        override=override if override else None,
    )

    # Full text override: replaces the measured value entirely
    if d.text_override is not None:
        dim.set_text(d.text_override)

    dim.render()


# ---------------------------------------------------------------------------
# Leader rendering
# ---------------------------------------------------------------------------


def _render_leader(msp: _Msp, ldr: LeaderSpec, s, sv) -> None:
    """Render a LeaderSpec as lines + filled arrowhead + MText.

    Consumes: LeaderSpec (drawing_model.py)

    Geometry layout:
        arrow_point ---leader_line--- landing_point ---shelf(0.25")--- [text]

    The shelf is always 0.25 sheet-inches long (not viewport-scaled; the shelf
    and text are sheet-space annotation elements, not model-space geometry).
    Text lines stack above the shelf end, descending with index (i=0 topmost).

    Arrowhead: filled SOLID triangle at arrow_point.
    """
    arrow_s = s(ldr.arrow_point)
    land_s = s(ldr.landing_point)
    layer = ldr.layer
    color = ldr.color
    th = ldr.text_height

    # ASME Y14.2-2023: leaders should be 30-60 degrees from horizontal
    dx = land_s[0] - arrow_s[0]
    dy = land_s[1] - arrow_s[1]
    if abs(dx) > 1e-6 and abs(dy) > 1e-6:
        angle = abs(math.degrees(math.atan2(dy, dx)))
        if angle < 30 or (angle > 60 and angle < 120) or angle > 150:
            logger.debug(
                "Leader angle %.1f deg outside ASME Y14.2 recommended 30-60 deg range",
                angle,
            )
    elif abs(dx) < 1e-6 or abs(dy) < 1e-6:
        logger.debug(
            "Leader is horizontal or vertical; ASME Y14.2 recommends 30-60 deg angle"
        )

    # Leader line (arrow tip -> landing point)
    msp.add_line(arrow_s, land_s, dxfattribs={"layer": layer, "color": color})

    # Horizontal shelf (0.25" to the right of landing)
    shelf_len = 0.25
    shelf_end = (land_s[0] + shelf_len, land_s[1])
    msp.add_line(land_s, shelf_end, dxfattribs={"layer": layer, "color": color})

    # Filled arrowhead at the arrow tip
    if ldr.has_arrow:
        _draw_filled_arrow(
            msp, arrow_s, land_s, size=0.06, layer=layer, color=color
        )

    # MText lines stacked above shelf end (top-to-bottom)
    if ldr.text_lines:
        spacing = th * 1.5
        tx = shelf_end[0] + 0.02   # small gap from shelf end
        n = len(ldr.text_lines)
        for i, line_text in enumerate(ldr.text_lines):
            # i=0 is the topmost line; descend with increasing i
            ty = land_s[1] + spacing * (n - i - 1) + th * 0.5
            msp.add_mtext(
                line_text,
                dxfattribs={
                    "char_height": th,
                    "insert": (tx, ty),
                    "layer": layer,
                    "color": color,
                    "attachment_point": 1,  # top-left
                },
            )


def _draw_filled_arrow(
    msp: _Msp,
    tip: Tuple[float, float],
    base_ref: Tuple[float, float],
    size: float,
    layer: str,
    color: int,
) -> None:
    """Draw a filled triangular arrowhead at tip pointing toward base_ref.

    Uses ezdxf SOLID entity (4 vertices; last two identical = triangle).
    The arrow points FROM base_ref TOWARD tip.
    """
    dx = base_ref[0] - tip[0]
    dy = base_ref[1] - tip[1]
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return

    ux, uy = dx / length, dy / length  # unit vector along shaft direction
    px, py = -uy, ux                    # unit vector perpendicular to shaft

    half_w = size / 3.0
    # Arrow base: size inches back from tip along the shaft
    bx = tip[0] + ux * size
    by = tip[1] + uy * size

    v0 = tip
    v1 = (bx + px * half_w, by + py * half_w)
    v2 = (bx - px * half_w, by - py * half_w)
    # SOLID requires 4 points; duplicate last for triangle form
    msp.add_solid(
        [v0, v1, v2, v2],
        dxfattribs={"layer": layer, "color": color},
    )


# ---------------------------------------------------------------------------
# Text rendering
# ---------------------------------------------------------------------------


def _render_text(msp: _Msp, t: TextSpec, s, sv) -> None:
    """Render a TextSpec as a DXF TEXT entity.

    Consumes: TextSpec (drawing_model.py)

    t.halign: "LEFT" | "CENTER" | "RIGHT"
    t.valign: "BASELINE" | "BOTTOM" | "MIDDLE" | "TOP"

    Text height is NOT multiplied by the viewport scale.  Annotation text
    height is specified in sheet units (e.g. 0.1" prints as 0.1" on paper).
    """
    from ezdxf.enums import TextEntityAlignment as _TEA

    # Map halign/valign string pairs to TextEntityAlignment enum values
    halign = (t.halign or "LEFT").upper()
    valign = (t.valign or "BASELINE").upper()

    _align_map = {
        ("LEFT",   "BASELINE"): _TEA.LEFT,
        ("CENTER", "BASELINE"): _TEA.CENTER,
        ("RIGHT",  "BASELINE"): _TEA.RIGHT,
        ("LEFT",   "BOTTOM"):   _TEA.BOTTOM_LEFT,
        ("CENTER", "BOTTOM"):   _TEA.BOTTOM_CENTER,
        ("RIGHT",  "BOTTOM"):   _TEA.BOTTOM_RIGHT,
        ("LEFT",   "MIDDLE"):   _TEA.MIDDLE_LEFT,
        ("CENTER", "MIDDLE"):   _TEA.MIDDLE_CENTER,
        ("RIGHT",  "MIDDLE"):   _TEA.MIDDLE_RIGHT,
        ("LEFT",   "TOP"):      _TEA.TOP_LEFT,
        ("CENTER", "TOP"):      _TEA.TOP_CENTER,
        ("RIGHT",  "TOP"):      _TEA.TOP_RIGHT,
    }
    align_enum = _align_map.get((halign, valign), _TEA.LEFT)

    insert_s = s(t.insert)
    dxfattribs: Dict = {
        "layer": t.layer,
        "color": t.color,
        "height": t.height,
        "rotation": t.rotation,
    }

    ent = msp.add_text(t.text, dxfattribs=dxfattribs)
    if align_enum == _TEA.LEFT:
        ent.set_placement(insert_s)
    else:
        ent.set_placement(insert_s, align=align_enum)


# ---------------------------------------------------------------------------
# Note block rendering
# ---------------------------------------------------------------------------


def _render_note_block(msp: _Msp, nb: NoteBlock) -> None:
    """Render a NoteBlock as stacked DXF TEXT entities.

    Consumes: NoteBlock (drawing_model.py)

    Title is rendered at the origin; notes descend in Y by nb.line_spacing.
    Supports both "notes" and "lines" as the list attribute name.
    """
    ox, oy = nb.origin
    layer = nb.layer
    th = nb.text_height
    spacing = nb.line_spacing

    y = oy

    # Title (optional; NoteBlock default is "NOTES")
    title = getattr(nb, "title", None)
    if title == "NOTES":
        msp.add_text(
            "NOTES:",
            dxfattribs={"layer": layer, "color": 7, "height": th * 1.2},
        ).set_placement((ox, y))
        y -= spacing * 1.4
    elif title:
        msp.add_text(
            title,
            dxfattribs={"layer": layer, "color": 7, "height": th * 1.4},
        ).set_placement((ox, y))
        y -= spacing * 1.5

    # Support both "notes" (DrawingModel) and "lines" (future)
    note_list: List[str] = getattr(nb, "notes", None) or getattr(nb, "lines", [])

    for note_text in note_list:
        msp.add_text(
            note_text,
            dxfattribs={"layer": layer, "color": 7, "height": th},
        ).set_placement((ox, y))
        y -= spacing


# ---------------------------------------------------------------------------
# Title block rendering
# ---------------------------------------------------------------------------

# Layout constants (sheet inches)
_TB_TEXT_H    = 0.09    # standard field text height
_TB_TEXT_H_LG = 0.14    # company name / drawing title height
_TB_INN       = 0.08    # inner border inset from outer border edge
_TB_RSPLIT    = 0.70    # fraction of width where right column starts
_TB_PAD       = 0.12    # padding from border edge to text


def _render_title_block(msp: _Msp, tb: TitleBlock) -> None:
    """Render a TitleBlock as border lines and text entities.

    Consumes: TitleBlock (drawing_model.py)

    Layout:
      Double-line border (outer heavy + inner medium) with a vertical divider
      at 70% of the block width.  Horizontal row dividers in the right column.

      Left column  (70%): company name, project, drawing title, scale
      Right column (30%): drawing number, revision, date, drawn/chk, sheet
    """
    ox, oy = tb.origin
    w = tb.width
    h = tb.height
    layer = getattr(tb, "layer", "TITLEBLOCK")
    text_layer = getattr(tb, "text_layer", "NOTES")

    doc = msp.doc
    for ln in [layer, text_layer]:
        if ln not in doc.layers:
            doc.layers.new(name=ln, dxfattribs={"color": 7})

    # Outer border (heavy 0.50mm)
    _rect_outline(msp, ox, oy, w, h, layer=layer, lineweight=50)

    # Inner border (medium 0.25mm, inset)
    _rect_outline(
        msp,
        ox + _TB_INN, oy + _TB_INN,
        w - 2 * _TB_INN, h - 2 * _TB_INN,
        layer=layer, lineweight=25,
    )

    # Vertical divider between left and right columns
    div_x = ox + w * _TB_RSPLIT
    msp.add_line(
        (div_x, oy + _TB_INN),
        (div_x, oy + h - _TB_INN),
        dxfattribs={"layer": layer, "lineweight": 25},
    )

    # Horizontal row dividers in the right column
    num_right_rows = 5
    row_h = (h - 2 * _TB_INN) / num_right_rows
    for row in range(1, num_right_rows):
        ry = oy + _TB_INN + row * row_h
        msp.add_line(
            (div_x, ry),
            (ox + w - _TB_INN, ry),
            dxfattribs={"layer": layer, "lineweight": 13},
        )

    # ---- Left column ----
    cx = ox + _TB_PAD
    ly = oy + h - _TB_PAD - _TB_TEXT_H_LG

    msp.add_text(
        tb.company,
        dxfattribs={"layer": text_layer, "color": 7, "height": _TB_TEXT_H_LG},
    ).set_placement((cx, ly))
    ly -= _TB_TEXT_H_LG * 1.8

    if tb.project:
        msp.add_text(
            f"PROJECT: {tb.project}",
            dxfattribs={"layer": text_layer, "color": 7, "height": _TB_TEXT_H},
        ).set_placement((cx, ly))
    ly -= _TB_TEXT_H * 1.6

    if tb.drawing_title:
        msp.add_text(
            tb.drawing_title,
            dxfattribs={"layer": text_layer, "color": 7, "height": _TB_TEXT_H * 1.15},
        ).set_placement((cx, ly))
    ly -= _TB_TEXT_H * 1.6

    if tb.scale:
        msp.add_text(
            f"SCALE: {tb.scale}",
            dxfattribs={"layer": text_layer, "color": 7, "height": _TB_TEXT_H},
        ).set_placement((cx, ly))

    # ---- Right column ----
    rx = div_x + _TB_PAD
    ry = oy + h - _TB_INN - _TB_PAD - _TB_TEXT_H

    _tb_text(msp, f"DWG NO: {tb.drawing_number}", rx, ry, text_layer, _TB_TEXT_H * 1.1)
    ry -= row_h
    _tb_text(msp, f"REV: {tb.revision}", rx, ry, text_layer, _TB_TEXT_H)
    ry -= row_h
    _tb_text(msp, f"DATE: {tb.date}", rx, ry, text_layer, _TB_TEXT_H)
    ry -= row_h
    drawn_line = f"DWN: {tb.drawn_by}"
    if tb.checked_by:
        drawn_line += f"   CHK: {tb.checked_by}"
    _tb_text(msp, drawn_line, rx, ry, text_layer, _TB_TEXT_H)
    ry -= row_h
    _tb_text(msp, f"SHEET: {tb.sheet}", rx, ry, text_layer, _TB_TEXT_H)


def _tb_text(
    msp: _Msp,
    text: str,
    x: float,
    y: float,
    layer: str,
    height: float,
) -> None:
    """Add a title block field text entity; suppress empty or None fields."""
    if not text or text.rstrip().endswith(":") or "None" in text:
        return
    msp.add_text(
        text,
        dxfattribs={"layer": layer, "color": 7, "height": height},
    ).set_placement((x, y))


def _rect_outline(
    msp: _Msp,
    x: float,
    y: float,
    w: float,
    h: float,
    layer: str,
    lineweight: int = -1,
) -> None:
    """Draw a closed rectangular LWPolyline at sheet-space coordinates."""
    pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    dxfattribs: Dict = {"layer": layer}
    if lineweight != -1:
        dxfattribs["lineweight"] = lineweight
    msp.add_lwpolyline(pts, close=True, dxfattribs=dxfattribs)
