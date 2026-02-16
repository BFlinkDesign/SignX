"""Bulk extract all SO.CONTRACT reports from KeyedIn MVI and parse into structured CSVs.

Phase 1: Download all SO.CONTRACT report texts from REPORT.IFRAME
Phase 2: Parse fixed-width text into 4 structured CSV files
"""

import csv
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ENV_FILE = Path(r"C:\Scripts\keyedin-capture\.env")
RAW_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\so_contract_raw")
CSV_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\raw")
SAMPLES_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\spooled_samples")

ERP_BASE = "https://eaglesign.keyedinsign.com"
MVI_BASE = f"{ERP_BASE}/cgi-bin/mvi.exe"

load_dotenv(ENV_FILE)
USERNAME = os.environ.get("KEYEDIN_USERNAME", "")
PASSWORD = os.environ.get("KEYEDIN_PASSWORD", "")


# ---------------------------------------------------------------------------
# Network functions (reused from extract_spooled_reports.py)
# ---------------------------------------------------------------------------
def create_session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.headers.update(
        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"}
    )
    print("[1] Getting initial session cookies...")
    s.get(f"{ERP_BASE}/", allow_redirects=True, timeout=30)
    print(f"[2] Logging in as {USERNAME}...")
    resp = s.post(
        f"{MVI_BASE}/LOGIN.START",
        data={"USERNAME": USERNAME, "PASSWORD": PASSWORD, "btnLogin": "Login"},
        allow_redirects=True,
        timeout=30,
    )
    if "DASHBOARD" in resp.text.upper() or resp.status_code == 200:
        print("    Login successful!")
    else:
        print("    WARNING: Login may have failed")
    s.cookies.set("user", USERNAME.upper(), domain="eaglesign.keyedinsign.com")
    s.cookies.set("secure", "FALSE", domain="eaglesign.keyedinsign.com")
    return s


def fetch_report_index(session, history="7"):
    url = f"{MVI_BASE}/REPORT.VIEW.INDEX?REPORT_HISTORY={history}"
    print(f"\n[*] Fetching REPORT.VIEW.INDEX?REPORT_HISTORY={history}...")
    resp = session.get(url, timeout=60)
    print(f"    Status: {resp.status_code}, Size: {len(resp.text)} bytes")
    return resp.text


def parse_report_listings(html):
    entries = []
    pattern = re.compile(
        r"openReport\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"](\d+)['\"]\s*,"
        r"\s*['\"](\d+)['\"]\s*,\s*['\"]([^'\"]*)['\"]"
    )
    for m in pattern.finditer(html):
        report_id, start, end, location = m.groups()
        entries.append(
            {
                "report_id": report_id,
                "start_line": int(start),
                "end_line": int(end),
                "location": location,
            }
        )
    return entries


def classify_report(report_id):
    parts = report_id.split("*")
    if len(parts) >= 2:
        return parts[1].split(":")[0]
    return "UNKNOWN"


def fetch_report_content(session, report_id, start_line=1, end_line=999999):
    url = (
        f"{MVI_BASE}/REPORT.IFRAME"
        f"?REPORT_ID={report_id}&START_LINE={start_line}&END_LINE={end_line}"
    )
    resp = session.get(url, timeout=120)
    return resp.text


def extract_text_from_iframe(html):
    pre_blocks = re.findall(
        r"<pre[^>]*>(.*?)</pre>", html, re.DOTALL | re.IGNORECASE
    )
    if pre_blocks:
        pages = []
        for block in pre_blocks:
            text = re.sub(r"<[^>]+>", "", block)
            pages.append(text.strip())
        return "\n\n".join(pages)
    text = re.sub(r"<[^>]+>", "\n", html)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Phase 1: Bulk Download
# ---------------------------------------------------------------------------
def download_all_so_contracts(session, entries):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    so_entries = [e for e in entries if classify_report(e["report_id"]) == "SO.CONTRACT"]
    total = len(so_entries)
    print(f"\n{'='*60}")
    print(f"[DOWNLOAD] {total} SO.CONTRACT entries to download")
    print(f"[DOWNLOAD] Output: {RAW_DIR}")
    print(f"{'='*60}")

    downloaded = skipped = errors = 0

    for i, entry in enumerate(so_entries, 1):
        report_id = entry["report_id"]
        safe_name = (
            report_id.replace("*", "_").replace(":", "_")
            .replace("/", "_").replace("\t", "_TAB_")
        )
        txt_path = RAW_DIR / f"{safe_name}.txt"

        if txt_path.exists() and txt_path.stat().st_size > 0:
            skipped += 1
            continue

        try:
            html = fetch_report_content(
                session, report_id, entry["start_line"], entry["end_line"]
            )
            text = extract_text_from_iframe(html)
            txt_path.write_text(text, encoding="utf-8")
            downloaded += 1
        except Exception as e:
            print(f"    ERROR [{i}/{total}]: {report_id} - {e}")
            errors += 1

        if i % 50 == 0 or i == total:
            print(
                f"    [{i}/{total}] downloaded={downloaded}"
                f" skipped={skipped} errors={errors}"
            )

        time.sleep(0.2)

    print(
        f"\n[DOWNLOAD] Done: {downloaded} new, {skipped} skipped, {errors} errors"
    )
    return so_entries


# ---------------------------------------------------------------------------
# Phase 2: Parser helpers
# ---------------------------------------------------------------------------
def strip_page_breaks(text: str) -> str:
    """Remove page-break headers that repeat mid-report."""
    lines = text.split("\n")
    clean: list[str] = []
    first_run_date = True

    i = 0
    while i < len(lines):
        line = lines[i]

        if re.match(r"\s*RUN DATE:", line):
            if first_run_date:
                clean.append(line)
                first_run_date = False
                i += 1
                continue

            # Skip page break block: RUN DATE, blank, COST SUMMARY, underscores,
            # blank, and any repeated section-header lines
            j = i + 1
            while j < len(lines):
                s = lines[j].strip()
                if (
                    not s
                    or "COST  SUMMARY" in lines[j]
                    or re.match(r"^_+$", s)
                    or re.match(r"\s*(LABOR|MATERIAL|OUTPLANT)\s+WORK", lines[j])
                    or re.match(r"\s*DATE\s+DEPT", lines[j])
                ):
                    j += 1
                else:
                    break
            i = j
            continue

        clean.append(line)
        i += 1

    return "\n".join(clean)


def extract_run_date(text: str) -> str:
    m = re.search(r"RUN DATE:\s*(\d{2}/\d{2}/\d{4})", text)
    return m.group(1) if m else ""


def parse_money(s: str) -> float:
    if not s or not s.strip():
        return 0.0
    s = s.strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_numbers(s: str) -> list[float]:
    """Extract all numbers from a string, stripping 'I' invoice flags."""
    s = re.sub(r"\bI\b", "", s)
    nums = re.findall(r"-?[\d,]+\.?\d*", s)
    result = []
    for n in nums:
        n = n.replace(",", "")
        try:
            result.append(float(n))
        except ValueError:
            pass
    return result


def extract_description(line: str) -> tuple[str, int]:
    """Extract description from the right end of a **** line.

    Walks right-to-left to find where the description starts: the position
    of a non-space character preceded by 2+ spaces.  Returns (description, start_pos).
    Descriptions that are purely numeric (like a trailing cost value) are rejected.
    """
    stripped = line.rstrip()
    if len(stripped) < 50:
        return "", len(stripped)

    for i in range(len(stripped) - 1, 1, -1):
        if stripped[i] != " " and stripped[i - 1] == " " and stripped[i - 2] == " ":
            desc = stripped[i:]
            if re.search(r"[A-Za-z]", desc):
                return desc, i
            break

    return "", len(stripped)


# ---------------------------------------------------------------------------
# Phase 2: WO header parser
# ---------------------------------------------------------------------------
def parse_wo_header(text: str) -> dict:
    result: dict = {}

    m = re.search(r"WORK ORDER\s+([\w.]+)", text)
    if m:
        result["wo_number"] = m.group(1)

    m = re.search(
        r"Customer:\s+(\S+)\s+(.+?)(?:\s{2,}Location:\s*(.+)|$)", text, re.MULTILINE
    )
    if m:
        result["customer_id"] = m.group(1).strip()
        result["customer_name"] = m.group(2).strip()
        result["location"] = (m.group(3) or "").strip()

    fin = {
        "total_material_cost": r"TOTAL MATERIAL COST\s+([\d,.]+)",
        "total_labor_cost": r"TOTAL LABOR COST\s+([\d,.]+)",
        "total_burden_cost": r"TOTAL BURDEN COST\s+([\d,.]+)",
        "total_outplant_cost": r"TOTAL OUTPLANT COST\s+([\d,.]+)",
        "total_use_tax": r"TOTAL USE TAX\s+([\d,.]+)",
        "total_cost": r"TOTAL COST\s+([\d,.]+)",
        "quoted_price": r"QUOTED PRICE\s+([\d,.]+)",
        "billing": r"BILLING\s+([\d,.]+)",
        "gross_margin": r"GROSS MARGIN\s+(-?[\d,.]+)",
        "gm_pct": r"GM\s*%\s*=\s+([\d,.]+)",
    }
    for key, pat in fin.items():
        m = re.search(pat, text)
        result[key] = parse_money(m.group(1)) if m else 0.0

    meta = {
        "quote_nbr": r"Quote Nbr\s*:\s*(\S+)",
        "date_completed": r"Date Compl:\s*(\S+)",
        "status": r"Status\s*:\s*(.+?)(?:\s{2,}|$)",
        "sales_code": r"Sales Code:\s*(\S+)",
        "estimator": r"Estimator\s*:\s*(.+?)(?:\s{2,}|$)",
        "price_class_code": r"Price Class Code:\s*(.+?)$",
        "use_tax_code": r"Use Tax\s*:\s*(\S+)",
    }
    for key, pat in meta.items():
        m = re.search(pat, text, re.MULTILINE)
        result[key] = m.group(1).strip() if m else ""

    m = re.search(r"Sign Type:\s*(\S+)", text)
    result["sign_type"] = m.group(1) if m else ""

    m = re.search(
        r"DESCRIPTION\s*-+\s*\n\n(.+?)(?:\n-{10,}|\nWORK ORDER|\Z)",
        text,
        re.DOTALL,
    )
    if m:
        desc_lines = [l.strip() for l in m.group(1).strip().split("\n") if l.strip()]
        result["description"] = " ".join(desc_lines)
    else:
        result["description"] = ""

    return result


# ---------------------------------------------------------------------------
# Phase 2: Subtotal line parsers
# ---------------------------------------------------------------------------
def parse_labor_subtotal(line: str) -> dict | None:
    """Parse a labor **** subtotal line using regex."""
    if "**** Total ****" in line:
        return None
    if "****" not in line:
        return None

    m = re.match(r"\s*\*{4}\s+(\d{4})\s+(\S+)", line)
    if not m:
        return None

    dept = m.group(1)
    code = m.group(2)

    description, desc_pos = extract_description(line)
    num_portion = line[m.end() : desc_pos]
    nums = parse_numbers(num_portion)

    result = {"work_dept": dept, "work_code": code, "description": description}

    if len(nums) >= 6:
        result.update(
            {
                "est_hours": nums[0],
                "actual_hours": nums[1],
                "variance_hours": nums[2],
                "est_cost": nums[3],
                "job_cost": nums[4],
                "cost_variance": nums[5],
            }
        )
    elif len(nums) >= 4:
        result.update(
            {
                "est_hours": 0.0,
                "actual_hours": nums[0],
                "variance_hours": nums[1],
                "est_cost": 0.0,
                "job_cost": nums[2],
                "cost_variance": nums[3],
            }
        )
    else:
        result.update(
            {
                "est_hours": 0.0,
                "actual_hours": 0.0,
                "variance_hours": 0.0,
                "est_cost": 0.0,
                "job_cost": nums[0] if len(nums) >= 1 else 0.0,
                "cost_variance": nums[1] if len(nums) >= 2 else 0.0,
            }
        )

    return result


def parse_mat_or_outplant_subtotal(line: str) -> dict | None:
    """Parse a material or outplant **** subtotal line.

    Returns dict with: work_dept, identifier, unit_of_measure, numbers, description.
    """
    if "**** Total ****" in line:
        return None
    if "****" not in line:
        return None

    description, desc_pos = extract_description(line)

    # After ****, optionally a 4-digit dept, then identifier, then U/M, then numbers
    m = re.match(r"\s*\*{4}\s+(?:(\d{4})\s+)?(\S+.*?)\s{2,}(\S{1,6})\s+", line)
    if not m:
        m2 = re.match(r"\s*\*{4}\s+(?:(\d{4})\s+)?(\S+)", line)
        if not m2:
            return None
        dept = m2.group(1) or ""
        identifier = m2.group(2)
        uom = ""
        num_start = m2.end()
    else:
        dept = m.group(1) or ""
        identifier = m.group(2).strip()
        uom = m.group(3)
        num_start = m.end()

    num_portion = line[num_start:desc_pos]
    nums = parse_numbers(num_portion)

    result = {
        "work_dept": dept,
        "identifier": identifier,
        "unit_of_measure": uom,
        "description": description,
    }

    if len(nums) >= 6:
        result.update(
            {
                "est_qty": nums[0],
                "actual_qty": nums[1],
                "variance_qty": nums[2],
                "est_cost": nums[3],
                "job_cost": nums[4],
                "cost_variance": nums[5],
            }
        )
    elif len(nums) >= 4:
        result.update(
            {
                "est_qty": 0.0,
                "actual_qty": nums[0],
                "variance_qty": nums[1],
                "est_cost": 0.0,
                "job_cost": nums[2],
                "cost_variance": nums[3],
            }
        )
    else:
        result.update(
            {
                "est_qty": 0.0,
                "actual_qty": 0.0,
                "variance_qty": 0.0,
                "est_cost": 0.0,
                "job_cost": nums[0] if len(nums) >= 1 else 0.0,
                "cost_variance": nums[1] if len(nums) >= 2 else 0.0,
            }
        )

    return result


# ---------------------------------------------------------------------------
# Phase 2: Full report parser
# ---------------------------------------------------------------------------
def parse_so_contract_text(text: str, report_id: str = "") -> dict:
    run_date = extract_run_date(text)
    clean = strip_page_breaks(text)

    # Split into WO blocks at "WORK ORDER" markers
    wo_pattern = re.compile(r"-{5,}\s*WORK ORDER\s+([\w.]+)\s*-{5,}")
    wo_matches = list(wo_pattern.finditer(clean))

    work_orders = []

    for idx, match in enumerate(wo_matches):
        wo_number = match.group(1)
        start = match.start()
        end = wo_matches[idx + 1].start() if idx + 1 < len(wo_matches) else len(clean)
        wo_text = clean[start:end]

        if "HAS NO HISTORY" in wo_text:
            header = parse_wo_header(wo_text)
            header.setdefault("wo_number", wo_number)
            work_orders.append(
                {"header": header, "labor": [], "material": [], "outplant": []}
            )
            continue

        # Parse header (text before first section divider)
        section_start = re.search(r"\n-{10,}\n", wo_text)
        header_text = wo_text[: section_start.start()] if section_start else wo_text
        header = parse_wo_header(header_text)
        header.setdefault("wo_number", wo_number)

        labor_rows: list[dict] = []
        material_rows: list[dict] = []
        outplant_rows: list[dict] = []

        current_section = None

        for line in wo_text.split("\n"):
            if re.match(r"\s*LABOR\s+WORK\s+WORK", line):
                current_section = "LABOR"
                continue
            elif re.match(r"\s*MATERIAL\s+WORK\s+INVENTORY", line):
                current_section = "MATERIAL"
                continue
            elif re.match(r"\s*OUTPLANT\s+WORK", line):
                current_section = "OUTPLANT"
                continue

            if "****" not in line:
                continue
            if "**** Total ****" in line:
                continue

            if current_section == "LABOR":
                row = parse_labor_subtotal(line)
                if row:
                    labor_rows.append(row)
            elif current_section == "MATERIAL":
                row = parse_mat_or_outplant_subtotal(line)
                if row:
                    row["item_number"] = row.pop("identifier", "")
                    material_rows.append(row)
            elif current_section == "OUTPLANT":
                row = parse_mat_or_outplant_subtotal(line)
                if row:
                    row["subcontractor"] = row.pop("identifier", "")
                    outplant_rows.append(row)

        work_orders.append(
            {
                "header": header,
                "labor": labor_rows,
                "material": material_rows,
                "outplant": outplant_rows,
            }
        )

    return {"report_id": report_id, "run_date": run_date, "work_orders": work_orders}


# ---------------------------------------------------------------------------
# Phase 3: CSV output
# ---------------------------------------------------------------------------
WO_SUMMARY_FIELDS = [
    "run_date", "report_id", "wo_number", "customer_id", "customer_name",
    "location", "total_material_cost", "total_labor_cost", "total_burden_cost",
    "total_outplant_cost", "total_use_tax", "total_cost", "quoted_price",
    "billing", "gross_margin", "gm_pct", "quote_nbr", "date_completed",
    "status", "sales_code", "use_tax_code", "estimator",
    "price_class_code", "sign_type", "description",
]

LABOR_FIELDS = [
    "run_date", "report_id", "wo_number", "work_dept", "work_code",
    "est_hours", "actual_hours", "variance_hours",
    "est_cost", "job_cost", "cost_variance", "description",
]

MATERIAL_FIELDS = [
    "run_date", "report_id", "wo_number", "work_dept", "item_number",
    "unit_of_measure", "est_qty", "actual_qty", "variance_qty",
    "est_cost", "job_cost", "cost_variance", "description",
]

OUTPLANT_FIELDS = [
    "run_date", "report_id", "wo_number", "work_dept", "subcontractor",
    "unit_of_measure", "est_qty", "actual_qty", "variance_qty",
    "est_cost", "job_cost", "cost_variance", "description",
]


def write_csv(filename, fields, rows):
    path = CSV_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"    Wrote {path.name}: {len(rows)} rows")


def process_all_reports(source_dir: Path | None = None):
    """Parse all downloaded SO.CONTRACT texts and write CSVs."""
    src = source_dir or RAW_DIR
    txt_files = sorted(src.glob("*.txt"))
    if not txt_files:
        print(f"[PARSE] No .txt files found in {src}")
        return

    print(f"\n{'='*60}")
    print(f"[PARSE] Processing {len(txt_files)} report files from {src}")
    print(f"{'='*60}")

    wo_summaries: list[dict] = []
    labor_all: list[dict] = []
    material_all: list[dict] = []
    outplant_all: list[dict] = []
    parse_errors: list[tuple] = []

    for i, filepath in enumerate(txt_files, 1):
        try:
            try:
                text = filepath.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = filepath.read_text(encoding="cp1252")
            report_id = filepath.stem
            result = parse_so_contract_text(text, report_id)

            for wo in result["work_orders"]:
                h = wo["header"]
                wo_number = h.get("wo_number", "")

                summary: dict = {"run_date": result["run_date"], "report_id": report_id}
                for field in WO_SUMMARY_FIELDS:
                    if field not in summary:
                        summary[field] = h.get(field, "")
                wo_summaries.append(summary)

                for row in wo["labor"]:
                    row["run_date"] = result["run_date"]
                    row["report_id"] = report_id
                    row["wo_number"] = wo_number
                    labor_all.append(row)

                for row in wo["material"]:
                    row["run_date"] = result["run_date"]
                    row["report_id"] = report_id
                    row["wo_number"] = wo_number
                    material_all.append(row)

                for row in wo["outplant"]:
                    row["run_date"] = result["run_date"]
                    row["report_id"] = report_id
                    row["wo_number"] = wo_number
                    outplant_all.append(row)

        except Exception as e:
            parse_errors.append((filepath.name, str(e)))

        if i % 100 == 0 or i == len(txt_files):
            print(
                f"    [{i}/{len(txt_files)}] WOs={len(wo_summaries)}"
                f" labor={len(labor_all)} material={len(material_all)}"
                f" outplant={len(outplant_all)}"
            )

    print(f"\n[CSV] Writing output files to {CSV_DIR}")
    write_csv("so_contract_wo_summary.csv", WO_SUMMARY_FIELDS, wo_summaries)
    write_csv("so_contract_labor.csv", LABOR_FIELDS, labor_all)
    write_csv("so_contract_material.csv", MATERIAL_FIELDS, material_all)
    write_csv("so_contract_outplant.csv", OUTPLANT_FIELDS, outplant_all)

    if parse_errors:
        print(f"\n[ERRORS] {len(parse_errors)} files had parse errors:")
        for name, err in parse_errors[:20]:
            print(f"    {name}: {err}")

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Files processed:  {len(txt_files)}")
    print(f"  Parse errors:     {len(parse_errors)}")
    print(f"  WO summaries:     {len(wo_summaries)}")
    print(f"  Labor rows:       {len(labor_all)}")
    print(f"  Material rows:    {len(material_all)}")
    print(f"  Outplant rows:    {len(outplant_all)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    if not USERNAME or not PASSWORD:
        print(f"ERROR: Set KEYEDIN_USERNAME and KEYEDIN_PASSWORD in {ENV_FILE}")
        sys.exit(1)

    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode in ("all", "download"):
        session = create_session()
        html = fetch_report_index(session, "7")
        entries = parse_report_listings(html)
        print(f"    Parsed {len(entries)} total report entries")
        download_all_so_contracts(session, entries)

    if mode in ("all", "parse"):
        process_all_reports()

    if mode == "test":
        # Parse just the existing samples for validation
        print("[TEST] Parsing samples from", SAMPLES_DIR)
        so_files = sorted(SAMPLES_DIR.glob("so_contract_*.txt"))
        for f in so_files:
            print(f"\n--- {f.name} ---")
            try:
                text = f.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = f.read_text(encoding="cp1252")
            result = parse_so_contract_text(text, f.stem)
            print(f"  run_date: {result['run_date']}")
            print(f"  work_orders: {len(result['work_orders'])}")
            for wo in result["work_orders"]:
                h = wo["header"]
                print(f"    WO {h.get('wo_number', '?')}:")
                print(f"      customer: {h.get('customer_id', '')} {h.get('customer_name', '')}")
                print(f"      total_cost: {h.get('total_cost', 0)}")
                print(f"      labor subtotals: {len(wo['labor'])}")
                print(f"      material subtotals: {len(wo['material'])}")
                print(f"      outplant subtotals: {len(wo['outplant'])}")
                if wo["labor"]:
                    r = wo["labor"][0]
                    print(f"        first labor: {r['work_dept']}/{r['work_code']}"
                          f" est={r.get('est_hours',0)} act={r.get('actual_hours',0)}"
                          f" job_cost={r.get('job_cost',0)} desc={r.get('description','')}")


if __name__ == "__main__":
    main()
