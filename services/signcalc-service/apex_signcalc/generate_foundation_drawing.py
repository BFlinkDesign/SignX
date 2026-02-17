"""
Generate a professional caisson foundation drawing using DEC-002 Drawing Model.

Produces a multi-view engineering drawing:
  1. SECTION ELEVATION — Full cross-section with rebar cage, post, base plate,
     anchor bolts, concrete hatching, grade line, dimensions
  2. ANCHOR BOLT PLAN — Top view showing bolt pattern, base plate, caisson OD
  3. REBAR CAGE DETAIL — Cage assembly with vertical bars, ties, cover
  4. NOTES + BOM — Foundation notes and bill of materials
  5. TITLE BLOCK — Eagle Sign Co standard

Quality target: real Eagle Sign shop drawings from G: drive.

SCALING RULES (critical — violated these on v1):
  - All geometry coordinates are in MODEL INCHES (real-world size)
  - Viewport.scale transforms model → sheet:  sheet_pt = origin + model_pt * scale
  - Text heights in LeaderSpec/TextSpec are SHEET INCHES (not model)
    → typical callout text: 0.08"   title text: 0.12"
  - Dimension text comes from dimstyle.dimtxt (0.10" in SIGNX dimstyle)
  - Dimensions measure SHEET distances; use dimlfac = 1/scale to show REAL dims
"""

from __future__ import annotations

import math
import os

from drawing_model import (
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
    TextSpec,
    ViewPort,
    new_sheet,
)
from dxf_renderer import render_to_dxf, render_preview
from foundation_embed import design_foundation


def _ft_in(inches: float) -> str:
    """Format inches as feet-inches string: 84 → 7'-0\", 90 → 7'-6\"."""
    ft = int(inches // 12)
    rem = inches % 12
    if rem < 0.1:
        return f"{ft}'-0\""
    return f"{ft}'-{rem:.0f}\""


def generate_foundation_drawing(
    # Sign parameters
    customer: str = "ACME CORPORATION",
    project_name: str = "MONUMENT SIGN",
    wo_number: str = "0226-40668",
    sign_width_in: float = 120.0,
    sign_height_in: float = 72.0,
    sign_depth_in: float = 24.0,
    # Post parameters
    post_type: str = "HSS 6x6x3/8",
    post_width_in: float = 6.0,
    num_posts: int = 2,
    caisson_dia_in: float = 24.0,
    soil_type: str = "medium_sand",
    wind_load_lbf: float = 3200.0,
    force_height_ft: float = 12.0,
    # Base plate / anchor bolts
    bp_size_in: float = 14.0,
    bp_thick_in: float = 0.75,
    num_bolts: int = 4,
    bolt_dia_in: float = 0.75,
    bolt_embed_in: float = 12.0,
    bolt_circle_in: float = 10.0,
    # Rebar (ACI 318-19: min 0.5% Ag for drilled shafts, ties per 10.7.6.1)
    num_vert_bars: int = 8,
    vert_bar_size: str = "#5",
    tie_bar_size: str = "#3",
    tie_spacing_in: float = 10.0,
    clear_cover_in: float = 3.0,
    # Concrete
    fc_psi: int = 4000,
    # Output
    output_dir: str = ".",
) -> dict:
    """Generate a complete foundation drawing package."""

    # ── Run foundation design ──────────────────────────────────────────
    caisson_dia_ft = caisson_dia_in / 12.0
    result = design_foundation(
        lateral_force_lbf=wind_load_lbf,
        moment_at_grade_ftlb=0,
        height_to_force_ft=force_height_ft,
        soil_type=soil_type,
        shaft_diameter_ft=caisson_dia_ft,
        method="all",
    )

    # Use max of PE methods (ignore IBC for concrete caissons)
    eng = {k: v for k, v in result["all_results"].items() if k != "ibc"}
    gov_method = max(eng, key=lambda k: eng[k].get("L_design_ft", 0))
    gov_depth_ft = eng[gov_method].get("L_design_ft", result["embedment_ft"])
    gov_depth_ft = math.ceil(gov_depth_ft * 2) / 2.0  # round up to 6"
    embed_in = gov_depth_ft * 12.0

    cage_od_in = caisson_dia_in - 2 * clear_cover_in
    cage_height_in = embed_in - 2 * clear_cover_in
    conc_vol = math.pi * (caisson_dia_ft / 2) ** 2 * gov_depth_ft / 27.0

    # ── ACI 318-19 rebar validation ─────────────────────────────────────
    Ag = math.pi / 4.0 * caisson_dia_in**2
    bar_areas = {"#3": 0.11, "#4": 0.20, "#5": 0.31, "#6": 0.44, "#7": 0.60, "#8": 0.79}
    Ab = bar_areas.get(vert_bar_size, 0.31)
    As_provided = num_vert_bars * Ab
    As_min = 0.005 * Ag  # ACI 318-19 Section 14.3.6.3.1
    if As_provided < As_min:
        import warnings
        needed = math.ceil(As_min / Ab)
        if needed % 2 != 0:
            needed += 1  # round up to even for symmetry
        warnings.warn(
            f"ACI 318-19 §14.3.6.3.1: {num_vert_bars} {vert_bar_size} = "
            f"{As_provided:.2f} sq.in. < 0.5% Ag = {As_min:.2f} sq.in. "
            f"(need {needed} {vert_bar_size} bars)",
            stacklevel=2,
        )

    D = caisson_dia_in
    L = embed_in
    pw = post_width_in
    bp = bp_size_in
    bar_r = 0.3125 if "5" in vert_bar_size else 0.25

    # ── Sheet setup ───────────────────────────────────────────────────
    sheet = new_sheet(
        project=f"{customer} - {project_name}",
        title="CAISSON FOUNDATION DETAIL",
        dwg_no=wo_number,
        size="D",
    )
    sheet.title_block.date = "02/17/2026"
    sheet.title_block.drawn_by = "SIGNX"
    sheet.title_block.checked_by = "PE"
    sheet.title_block.scale = "AS NOTED"

    # ── Text height constants (SHEET inches) ──────────────────────────
    TH_CALLOUT = 0.08   # leader text
    TH_LABEL = 0.12     # view labels
    TH_NOTE = 0.065     # notes block
    TH_GRADE = 0.10     # grade/annotation

    # ══════════════════════════════════════════════════════════════════
    # VIEW 1: SECTION ELEVATION  (left 55% of sheet)
    # ══════════════════════════════════════════════════════════════════
    # Model extents: width = D + 50 (leaders), height = L + 20 (post stub)
    model_h = L + 20
    sec_scale = min(16.0 / model_h, 10.0 / (D + 50))
    sec_scale = round(sec_scale, 3)
    sec_dimlfac = 1.0 / sec_scale

    sec = ViewPort(
        name="SECTION ELEVATION",
        origin=(5.0, 4.0),
        scale=sec_scale,
        label="SECTION ELEVATION",
        label_scale=f"SCALE: {sec_scale:.3f}",
    )

    # -- Caisson outline --
    for start, end in [
        ((0, 0), (D, 0)), ((D, 0), (D, L)),
        ((D, L), (0, L)), ((0, L), (0, 0)),
    ]:
        sec.lines.append(LineSpec(
            start=start, end=end, layer="CONCRETE", color=8, lineweight=50,
        ))

    # -- Concrete hatch (ANSI31 diagonal lines — renders cleanly in preview+DXF) --
    sec.hatches.append(HatchSpec(
        boundary_points=[(0, 0), (D, 0), (D, L), (0, L)],
        pattern=HatchPattern.CONCRETE, scale=1.5, angle=45, layer="HATCH", color=8,
    ))

    # -- Base plate --
    bp_x = (D - bp) / 2.0
    bp_y = L
    for start, end in [
        ((bp_x, bp_y), (bp_x + bp, bp_y)),
        ((bp_x + bp, bp_y), (bp_x + bp, bp_y + bp_thick_in)),
        ((bp_x + bp, bp_y + bp_thick_in), (bp_x, bp_y + bp_thick_in)),
        ((bp_x, bp_y + bp_thick_in), (bp_x, bp_y)),
    ]:
        sec.lines.append(LineSpec(
            start=start, end=end, layer="STEEL", color=1, lineweight=50,
        ))

    # -- Post stub --
    post_x = (D - pw) / 2.0
    post_top = bp_y + bp_thick_in + 18
    sec.lines.append(LineSpec(
        start=(post_x, bp_y + bp_thick_in), end=(post_x, post_top),
        layer="STEEL", color=1, lineweight=35,
    ))
    sec.lines.append(LineSpec(
        start=(post_x + pw, bp_y + bp_thick_in), end=(post_x + pw, post_top),
        layer="STEEL", color=1, lineweight=35,
    ))
    # Break lines
    for dy in [-1, 1]:
        sec.lines.append(LineSpec(
            start=(post_x - 2, post_top + dy),
            end=(post_x + pw + 2, post_top - dy),
            layer="STEEL", color=1,
        ))

    # -- Anchor bolts (J-bolts in section) --
    bc_half = bolt_circle_in / 2.0
    for bx in [D / 2.0 - bc_half, D / 2.0 + bc_half]:
        # Shank
        sec.lines.append(LineSpec(
            start=(bx, L - bolt_embed_in), end=(bx, L + bp_thick_in + 2),
            layer="STEEL", color=1, linetype=LineType.DASHED,
        ))
        # J-hook
        hook_dir = 1.5 if bx < D / 2 else -1.5
        sec.lines.append(LineSpec(
            start=(bx, L - bolt_embed_in),
            end=(bx + hook_dir, L - bolt_embed_in),
            layer="STEEL", color=1,
        ))
        # Nut (two short lines)
        for ny in [1, 2]:
            sec.lines.append(LineSpec(
                start=(bx - 0.75, L + bp_thick_in + ny),
                end=(bx + 0.75, L + bp_thick_in + ny),
                layer="STEEL", color=1, lineweight=35,
            ))

    # -- Rebar cage (vertical bars shown as filled circles at two depths) --
    cage_r = cage_od_in / 2.0
    for i in range(num_vert_bars):
        angle = 2.0 * math.pi * i / num_vert_bars
        bx = D / 2.0 + cage_r * math.cos(angle)
        for by in [clear_cover_in + 3, L - clear_cover_in - 3]:
            sec.circles.append(CircleSpec(
                center=(bx, by), radius=bar_r * 3,
                layer="REBAR", color=3, filled=True,
            ))

    # -- Tie bars (horizontal dashed) --
    ty = clear_cover_in
    while ty < L - clear_cover_in:
        sec.lines.append(LineSpec(
            start=(D / 2.0 - cage_r, ty), end=(D / 2.0 + cage_r, ty),
            layer="REBAR", color=3, linetype=LineType.DASHED,
        ))
        ty += tie_spacing_in

    # -- Centerline --
    sec.lines.append(LineSpec(
        start=(D / 2.0, -5), end=(D / 2.0, post_top + 5),
        layer="CENTERLINE", color=1, linetype=LineType.CENTER,
    ))

    # -- Grade line + earth marks --
    sec.lines.append(LineSpec(
        start=(-12, L), end=(0, L), layer="NOTES", color=7, lineweight=35,
    ))
    sec.lines.append(LineSpec(
        start=(D, L), end=(D + 12, L), layer="NOTES", color=7, lineweight=35,
    ))
    for ex in range(-10, 0, 3):
        sec.lines.append(LineSpec(
            start=(ex, L), end=(ex - 2, L - 3), layer="NOTES", color=7,
        ))
    for ex in range(int(D) + 2, int(D) + 12, 3):
        sec.lines.append(LineSpec(
            start=(ex, L), end=(ex - 2, L - 3), layer="NOTES", color=7,
        ))
    sec.texts.append(TextSpec(
        insert=(-12, L + 2), text="GRADE", height=TH_GRADE,
        layer="NOTES", color=7,
    ))

    # ── SECTION DIMENSIONS ──
    # All need dimlfac so sheet-space measurements show real inches
    sec.dimensions.append(DimensionSpec(
        p1=(0, 0), p2=(D, 0), side=DimSide.BOTTOM, offset=8,
        dimpost='<>" DIA.', dimlfac=sec_dimlfac, layer="DIMENSIONS",
    ))
    sec.dimensions.append(DimensionSpec(
        p1=(D, 0), p2=(D, L), side=DimSide.RIGHT, offset=8,
        text_override=_ft_in(embed_in), dimlfac=sec_dimlfac, layer="DIMENSIONS",
    ))
    sec.dimensions.append(DimensionSpec(
        p1=(D / 2.0 - bc_half, L + bp_thick_in + 3),
        p2=(D / 2.0 + bc_half, L + bp_thick_in + 3),
        side=DimSide.TOP, offset=3,
        dimpost='<>" B.C.', dimlfac=sec_dimlfac, dimdec=1, layer="DIMENSIONS",
    ))
    sec.dimensions.append(DimensionSpec(
        p1=(bp_x, bp_y + bp_thick_in + 3), p2=(bp_x + bp, bp_y + bp_thick_in + 3),
        side=DimSide.TOP, offset=8,
        dimpost='<>" SQ BASE PL', dimlfac=sec_dimlfac, layer="DIMENSIONS",
    ))
    sec.dimensions.append(DimensionSpec(
        p1=(0, L - bolt_embed_in), p2=(0, L),
        side=DimSide.LEFT, offset=8,
        dimpost='<>" EMBED', dimlfac=sec_dimlfac, layer="DIMENSIONS",
    ))
    sec.dimensions.append(DimensionSpec(
        p1=(0, 0), p2=(0, clear_cover_in),
        side=DimSide.LEFT, offset=14,
        dimpost='<>" CLR', dimlfac=sec_dimlfac, layer="DIMENSIONS",
    ))

    # -- Conduit sleeve (2" PVC through caisson) --
    conduit_x = D * 0.35  # offset from center
    conduit_r = 1.25  # 2" PVC schedule 40 OD ≈ 2.375, show as 2.5" hole
    sec.circles.append(CircleSpec(
        center=(conduit_x, L - 6), radius=conduit_r,
        layer="NOTES", color=4,
    ))
    sec.lines.append(LineSpec(
        start=(conduit_x, L - 6 - conduit_r), end=(conduit_x, 0),
        layer="NOTES", color=4, linetype=LineType.DASHED,
    ))

    # ── SECTION LEADERS ──
    # Leader landing points go to right side of caisson, stacked vertically
    right_x = D + 18  # model inches to the right (compact)
    sec.leaders.append(LeaderSpec(
        arrow_point=(post_x + pw / 2, post_top - 5),
        landing_point=(right_x, post_top - 2),
        text_lines=[post_type, "ASTM A500 GR. C, Fy = 46 KSI"],
        layer="NOTES", text_height=TH_CALLOUT,
    ))
    sec.leaders.append(LeaderSpec(
        arrow_point=(bp_x + bp / 2, bp_y + bp_thick_in / 2),
        landing_point=(right_x, bp_y + 2),
        text_lines=[f'{bp:.0f}" x {bp:.0f}" x {bp_thick_in}" BASE PL', "ASTM A36 STEEL"],
        layer="NOTES", text_height=TH_CALLOUT,
    ))
    sec.leaders.append(LeaderSpec(
        arrow_point=(D / 2.0 + bc_half, L - bolt_embed_in / 2),
        landing_point=(right_x, L - bolt_embed_in + 2),
        text_lines=[
            f'({num_bolts}) {bolt_dia_in}" DIA. J-BOLTS',
            f'{bolt_embed_in}" EMBED, {bolt_circle_in}" B.C.',
            "ASTM F1554 GR. 36, HDG",
        ],
        layer="NOTES", text_height=TH_CALLOUT,
    ))
    sec.leaders.append(LeaderSpec(
        arrow_point=(D / 2.0 + cage_r, clear_cover_in + 3),
        landing_point=(right_x, clear_cover_in + 12),
        text_lines=[
            f"({num_vert_bars}) {vert_bar_size} VERT. BARS",
            f"{tie_bar_size} TIES @ {tie_spacing_in:.0f}\" O.C.",
            f'{clear_cover_in:.0f}" CLR COVER ALL AROUND',
            "ASTM A615 GR. 60",
        ],
        layer="NOTES", text_height=TH_CALLOUT,
    ))
    # Concrete callout (left side — compact landing)
    sec.leaders.append(LeaderSpec(
        arrow_point=(D / 4, L / 2),
        landing_point=(-14, L / 2 + 6),
        text_lines=[
            f"CONCRETE f'c = {fc_psi} PSI",
            f'{D:.0f}" DIA. x {_ft_in(embed_in)} DEEP',
            f"{conc_vol:.2f} CY PER CAISSON",
        ],
        layer="NOTES", text_height=TH_CALLOUT,
    ))
    # Conduit callout (placed left-center, below grade)
    sec.leaders.append(LeaderSpec(
        arrow_point=(conduit_x, L - 6),
        landing_point=(-16, L - 20),
        text_lines=[
            '2" PVC CONDUIT SLEEVE',
            "FOR ELECTRICAL/DATA",
        ],
        layer="NOTES", text_height=TH_CALLOUT,
    ))

    sheet.viewports.append(sec)

    # ══════════════════════════════════════════════════════════════════
    # VIEW 2: ANCHOR BOLT PLAN  (top-right of sheet)
    # ══════════════════════════════════════════════════════════════════
    plan_scale = min(7.0 / (D + 15), 7.0 / (D + 15))
    plan_scale = round(plan_scale, 3)
    plan_dimlfac = 1.0 / plan_scale

    plan = ViewPort(
        name="ANCHOR BOLT PLAN",
        origin=(23.0, 14.5),
        scale=plan_scale,
        label="ANCHOR BOLT PLAN",
        label_scale=f"SCALE: {plan_scale:.3f}",
    )

    # Caisson circle
    plan.circles.append(CircleSpec(
        center=(D / 2, D / 2), radius=D / 2,
        layer="CONCRETE", color=8,
    ))
    # Cage circle (dashed)
    plan.circles.append(CircleSpec(
        center=(D / 2, D / 2), radius=cage_od_in / 2,
        layer="REBAR", color=3,
    ))
    # Base plate
    bp_ox = (D - bp) / 2.0
    bp_oy = (D - bp) / 2.0
    for start, end in [
        ((bp_ox, bp_oy), (bp_ox + bp, bp_oy)),
        ((bp_ox + bp, bp_oy), (bp_ox + bp, bp_oy + bp)),
        ((bp_ox + bp, bp_oy + bp), (bp_ox, bp_oy + bp)),
        ((bp_ox, bp_oy + bp), (bp_ox, bp_oy)),
    ]:
        plan.lines.append(LineSpec(
            start=start, end=end, layer="STEEL", color=1, lineweight=35,
        ))
    # Post
    pp_ox = (D - pw) / 2.0
    pp_oy = (D - pw) / 2.0
    for start, end in [
        ((pp_ox, pp_oy), (pp_ox + pw, pp_oy)),
        ((pp_ox + pw, pp_oy), (pp_ox + pw, pp_oy + pw)),
        ((pp_ox + pw, pp_oy + pw), (pp_ox, pp_oy + pw)),
        ((pp_ox, pp_oy + pw), (pp_ox, pp_oy)),
    ]:
        plan.lines.append(LineSpec(
            start=start, end=end, layer="STEEL", color=1, lineweight=50,
        ))
    # Bolts at 45° positions
    bc_r = bolt_circle_in / 2.0
    for i in range(num_bolts):
        angle = math.pi / 4 + 2.0 * math.pi * i / num_bolts
        bx = D / 2.0 + bc_r * math.cos(angle)
        by = D / 2.0 + bc_r * math.sin(angle)
        # Bolt hole (unfilled circle) + bolt shank (filled smaller)
        plan.circles.append(CircleSpec(
            center=(bx, by), radius=bolt_dia_in * 0.7,
            layer="STEEL", color=1,
        ))
        plan.circles.append(CircleSpec(
            center=(bx, by), radius=bolt_dia_in * 0.4,
            layer="STEEL", color=1, filled=True,
        ))
    # Rebar dots
    for i in range(num_vert_bars):
        angle = 2.0 * math.pi * i / num_vert_bars
        rx = D / 2.0 + cage_od_in / 2.0 * math.cos(angle)
        ry = D / 2.0 + cage_od_in / 2.0 * math.sin(angle)
        plan.circles.append(CircleSpec(
            center=(rx, ry), radius=bar_r * 2.5,
            layer="REBAR", color=3, filled=True,
        ))
    # Bolt circle (dashed)
    plan.circles.append(CircleSpec(
        center=(D / 2, D / 2), radius=bc_r, layer="DIMENSIONS", color=2,
    ))
    # Conduit sleeve in plan (2" PVC)
    plan.circles.append(CircleSpec(
        center=(conduit_x, D / 2 - 4), radius=conduit_r,
        layer="NOTES", color=4,
    ))
    # Centerlines
    plan.lines.append(LineSpec(
        start=(D / 2, -3), end=(D / 2, D + 3),
        layer="CENTERLINE", color=1, linetype=LineType.CENTER,
    ))
    plan.lines.append(LineSpec(
        start=(-3, D / 2), end=(D + 3, D / 2),
        layer="CENTERLINE", color=1, linetype=LineType.CENTER,
    ))

    # Plan dimensions
    plan.dimensions.append(DimensionSpec(
        p1=(0, D / 2), p2=(D, D / 2), side=DimSide.BOTTOM, offset=5,
        dimpost='<>" DIA.', dimlfac=plan_dimlfac, layer="DIMENSIONS",
    ))
    plan.dimensions.append(DimensionSpec(
        p1=(bp_ox, bp_oy + bp), p2=(bp_ox + bp, bp_oy + bp),
        side=DimSide.TOP, offset=D / 2 - bp / 2 + 3,
        dimpost='<>" SQ', dimlfac=plan_dimlfac, layer="DIMENSIONS",
    ))
    # Plan leaders
    plan.leaders.append(LeaderSpec(
        arrow_point=(D / 2 + bc_r * 0.707, D / 2 + bc_r * 0.707),
        landing_point=(D + 6, D + 4),
        text_lines=[f'{bolt_circle_in}" B.C.', f'({num_bolts}) BOLTS @ 90\u00b0'],
        layer="NOTES", text_height=TH_CALLOUT,
    ))
    plan.leaders.append(LeaderSpec(
        arrow_point=(D / 2 + cage_od_in / 2 * 0.707, D / 2 - cage_od_in / 2 * 0.707),
        landing_point=(D + 6, -2),
        text_lines=[f'{cage_od_in:.0f}" CAGE O.D.', f'({num_vert_bars}) {vert_bar_size}'],
        layer="NOTES", text_height=TH_CALLOUT,
    ))

    sheet.viewports.append(plan)

    # ══════════════════════════════════════════════════════════════════
    # VIEW 3: REBAR CAGE DETAIL  (bottom-right of sheet)
    # ══════════════════════════════════════════════════════════════════
    cage_w = cage_od_in
    cage_h = cage_height_in
    cage_scale = min(6.0 / (cage_h + 20), 4.0 / (cage_w + 25))
    cage_scale = round(cage_scale, 3)
    cage_dimlfac = 1.0 / cage_scale

    cage = ViewPort(
        name="REBAR CAGE DETAIL",
        origin=(23.0, 4.0),
        scale=cage_scale,
        label="REBAR CAGE DETAIL",
        label_scale=f"SCALE: {cage_scale:.3f}",
    )

    # Cage outline
    for start, end in [
        ((0, 0), (cage_w, 0)), ((cage_w, 0), (cage_w, cage_h)),
        ((cage_w, cage_h), (0, cage_h)), ((0, cage_h), (0, 0)),
    ]:
        cage.lines.append(LineSpec(
            start=start, end=end, layer="REBAR", color=3, lineweight=35,
        ))
    # Vertical bars
    bar_sp = cage_w / (num_vert_bars - 1) if num_vert_bars > 1 else cage_w / 2
    for i in range(num_vert_bars):
        bx = i * bar_sp
        cage.lines.append(LineSpec(
            start=(bx, 0), end=(bx, cage_h),
            layer="REBAR", color=3, lineweight=25,
        ))
        cage.lines.append(LineSpec(
            start=(bx, 0), end=(bx + 3, -3), layer="REBAR", color=3,
        ))
    # Tie bars
    ty = 3.0
    while ty < cage_h - 2:
        cage.lines.append(LineSpec(
            start=(0, ty), end=(cage_w, ty),
            layer="REBAR", color=3, linetype=LineType.DASHED,
        ))
        ty += tie_spacing_in

    # Cage dimensions
    cage.dimensions.append(DimensionSpec(
        p1=(0, 0), p2=(cage_w, 0), side=DimSide.BOTTOM, offset=8,
        dimpost='<>" O.D.', dimlfac=cage_dimlfac, layer="DIMENSIONS",
    ))
    cage.dimensions.append(DimensionSpec(
        p1=(cage_w, 0), p2=(cage_w, cage_h), side=DimSide.RIGHT, offset=6,
        text_override=f'{cage_height_in:.0f}"', layer="DIMENSIONS",
    ))
    cage.dimensions.append(DimensionSpec(
        p1=(0, 3.0), p2=(0, 3.0 + tie_spacing_in),
        side=DimSide.LEFT, offset=6,
        dimpost='<>" O.C. TYP', dimlfac=cage_dimlfac, layer="DIMENSIONS",
    ))
    cage.leaders.append(LeaderSpec(
        arrow_point=(bar_sp, cage_h / 2),
        landing_point=(cage_w + 12, cage_h * 0.7),
        text_lines=[f'{vert_bar_size} VERT.', f'{clear_cover_in:.0f}" CLR'],
        layer="NOTES", text_height=TH_CALLOUT,
    ))
    cage.leaders.append(LeaderSpec(
        arrow_point=(cage_w / 2, 3.0 + tie_spacing_in / 2),
        landing_point=(cage_w + 12, cage_h * 0.3),
        text_lines=[f'{tie_bar_size} TIES', f'{tie_spacing_in:.0f}" O.C.'],
        layer="NOTES", text_height=TH_CALLOUT,
    ))

    sheet.viewports.append(cage)

    # ══════════════════════════════════════════════════════════════════
    # NOTES
    # ══════════════════════════════════════════════════════════════════
    broms_d = eng.get("broms", {}).get("L_design_ft", "N/A")
    hansen_d = eng.get("hansen", {}).get("L_design_ft", "N/A")
    czerniak_d = eng.get("czerniak", {}).get("L_design_ft", "N/A")
    if isinstance(broms_d, float):
        broms_d = f"{broms_d:.1f}"
    if isinstance(hansen_d, float):
        hansen_d = f"{hansen_d:.1f}"
    if isinstance(czerniak_d, float):
        czerniak_d = f"{czerniak_d:.1f}"

    notes = NoteBlock(
        origin=(3.0, 2.5),
        title="FOUNDATION NOTES",
        notes=[
            f"1. CONCRETE: {fc_psi} PSI @ 28 DAYS, NORMAL WEIGHT (150 PCF)",
            f"2. REBAR: ASTM A615 GRADE 60",
            f"3. ANCHOR BOLTS: ASTM F1554 GR. 36, HOT-DIP GALVANIZED",
            f"4. BASE PLATE: ASTM A36 STEEL",
            f"5. POST: {post_type}, ASTM A500 GR. C, Fy = 46 KSI",
            f"6. SOIL: {soil_type.upper().replace('_', ' ')} (IBC TABLE 1806.2)",
            f"7. WIND: {wind_load_lbf:.0f} LBF @ {force_height_ft:.1f}' AGL",
            f"8. GOVERNING: {gov_method.upper()} = {gov_depth_ft:.1f}' EMBED",
            f"9. BROMS={broms_d}' HANSEN={hansen_d}' CZERNIAK={czerniak_d}'",
            f"10. {clear_cover_in:.0f}\" MIN CLR COVER ON ALL REBAR",
            f"11. PROVIDE 2\" PVC CONDUIT SLEEVE FOR ELECTRICAL/DATA",
            f"12. VERIFY SOIL CONDITIONS BEFORE POUR",
            f"13. ALL WORK PER IBC 2021 CH.18 & ACI 318-19",
        ],
        text_height=TH_NOTE,
        line_spacing=0.12,
    )
    sheet.note_blocks.append(notes)

    # ══════════════════════════════════════════════════════════════════
    # RENDER
    # ══════════════════════════════════════════════════════════════════
    os.makedirs(output_dir, exist_ok=True)
    dxf_path = os.path.join(output_dir, f"foundation_{wo_number}.dxf")
    png_path = os.path.join(output_dir, f"foundation_{wo_number}.png")

    render_to_dxf(sheet, dxf_path)
    preview_path = render_preview(sheet, png_path, dpi=200)

    return {
        "dxf_path": dxf_path,
        "png_path": preview_path,
        "design_result": result,
        "governing_method": gov_method,
        "governing_depth_ft": gov_depth_ft,
        "embed_in": embed_in,
        "conc_cy": round(conc_vol, 2),
        "scales": {
            "section": sec_scale,
            "plan": plan_scale,
            "cage": cage_scale,
        },
    }


if __name__ == "__main__":
    out = generate_foundation_drawing(
        customer="DAIRY QUEEN",
        project_name="ALTOONA MONUMENT SIGN",
        wo_number="0226-40700",
        sign_width_in=120,
        sign_height_in=68,
        sign_depth_in=24,
        post_type="HSS 4x4x3/16",
        post_width_in=4.0,
        num_posts=2,
        caisson_dia_in=24,
        wind_load_lbf=2800,
        force_height_ft=10.0,
        soil_type="medium_sand",
        bp_size_in=12,
        bp_thick_in=0.75,
        bolt_circle_in=9.5,
        bolt_embed_in=12,
        num_vert_bars=8,
        tie_spacing_in=10,
        fc_psi=4000,
        output_dir=r"C:\Temp",
    )
    print(f"DXF: {out['dxf_path']}")
    print(f"PNG: {out['png_path']}")
    print(f"Governing: {out['governing_method']} @ {out['governing_depth_ft']}' deep")
    print(f"Concrete: {out['conc_cy']} cy")
    print(f"Scales: {out['scales']}")
