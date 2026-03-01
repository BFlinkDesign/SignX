"""
extract_pf_from_pdf.py — Extract Peripheral Feet from PDF vectors.

Uses PyMuPDF (fitz) to walk all vector paths in a PDF page, compute bezier
curve lengths, and sum them to get total peripheral feet (PF).

Best results by PDF type:
  - Gemini Art (1:1 pages): ~11% variance vs CorelDRAW macro
  - Cut files: Include extra paths (weeds, registration). PF too high.
  - Conceptual PDFs (letter-size): Vectors are annotations, not letter
    outlines. Use scale_factor ~2.75 for Eagle conceptuals, or prefer
    the footage chart for reliable PF.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import fitz  # PyMuPDF


@dataclass
class LetterMeasurement:
    """Measurements for a single letter/shape."""
    index: int
    perimeter_inches: float
    area_sq_inches: float
    height_inches: float
    width_inches: float

    @property
    def perimeter_feet(self) -> float:
        return self.perimeter_inches / 12.0

    @property
    def area_sq_feet(self) -> float:
        return self.area_sq_inches / 144.0


@dataclass
class PDFExtraction:
    """Result of extracting peripheral feet from a PDF."""
    filename: str
    page_number: int
    letters: list[LetterMeasurement] = field(default_factory=list)
    total_perimeter_inches: float = 0.0
    total_area_sq_inches: float = 0.0
    letter_count: int = 0
    max_height_inches: float = 0.0
    min_height_inches: float = 0.0
    median_height_inches: float = 0.0
    representative_height_inches: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def total_pf(self) -> float:
        """Total peripheral feet."""
        return self.total_perimeter_inches / 12.0

    @property
    def total_face_sf(self) -> float:
        """Total face area in square feet."""
        return self.total_area_sq_inches / 144.0


def _bezier_length(p0: tuple, p1: tuple, p2: tuple, p3: tuple,
                   subdivisions: int = 128) -> float:
    """Approximate cubic bezier curve length via subdivision."""
    length = 0.0
    prev = p0
    for i in range(1, subdivisions + 1):
        t = i / subdivisions
        t2 = t * t
        t3 = t2 * t
        mt = 1 - t
        mt2 = mt * mt
        mt3 = mt2 * mt

        x = mt3 * p0[0] + 3 * mt2 * t * p1[0] + 3 * mt * t2 * p2[0] + t3 * p3[0]
        y = mt3 * p0[1] + 3 * mt2 * t * p1[1] + 3 * mt * t2 * p2[1] + t3 * p3[1]

        dx = x - prev[0]
        dy = y - prev[1]
        length += math.sqrt(dx * dx + dy * dy)
        prev = (x, y)
    return length


def _quad_bezier_length(p0: tuple, p1: tuple, p2: tuple,
                        subdivisions: int = 128) -> float:
    """Approximate quadratic bezier curve length via subdivision."""
    length = 0.0
    prev = p0
    for i in range(1, subdivisions + 1):
        t = i / subdivisions
        mt = 1 - t
        x = mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0]
        y = mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1]
        dx = x - prev[0]
        dy = y - prev[1]
        length += math.sqrt(dx * dx + dy * dy)
        prev = (x, y)
    return length


def _line_length(p0: tuple, p1: tuple) -> float:
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    return math.sqrt(dx * dx + dy * dy)


def _polygon_area(points: list[tuple]) -> float:
    """Shoelace formula for polygon area (approximate for curves)."""
    n = len(points)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2.0


def extract_pf_from_pdf(pdf_bytes: bytes, filename: str = "upload.pdf",
                        page_num: int = 0,
                        scale_factor: float = 0.0,
                        known_letter_height: float = 0.0) -> PDFExtraction:
    """
    Extract peripheral feet from a conceptual PDF.

    Walks all vector drawing commands on the specified page, computes
    perimeter of each closed path (letter outline), and sums them.

    Args:
        pdf_bytes: Raw PDF file content.
        filename: Original filename for reporting.
        page_num: Which page to analyze (0-indexed).
        scale_factor: Manual scale multiplier (0 = auto-detect).
            For Gemini Art / cut files (1:1 scale): leave at 0 (auto = 1.0).
            For conceptual PDFs on letter-size paper: typically 2.5-3.5x.
        known_letter_height: Actual letter height in inches (0 = not provided).
            When provided on a scaled-down conceptual PDF, auto-computes
            scale_factor from (known_height / detected_max_height).

    Returns:
        PDFExtraction with per-letter and total measurements.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    result = PDFExtraction(filename=filename, page_number=page_num)

    if page_num >= len(doc):
        result.warnings.append(f"Page {page_num} does not exist (PDF has {len(doc)} pages)")
        doc.close()
        return result

    page = doc[page_num]
    # PDF units are points (1/72 inch)
    pts_to_inches = 1.0 / 72.0

    # Page size for scale detection
    page_w_in = page.rect.width * pts_to_inches
    page_h_in = page.rect.height * pts_to_inches

    paths = page.get_drawings()

    if not paths:
        result.warnings.append("No vector paths found on this page. Is this a raster PDF?")
        doc.close()
        return result

    # Determine scale factor
    if scale_factor > 0:
        sf = scale_factor
    elif known_letter_height > 0:
        # First pass: collect heights of all significant paths
        raw_heights = []
        for path in paths:
            items = path.get("items", [])
            ys = []
            path_perim = 0.0
            for item in items:
                cmd = item[0]
                if cmd == "l":
                    ys.extend([item[1].y, item[2].y])
                    p0 = (item[1].x, item[1].y)
                    p1 = (item[2].x, item[2].y)
                    path_perim += _line_length(p0, p1)
                elif cmd == "c":
                    ys.extend([item[1].y, item[4].y])
                    path_perim += _bezier_length(
                        (item[1].x, item[1].y), (item[2].x, item[2].y),
                        (item[3].x, item[3].y), (item[4].x, item[4].y),
                    )
                elif cmd == "re":
                    ys.extend([item[1].y0, item[1].y1])
                    path_perim += 2 * (abs(item[1].width) + abs(item[1].height))
                elif cmd == "qu":
                    quad = item[1]
                    ys.extend([quad.ul.y, quad.ur.y, quad.lr.y, quad.ll.y])
            if ys:
                h = (max(ys) - min(ys)) * pts_to_inches
                perim_in = path_perim * pts_to_inches
                # Only consider substantial shapes (not tiny noise)
                if h > 0.5 and perim_in > 1.0:
                    raw_heights.append(h)
        if raw_heights:
            raw_heights.sort()
            # Use median height (robust to outlier serifs/ascenders)
            mid = len(raw_heights) // 2
            if len(raw_heights) % 2 == 0:
                repr_h = (raw_heights[mid - 1] + raw_heights[mid]) / 2.0
            else:
                repr_h = raw_heights[mid]
            sf = known_letter_height / repr_h
            result.warnings.append(
                f"Auto-scale: median height {repr_h:.1f}\" (n={len(raw_heights)}), "
                f"known height {known_letter_height:.0f}\" -> scale {sf:.2f}x"
            )
        else:
            sf = 1.0
    elif max(page_w_in, page_h_in) > 24.0:
        sf = 1.0
    else:
        sf = 1.0
        result.warnings.append(
            f"Page is {page_w_in:.1f}\" x {page_h_in:.1f}\" (standard paper). "
            "Letters are likely scaled down. Provide known_letter_height or "
            "scale_factor, or use Gemini Art / cut files for accurate PF."
        )

    letter_idx = 0
    min_height = float("inf")
    max_height = 0.0

    for path in paths:
        items = path.get("items", [])
        if not items:
            continue

        # Walk path items and compute perimeter + area
        perimeter = 0.0
        path_points = []
        current = None
        is_closed = path.get("closePath", False)

        for item in items:
            cmd = item[0]

            if cmd == "l":  # line
                p0 = (item[1].x, item[1].y)
                p1 = (item[2].x, item[2].y)
                perimeter += _line_length(p0, p1)
                path_points.append(p0)
                current = p1

            elif cmd == "c":  # cubic bezier
                p0 = (item[1].x, item[1].y)
                p1 = (item[2].x, item[2].y)
                p2 = (item[3].x, item[3].y)
                p3 = (item[4].x, item[4].y)
                perimeter += _bezier_length(p0, p1, p2, p3)
                # Sample points for area approximation
                for t_i in range(0, 33, 4):
                    t = t_i / 32.0
                    mt = 1 - t
                    x = (mt**3 * p0[0] + 3 * mt**2 * t * p1[0]
                         + 3 * mt * t**2 * p2[0] + t**3 * p3[0])
                    y = (mt**3 * p0[1] + 3 * mt**2 * t * p1[1]
                         + 3 * mt * t**2 * p2[1] + t**3 * p3[1])
                    path_points.append((x, y))
                current = p3

            elif cmd == "qu":  # quad (4-point area, not quadratic bezier)
                # PyMuPDF "qu" items contain a Quad object with corners
                quad = item[1]
                # Quad has ul, ur, lr, ll (upper-left, upper-right, etc.)
                corners = [
                    (quad.ul.x, quad.ul.y),
                    (quad.ur.x, quad.ur.y),
                    (quad.lr.x, quad.lr.y),
                    (quad.ll.x, quad.ll.y),
                ]
                for ci in range(4):
                    cj = (ci + 1) % 4
                    perimeter += _line_length(corners[ci], corners[cj])
                path_points.extend(corners)
                current = corners[-1]

            elif cmd == "re":  # rectangle
                rect = item[1]
                w = abs(rect.width)
                h = abs(rect.height)
                perimeter += 2 * (w + h)
                path_points.extend([
                    (rect.x0, rect.y0), (rect.x1, rect.y0),
                    (rect.x1, rect.y1), (rect.x0, rect.y1),
                ])

        if current:
            path_points.append(current)

        # Filter out tiny paths (noise, guidelines, etc.)
        perimeter_in = perimeter * pts_to_inches * sf
        if perimeter_in < 1.0:
            continue

        # Compute area from sampled points
        area_pts = _polygon_area(path_points) if len(path_points) >= 3 else 0.0
        area_in = area_pts * pts_to_inches * pts_to_inches * sf * sf

        # Compute bounding box for height/width
        if path_points:
            xs = [p[0] for p in path_points]
            ys = [p[1] for p in path_points]
            width_in = (max(xs) - min(xs)) * pts_to_inches * sf
            height_in = (max(ys) - min(ys)) * pts_to_inches * sf
        else:
            width_in = 0.0
            height_in = 0.0

        letter = LetterMeasurement(
            index=letter_idx,
            perimeter_inches=perimeter_in,
            area_sq_inches=area_in,
            height_inches=height_in,
            width_inches=width_in,
        )
        result.letters.append(letter)
        result.total_perimeter_inches += perimeter_in
        result.total_area_sq_inches += area_in

        if height_in > max_height:
            max_height = height_in
        if height_in < min_height:
            min_height = height_in

        letter_idx += 1

    result.letter_count = letter_idx
    result.max_height_inches = max_height
    result.min_height_inches = min_height if min_height != float("inf") else 0.0

    # Compute representative height (median of all shape heights)
    if result.letters:
        heights = sorted(ltr.height_inches for ltr in result.letters)
        mid = len(heights) // 2
        if len(heights) % 2 == 0:
            result.median_height_inches = (heights[mid - 1] + heights[mid]) / 2.0
        else:
            result.median_height_inches = heights[mid]
        # Representative = median (robust to outlier serifs/ascenders)
        result.representative_height_inches = result.median_height_inches

    if letter_idx == 0:
        result.warnings.append(
            "No significant vector paths found. The PDF may contain only "
            "raster images or very small decorative elements."
        )

    doc.close()
    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python extract_pf_from_pdf.py <file.pdf> [page_num]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    page = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    with open(pdf_path, "rb") as f:
        data = f.read()

    result = extract_pf_from_pdf(data, filename=pdf_path, page_num=page)

    print(f"\n{'=' * 60}")
    print(f"PDF Extraction: {result.filename} (page {result.page_number})")
    print(f"{'=' * 60}")
    print(f"Letters/Shapes found: {result.letter_count}")
    print(f"Total Peripheral Feet: {result.total_pf:.2f} ft")
    print(f"Total Face Area: {result.total_face_sf:.2f} sq ft")
    print(f"Height range: {result.min_height_inches:.1f}\" - {result.max_height_inches:.1f}\"")

    if result.warnings:
        print(f"\nWarnings:")
        for w in result.warnings:
            print(f"  - {w}")

    if result.letters:
        print(f"\nPer-shape detail:")
        for ltr in result.letters[:20]:
            print(f"  #{ltr.index}: PF={ltr.perimeter_feet:.2f} ft, "
                  f"Area={ltr.area_sq_feet:.2f} sf, "
                  f"H={ltr.height_inches:.1f}\" W={ltr.width_inches:.1f}\"")
        if len(result.letters) > 20:
            print(f"  ... and {len(result.letters) - 20} more")
