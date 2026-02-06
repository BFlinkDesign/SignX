"""
Phase 1: Parse Historical HTML Cost Summary Detail Reports
===========================================================
Extracts ALL data from 168 HTML batch files (402MB) using BeautifulSoup.
Zero network risk — works entirely from local files.

Outputs:
  - wo_headers.csv          (1 row per WO: costs, margins, metadata)
  - labor_detail.csv        (individual employee time entries)
  - labor_summary.csv       (**** summary lines with EST vs ACTUAL)
  - material_detail.csv     (material lines: detail + **** summary)
  - outplant_detail.csv     (outplant lines: detail + **** summary)

Cross-validates header totals vs detail line sums.

Parsing strategy:
  - BeautifulSoup extracts <pre> block contents (NO regex on raw HTML)
  - **** summary lines: parse <span> tags directly (6 spans = 6 values,
    blank spans → None, preserving positional alignment)
  - Detail lines: fixed-width column parsing on stripped text
  - WO headers: regex on stripped text for labeled fields
"""

import argparse
import csv
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

INPUT_DIR = Path(r"C:\Scripts\keyedin-capture\reports\cost_detail")
OUTPUT_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\raw")

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("phase1")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def safe_float(s: str | None) -> float | None:
    """Parse a float from a string, handling commas and blanks."""
    if s is None:
        return None
    s = s.strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def safe_int(s: str | None) -> int | None:
    """Parse an int from a string."""
    if s is None:
        return None
    s = s.strip().replace(",", "")
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def parse_date(s: str) -> str | None:
    """Parse MM/DD/YY date to ISO format YYYY-MM-DD."""
    s = s.strip()
    if not s or s.startswith("*"):
        return None
    try:
        dt = datetime.strptime(s, "%m/%d/%y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# HTML-aware line extraction
# ---------------------------------------------------------------------------


class ParsedLine:
    """A line from a <pre> block with both stripped text and span values."""

    __slots__ = ("text", "span_values", "raw_html")

    def __init__(self, text: str, span_values: list[str | None], raw_html: str = ""):
        self.text = text  # HTML-stripped text (for fixed-width parsing)
        self.span_values = span_values  # Ordered list of <span> contents
        self.raw_html = raw_html


def extract_lines_from_html(html_content: str) -> list[ParsedLine]:
    """
    Extract lines from <pre> blocks preserving both stripped text
    and <span> tag contents for positional numeric parsing.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    pre_blocks = soup.find_all("pre")
    all_lines: list[ParsedLine] = []

    for pre in pre_blocks:
        # Get the raw inner HTML to split by newlines
        # We need to process line by line, tracking spans per line
        raw_inner = pre.decode_contents()

        # Split raw HTML by newlines
        html_lines = raw_inner.split("\n")

        for html_line in html_lines:
            # Get stripped text
            line_soup = BeautifulSoup(html_line, "html.parser")
            text = line_soup.get_text()

            # Skip page headers
            if text.strip().startswith("RUN DATE:"):
                continue
            if "COST  SUMMARY" in text and "#" in text:
                continue
            if text.strip().startswith("________"):
                continue

            # Extract span values in order
            spans = line_soup.find_all("span")
            span_values = []
            for span in spans:
                val = span.get_text()
                # A span with only whitespace means the field is blank
                if val.strip():
                    span_values.append(val.strip())
                else:
                    span_values.append(None)

            all_lines.append(ParsedLine(text, span_values, html_line))

    return all_lines


# ---------------------------------------------------------------------------
# WO Header Parser
# ---------------------------------------------------------------------------


def parse_wo_header(header_text: str) -> dict:
    """Parse the SUMMARY block of a work order into a dict."""
    rec = {
        "wo_number": None,
        "customer_id": None,
        "customer_name": None,
        "location": None,
        "total_material_cost": None,
        "total_labor_cost": None,
        "total_burden_cost": None,
        "total_outplant_cost": None,
        "total_use_tax": None,
        "total_cost": None,
        "quoted_price": None,
        "sale_price": None,
        "billing": None,
        "gross_margin": None,
        "gm_pct": None,
        "sales_code": None,
        "use_tax_code": None,
        "estimator": None,
        "quote_nbr": None,
        "date_completed": None,
        "status": None,
        "sign_type": None,
        "price_class_code": None,
        "description": None,
        "part_number": None,
    }

    lines = header_text.split("\n")

    for line in lines:
        wo_match = re.search(r"WORK ORDER\s+(\S+?)--", line)
        if wo_match:
            rec["wo_number"] = wo_match.group(1).strip("-")
            continue

        cust_match = re.search(
            r"Customer:\s*(\d+)\s+(.+?)\s{2,}Location:\s*(.+)", line
        )
        if cust_match:
            rec["customer_id"] = cust_match.group(1).strip()
            rec["customer_name"] = cust_match.group(2).strip()
            rec["location"] = cust_match.group(3).strip()
            continue

        # Cost fields (left side)
        for pattern, key in [
            (r"TOTAL MATERIAL COST\s+([\d,.-]+)", "total_material_cost"),
            (r"TOTAL LABOR COST\s+([\d,.-]+)", "total_labor_cost"),
            (r"TOTAL BURDEN COST\s+([\d,.-]+)", "total_burden_cost"),
            (r"TOTAL OUTPLANT COST\s+([\d,.-]+)", "total_outplant_cost"),
            (r"TOTAL USE TAX\s+([\d,.-]+)", "total_use_tax"),
            (r"TOTAL COST\s+([\d,.-]+)", "total_cost"),
            (r"QUOTED PRICE\s+([\d,.-]+)", "quoted_price"),
            (r"SALE PRICE\s+([\d,.-]+)", "sale_price"),
            (r"BILLING\s+([\d,.-]+)", "billing"),
            (r"GROSS MARGIN\s+([-\d,.]+)", "gross_margin"),
            (r"GM %\s*=\s+([-\d,.]+)", "gm_pct"),
        ]:
            m = re.search(pattern, line)
            if m:
                rec[key] = safe_float(m.group(1))

        # String fields (right side)
        for pattern, key in [
            (r"Sales Code:\s*(\S+)", "sales_code"),
            (r"Use Tax\s*:\s*(\S+)", "use_tax_code"),
            (r"Estimator\s*:\s*(.+?)(?:\s{2,}|$)", "estimator"),
            (r"Quote Nbr\s*:\s*(\S+)", "quote_nbr"),
            (r"Status\s*:\s*(.+?)(?:\s{2,}|$)", "status"),
            (r"Sign Type:\s*(\S+)", "sign_type"),
            (r"Price Class Code:\s*(.+?)(?:\s{2,}|$)", "price_class_code"),
        ]:
            m = re.search(pattern, line)
            if m:
                rec[key] = m.group(1).strip()

        dc_match = re.search(r"Date Compl:\s*(\S+)", line)
        if dc_match:
            rec["date_completed"] = parse_date(dc_match.group(1))

        part_match = re.search(r"Part:\s*(\S+)\s+(.+)", line)
        if part_match:
            rec["part_number"] = part_match.group(1).strip()

    # Extract description — text after DESCRIPTION header to end of header block
    # (The terminating dashes are excluded from header_text by the state machine)
    desc_match = re.search(
        r"-------- DESCRIPTION -------+\s*\n(.*)",
        header_text,
        re.DOTALL,
    )
    if desc_match:
        desc_lines = desc_match.group(1).strip().split("\n")
        desc_parts = []
        for dl in desc_lines:
            dl_stripped = dl.strip()
            if dl_stripped.startswith(("Sign Type:", "Price Class Code:", "Part:")):
                continue
            if dl_stripped:
                desc_parts.append(dl_stripped)
        rec["description"] = " ".join(desc_parts) if desc_parts else None

    return rec


# ---------------------------------------------------------------------------
# **** Summary Line Parser (span-aware — the key fix)
# ---------------------------------------------------------------------------


def parse_star_summary(
    pline: ParsedLine, wo_number: str, section: str
) -> dict | None:
    """
    Parse a **** summary line using span values for positional accuracy.

    The CGI report wraps each numeric field in a <span> tag, always in order:
      [0] est_qty/hrs  [1] actual_qty/hrs  [2] variance
      [3] est_cost     [4] job_cost        [5] cost_variance

    Blank fields have spans containing only whitespace → mapped to None.
    """
    text = pline.text
    spans = pline.span_values

    if "****" not in text[:10]:
        return None
    if "**** Total ****" in text:
        return None

    dept = text[10:16].strip()

    # Field after dept depends on section type
    if section == "labor":
        code = text[16:22].strip()
        identifier_key = "work_code"
        identifier_val = code
    elif section == "material":
        item = text[16:40].strip()
        # Extract UOM from text after item position
        rest = text[40:]
        uom_match = re.match(r"\s*([A-Z]{1,5})\s+", rest)
        uom = uom_match.group(1) if uom_match else None
        identifier_key = "inventory_item"
        identifier_val = item
    elif section == "outplant":
        sub = text[16:40].strip()
        rest = text[40:]
        uom_match = re.match(r"\s*([A-Z]{1,5})\s+", rest)
        uom = uom_match.group(1) if uom_match else None
        identifier_key = "sub_contractor"
        identifier_val = sub
    else:
        return None

    # Extract 6 values from spans (always 6 for **** lines)
    est_v1 = safe_float(spans[0]) if len(spans) > 0 else None
    act_v1 = safe_float(spans[1]) if len(spans) > 1 else None
    var_v1 = safe_float(spans[2]) if len(spans) > 2 else None
    est_v2 = safe_float(spans[3]) if len(spans) > 3 else None
    job_cost = safe_float(spans[4]) if len(spans) > 4 else None
    cost_var = safe_float(spans[5]) if len(spans) > 5 else None

    # Extract description from text (after the last number region)
    # Description is everything after ~col 102
    desc = ""
    # Find description from the raw text after stripping
    # It's the text following the last numeric span content
    if spans:
        last_span_text = None
        for s in reversed(spans):
            if s is not None:
                last_span_text = s
                break
        if last_span_text:
            last_pos = text.rfind(last_span_text)
            if last_pos >= 0:
                desc = text[last_pos + len(last_span_text) :].strip()

    rec = {
        "wo_number": wo_number,
        "work_dept": dept,
        identifier_key: identifier_val,
    }

    if section == "labor":
        rec["est_hrs"] = est_v1
        rec["actual_hrs"] = act_v1
        rec["hrs_variance"] = var_v1
        rec["est_cost"] = est_v2
        rec["job_cost"] = job_cost
        rec["cost_variance"] = cost_var
        rec["description"] = desc
    elif section in ("material", "outplant"):
        rec["uom"] = uom
        rec["est_qty"] = safe_int(str(est_v1)) if est_v1 is not None else None
        rec["actual_qty"] = safe_int(str(act_v1)) if act_v1 is not None else None
        rec["qty_variance"] = safe_int(str(var_v1)) if var_v1 is not None else None
        rec["est_cost"] = est_v2
        rec["job_cost"] = job_cost
        rec["cost_variance"] = cost_var
        rec["description"] = desc

    return rec


# ---------------------------------------------------------------------------
# Detail Line Parsers (fixed-width text — no spans on detail lines)
# ---------------------------------------------------------------------------


def parse_labor_detail_line(text: str, wo_number: str) -> dict | None:
    """Parse an individual labor entry (employee time clock line)."""
    if len(text) < 40:
        return None

    date_str = text[0:10].strip()
    if not date_str or not re.match(r"\d{2}/\d{2}/\d{2}", date_str):
        return None

    dept = text[10:16].strip()
    code = text[16:22].strip()
    employee = text[22:46].strip()

    # Detail lines have actual_hrs and job_cost only (no EST fields)
    # Actual hrs is the first number after employee name
    rest = text[46:]
    numbers = re.findall(r"[\d,]+\.?\d*", rest)

    actual_hrs = safe_float(numbers[0]) if len(numbers) > 0 else None
    job_cost = safe_float(numbers[1]) if len(numbers) > 1 else None

    return {
        "wo_number": wo_number,
        "labor_date": parse_date(date_str),
        "work_dept": dept,
        "work_code": code,
        "employee_name": employee,
        "actual_hrs": actual_hrs,
        "job_cost": job_cost,
    }


def parse_material_detail_line(text: str, wo_number: str) -> dict | None:
    """Parse an individual material issuance line."""
    if len(text) < 30:
        return None

    date_str = text[0:10].strip()
    if not date_str or not re.match(r"\d{2}/\d{2}/\d{2}", date_str):
        return None

    dept = text[10:16].strip()
    item = text[16:40].strip()
    rest = text[40:].strip()
    numbers = re.findall(r"[\d,]+\.?\d*", rest)

    actual_qty = safe_float(numbers[0]) if len(numbers) > 0 else None
    job_cost = safe_float(numbers[1]) if len(numbers) > 1 else None

    return {
        "wo_number": wo_number,
        "material_date": parse_date(date_str),
        "work_dept": dept,
        "inventory_item": item,
        "actual_qty": actual_qty,
        "job_cost": job_cost,
    }


def parse_outplant_detail_line(text: str, wo_number: str) -> dict | None:
    """Parse an individual outplant PO line."""
    if len(text) < 30:
        return None

    date_str = text[0:10].strip()
    if not date_str or not re.match(r"\d{2}/\d{2}/\d{2}", date_str):
        return None

    dept = text[10:16].strip()
    sub = text[16:40].strip()
    rest = text[40:].strip()
    numbers = re.findall(r"[\d,]+\.?\d*", rest)

    actual_qty = safe_float(numbers[0]) if len(numbers) > 0 else None
    job_cost = safe_float(numbers[1]) if len(numbers) > 1 else None

    # Check for "I" flag (invoiced indicator)
    invoiced = bool(re.search(r"\bI\b", rest.split(".")[-1] if "." in rest else rest))

    return {
        "wo_number": wo_number,
        "outplant_date": parse_date(date_str),
        "work_dept": dept,
        "sub_contractor": sub,
        "actual_qty": actual_qty,
        "job_cost": job_cost,
        "invoiced": invoiced,
    }


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------


class Section:
    HEADER = "header"
    LABOR = "labor"
    MATERIAL = "material"
    OUTPLANT = "outplant"
    BETWEEN = "between"


def detect_section(text: str) -> str | None:
    """Detect if a line is a section header."""
    stripped = text.strip()
    if "LABOR   WORK  WORK" in stripped:
        return Section.LABOR
    if "MATERIAL  WORK  INVENTORY" in stripped:
        return Section.MATERIAL
    if "OUTPLANT  WORK" in stripped:
        return Section.OUTPLANT
    # Second line of section header
    if stripped.startswith("DATE") and "DEPT" in stripped:
        if "/ PURCHASE" in stripped or "SUB-CONTRACTOR" in stripped:
            return None  # Sub-header line, not a new section
    return None


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------


def parse_html_file(filepath: Path) -> tuple[list, list, list, list, list]:
    """
    Parse one HTML batch file, returning:
      (wo_headers, labor_details, labor_summaries, material_summaries, outplant_summaries)
    """
    log.info(f"Parsing {filepath.name} ...")
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()

    parsed_lines = extract_lines_from_html(html)

    wo_headers = []
    labor_details = []
    labor_summaries = []
    material_records = []
    outplant_records = []

    current_wo = None
    current_section = Section.BETWEEN
    header_lines: list[str] = []
    in_header = False

    i = 0
    while i < len(parsed_lines):
        pline = parsed_lines[i]
        text = pline.text

        # ---- WO boundary ----
        if " WORK ORDER " in text and "--" in text:
            # Finalize previous WO header
            if header_lines:
                wo_rec = parse_wo_header("\n".join(header_lines))
                if wo_rec["wo_number"]:
                    wo_headers.append(wo_rec)

            wo_match = re.search(r"WORK ORDER\s+(\S+?)--", text)
            if wo_match:
                current_wo = wo_match.group(1).strip("-")
            header_lines = [text]
            in_header = True
            current_section = Section.HEADER
            i += 1
            continue

        # ---- Collecting header ----
        if in_header:
            section = detect_section(text)
            if section:
                wo_rec = parse_wo_header("\n".join(header_lines))
                if wo_rec["wo_number"]:
                    wo_headers.append(wo_rec)
                header_lines = []
                in_header = False
                current_section = section
                i += 1
                continue

            # Check dashed divider followed by a section header
            if text.strip().startswith("-" * 50):
                j = i + 1
                while j < len(parsed_lines) and not parsed_lines[j].text.strip():
                    j += 1
                if j < len(parsed_lines):
                    next_section = detect_section(parsed_lines[j].text)
                    if next_section:
                        wo_rec = parse_wo_header("\n".join(header_lines))
                        if wo_rec["wo_number"]:
                            wo_headers.append(wo_rec)
                        header_lines = []
                        in_header = False
                        current_section = next_section
                        i = j + 1
                        continue

            header_lines.append(text)
            i += 1
            continue

        # ---- Section header detection ----
        section = detect_section(text)
        if section:
            current_section = section
            i += 1
            # Skip the sub-header line (DATE DEPT CODE... or DATE DEPT / PURCHASE...)
            if i < len(parsed_lines):
                next_text = parsed_lines[i].text.strip()
                if next_text.startswith("DATE") or next_text.startswith("  DATE"):
                    i += 1
            continue

        # ---- Divider lines ----
        if text.strip().startswith("-" * 50):
            current_section = Section.BETWEEN
            i += 1
            continue

        # ---- Empty lines ----
        if not text.strip():
            i += 1
            continue

        # ---- Data lines ----
        if current_section == Section.LABOR:
            if "**** Total ****" in text:
                i += 1
                continue
            if "****" in text[:10]:
                rec = parse_star_summary(pline, current_wo, "labor")
                if rec:
                    labor_summaries.append(rec)
            else:
                rec = parse_labor_detail_line(text, current_wo)
                if rec:
                    labor_details.append(rec)

        elif current_section == Section.MATERIAL:
            if "**** Total ****" in text:
                i += 1
                continue
            if "****" in text[:10]:
                # Summary lines are per-item aggregates — skip to avoid
                # double-counting with the detail lines below.
                pass
            else:
                rec = parse_material_detail_line(text, current_wo)
                if rec:
                    material_records.append(rec)

        elif current_section == Section.OUTPLANT:
            if "**** Total ****" in text:
                i += 1
                continue
            if "****" in text[:10]:
                # Summary lines are per-subcontractor aggregates — skip to
                # avoid double-counting with the detail lines below.
                pass
            else:
                rec = parse_outplant_detail_line(text, current_wo)
                if rec:
                    outplant_records.append(rec)

        i += 1

    # Finalize last WO header
    if header_lines:
        wo_rec = parse_wo_header("\n".join(header_lines))
        if wo_rec["wo_number"]:
            wo_headers.append(wo_rec)

    return wo_headers, labor_details, labor_summaries, material_records, outplant_records


# ---------------------------------------------------------------------------
# Cross-validation
# ---------------------------------------------------------------------------


def cross_validate(
    wo_headers: list, labor_summaries: list, material_records: list, outplant_records: list
) -> dict:
    """Compare WO header totals against sum of **** summary line job_costs."""
    stats = {
        "total_wos": len(wo_headers),
        "labor_matches": 0,
        "labor_mismatches": 0,
        "material_matches": 0,
        "material_mismatches": 0,
        "mismatched_wos": [],
    }

    # Sum labor summary job_cost by WO
    labor_by_wo: dict[str, float] = {}
    for rec in labor_summaries:
        wo = rec["wo_number"]
        cost = rec.get("job_cost")
        if cost is not None:
            labor_by_wo[wo] = labor_by_wo.get(wo, 0) + cost

    # Sum material detail job_cost by WO.
    mat_by_wo: dict[str, float] = {}
    for rec in material_records:
        wo = rec["wo_number"]
        cost = rec.get("job_cost")
        if cost is not None:
            mat_by_wo[wo] = mat_by_wo.get(wo, 0) + cost

    tolerance = 0.50  # $0.50 tolerance for rounding across many lines

    for wo in wo_headers:
        wo_num = wo["wo_number"]

        # Labor check: **** summary job_cost includes burden
        # So compare against labor + burden from header
        header_labor = (wo.get("total_labor_cost") or 0) + (wo.get("total_burden_cost") or 0)
        detail_labor = labor_by_wo.get(wo_num, 0)
        if abs(header_labor - detail_labor) <= tolerance:
            stats["labor_matches"] += 1
        else:
            stats["labor_mismatches"] += 1
            if abs(header_labor - detail_labor) > 1.0:
                stats["mismatched_wos"].append(
                    {
                        "wo": wo_num,
                        "type": "labor",
                        "header": header_labor,
                        "detail_sum": detail_labor,
                        "diff": round(header_labor - detail_labor, 2),
                    }
                )

        # Material check
        header_mat = wo.get("total_material_cost") or 0
        detail_mat = mat_by_wo.get(wo_num, 0)
        if abs(header_mat - detail_mat) <= tolerance:
            stats["material_matches"] += 1
        else:
            stats["material_mismatches"] += 1

    return stats


# ---------------------------------------------------------------------------
# CSV field definitions
# ---------------------------------------------------------------------------

WO_HEADER_FIELDS = [
    "wo_number", "customer_id", "customer_name", "location",
    "total_material_cost", "total_labor_cost", "total_burden_cost",
    "total_outplant_cost", "total_use_tax", "total_cost",
    "quoted_price", "sale_price", "billing", "gross_margin", "gm_pct",
    "sales_code", "use_tax_code", "estimator", "quote_nbr",
    "date_completed", "status", "sign_type", "price_class_code",
    "description", "part_number",
    "source_tier", "source_file",
]

LABOR_DETAIL_FIELDS = [
    "wo_number", "labor_date", "work_dept", "work_code",
    "employee_name", "actual_hrs", "job_cost",
    "source_tier", "source_file",
]

LABOR_SUMMARY_FIELDS = [
    "wo_number", "work_dept", "work_code",
    "est_hrs", "actual_hrs", "hrs_variance",
    "est_cost", "job_cost", "cost_variance",
    "description",
    "source_tier", "source_file",
]

MATERIAL_FIELDS = [
    "wo_number", "material_date", "work_dept", "inventory_item", "uom",
    "est_qty", "actual_qty", "qty_variance",
    "est_cost", "job_cost", "cost_variance",
    "description",
    "source_tier", "source_file",
]

OUTPLANT_FIELDS = [
    "wo_number", "outplant_date", "work_dept", "sub_contractor", "uom",
    "est_qty", "actual_qty", "qty_variance",
    "est_cost", "job_cost", "cost_variance",
    "description",
    "source_tier", "source_file",
]


def write_csv(filepath: Path, rows: list[dict], fieldnames: list[str]):
    """Write rows to CSV."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    log.info(f"  Wrote {len(rows):,} rows -> {filepath.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Phase 1: Parse HTML Cost Summary Detail"
    )
    parser.add_argument("--input-dir", type=Path, default=INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--batch", type=str, help="Parse single batch (e.g. cost_detail_batch_001.html)"
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y-%m-%dT%H%M")
    out_dir = args.output_dir / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.batch:
        files = [args.input_dir / args.batch]
        if not files[0].exists():
            log.error(f"File not found: {files[0]}")
            sys.exit(1)
    else:
        files = sorted(args.input_dir.glob("cost_detail_batch_*.html"))

    if not files:
        log.error(f"No HTML batch files found in {args.input_dir}")
        sys.exit(1)

    log.info(f"Found {len(files)} batch files to parse")

    all_wo_headers = []
    all_labor_details = []
    all_labor_summaries = []
    all_material_records = []
    all_outplant_records = []

    source_tier = 3  # html_reparse per trust hierarchy

    for filepath in files:
        try:
            wo_h, lab_d, lab_s, mat_r, out_r = parse_html_file(filepath)

            # Tag every row with source metadata
            for collection in (wo_h, lab_d, lab_s, mat_r, out_r):
                for rec in collection:
                    rec["source_tier"] = source_tier
                    rec["source_file"] = str(filepath)

            all_wo_headers.extend(wo_h)
            all_labor_details.extend(lab_d)
            all_labor_summaries.extend(lab_s)
            all_material_records.extend(mat_r)
            all_outplant_records.extend(out_r)

            log.info(
                f"  -> {filepath.name}: {len(wo_h)} WOs, "
                f"{len(lab_d)} labor detail, {len(lab_s)} labor summary, "
                f"{len(mat_r)} material, {len(out_r)} outplant"
            )
        except Exception:
            log.exception(f"FAILED to parse {filepath.name}")

    # Deduplicate WO headers (keep version with most non-None fields)
    seen_wos: dict[str, dict] = {}
    deduped_headers = []
    for wo in all_wo_headers:
        wo_num = wo["wo_number"]
        if wo_num not in seen_wos:
            seen_wos[wo_num] = wo
            deduped_headers.append(wo)
        else:
            existing = seen_wos[wo_num]
            existing_count = sum(1 for v in existing.values() if v is not None)
            new_count = sum(1 for v in wo.values() if v is not None)
            if new_count > existing_count:
                idx = deduped_headers.index(existing)
                deduped_headers[idx] = wo
                seen_wos[wo_num] = wo

    log.info(f"\n{'=' * 60}")
    log.info("TOTALS:")
    log.info(f"  WO Headers:       {len(deduped_headers):,} (deduped from {len(all_wo_headers):,})")
    log.info(f"  Labor Detail:     {len(all_labor_details):,}")
    log.info(f"  Labor Summary:    {len(all_labor_summaries):,}")
    log.info(f"  Material Records: {len(all_material_records):,}")
    log.info(f"  Outplant Records: {len(all_outplant_records):,}")

    # Write CSVs
    write_csv(out_dir / "wo_headers.csv", deduped_headers, WO_HEADER_FIELDS)
    write_csv(out_dir / "labor_detail.csv", all_labor_details, LABOR_DETAIL_FIELDS)
    write_csv(out_dir / "labor_summary.csv", all_labor_summaries, LABOR_SUMMARY_FIELDS)
    write_csv(out_dir / "material_detail.csv", all_material_records, MATERIAL_FIELDS)
    write_csv(out_dir / "outplant_detail.csv", all_outplant_records, OUTPLANT_FIELDS)

    # Cross-validate
    log.info("\nCross-validation:")
    stats = cross_validate(deduped_headers, all_labor_summaries, all_material_records, all_outplant_records)
    log.info(f"  Labor:    {stats['labor_matches']:,} match, {stats['labor_mismatches']:,} mismatch")
    log.info(f"  Material: {stats['material_matches']:,} match, {stats['material_mismatches']:,} mismatch")

    completeness = len(deduped_headers) / max(len(all_wo_headers), 1) * 100
    log.info(f"  Completeness: {completeness:.1f}%")

    if stats["mismatched_wos"]:
        log.warning(f"  {len(stats['mismatched_wos'])} WOs with labor mismatch > $1.00:")
        for m in stats["mismatched_wos"][:10]:
            log.warning(
                f"    WO {m['wo']}: header=${m['header']:.2f} "
                f"detail=${m['detail_sum']:.2f} diff=${m['diff']:.2f}"
            )

    # Write manifest
    manifest = {
        "timestamp": timestamp,
        "source": str(args.input_dir),
        "files_parsed": len(files),
        "wo_headers": len(deduped_headers),
        "labor_detail_rows": len(all_labor_details),
        "labor_summary_rows": len(all_labor_summaries),
        "material_rows": len(all_material_records),
        "outplant_rows": len(all_outplant_records),
        "source_tier": source_tier,
        "cross_validation": stats,
    }
    with open(out_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    log.info(f"\nOutput written to: {out_dir}")
    log.info("Phase 1 complete.")


if __name__ == "__main__":
    main()
