"""Split raw_captures.json into individual payload files for scrape_informer.py.

Usage:
    python split_captures.py                          # default path
    python split_captures.py path/to/raw_captures.json
    python split_captures.py --dry-run                # preview without writing

Reads the JSON array produced by capture_hook.js and writes individual files:
    report_{slug}_view_request.txt   — ViewRPCService request payload
    report_{slug}_view_response.txt  — ViewRPCService response body
    report_{slug}_cmd_request.txt    — commandService request payload
    report_{slug}_cmd_response.txt   — commandService response body

Files are written to C:\\Scripts\\keyedin-capture\\reports\\ matching the
naming convention expected by scrape_informer.py load_captured_payload().
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Report ID → name mapping (must match capture_all_reports.py REPORTS list)
# ---------------------------------------------------------------------------

REPORTS = [
    {"id": 1441842, "name": "AR Invoice Details"},
    {"id": 1441843, "name": "AR Invoice Listing"},
    {"id": 1441844, "name": "AR Open Invoices"},
    {"id": 1441849, "name": "Cash Receipts"},
    {"id": 1441850, "name": "Customer Listing"},
    {"id": 1441851, "name": "Customer Listing Export"},
    {"id": 1441852, "name": "Customer Location Listing"},
    {"id": 1441853, "name": "Customer Location Listing Export"},
    {"id": 1441854, "name": "Inventory List"},
    {"id": 1441855, "name": "Inventory List Export"},
    {"id": 1441856, "name": "Inventory Transaction History"},
    {"id": 1441857, "name": "Invoice Register"},
    {"id": 1441859, "name": "Open Sales Order Backlog"},
    {"id": 1441860, "name": "Open Sales Orders"},
    {"id": 1441861, "name": "Open Work Orders"},
    {"id": 1441862, "name": "Planned Part Activity"},
    {"id": 1441865, "name": "Purchase History"},
    {"id": 1441866, "name": "Purchase Order Detail"},
    {"id": 1441868, "name": "Purchased Part Variance"},
    {"id": 1441869, "name": "Quote Status Report"},
    {"id": 1441870, "name": "Sales Cost Detail Report"},
    {"id": 1441872, "name": "Sales Order Bookings By Line Date"},
    {"id": 1441873, "name": "Sales Order Bookings By SO Date"},
    {"id": 1441874, "name": "Sales Order Detail"},
    {"id": 1441875, "name": "Sales Order Status by Customer"},
    {"id": 1441877, "name": "Sales Summary by Customer"},
    {"id": 1441878, "name": "Sales Summary by Product Type"},
    {"id": 1441883, "name": "Vendor Listing"},
    {"id": 1441884, "name": "Vendor Listing Export"},
    {"id": 1441887, "name": "Work Order Listing"},
]

REPORT_BY_ID = {r["id"]: r["name"] for r in REPORTS}

OUTPUT_DIR = Path(r"C:\Scripts\keyedin-capture\reports")
DEFAULT_INPUT = OUTPUT_DIR / "raw_captures.json"


def make_slug(name: str) -> str:
    """Convert report name to filename slug (matches scrape_informer.py)."""
    return re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "_").lower()


def split(input_path: Path, dry_run: bool = False) -> None:
    """Read raw_captures.json and write individual payload files."""
    print(f"Reading: {input_path}")
    data = json.loads(input_path.read_text(encoding="utf-8"))
    print(f"Found {len(data)} captured RPC calls\n")

    # Group captures by (reportId, endpoint), keeping the best one
    # "Best" = largest request payload (most likely the real report execution)
    best: dict[tuple[int, str], dict] = {}
    skipped = 0

    for entry in data:
        report_id = entry.get("reportId")
        endpoint = entry.get("endpoint")  # "view" or "command"
        payload = entry.get("requestPayload", "")

        if not report_id or not endpoint or not payload:
            skipped += 1
            continue

        key = (report_id, endpoint)
        existing = best.get(key)
        if not existing or len(payload) > len(existing.get("requestPayload", "")):
            best[key] = entry

    if skipped:
        print(f"Skipped {skipped} entries (missing reportId/endpoint/payload)\n")

    # Write files
    written = 0
    reports_seen = set()

    for (report_id, endpoint), entry in sorted(best.items()):
        name = REPORT_BY_ID.get(report_id)
        if not name:
            print(f"  WARN: Unknown reportId={report_id} — skipping")
            continue

        slug = make_slug(name)
        reports_seen.add(report_id)

        # Request payload
        req_payload = entry.get("requestPayload", "")
        if req_payload:
            suffix = "view_request" if endpoint == "view" else "cmd_request"
            req_file = OUTPUT_DIR / f"report_{slug}_{suffix}.txt"
            if dry_run:
                print(f"  [DRY] Would write {req_file.name} ({len(req_payload):,} bytes)")
            else:
                req_file.write_text(req_payload, encoding="utf-8")
                print(f"  WROTE {req_file.name} ({len(req_payload):,} bytes)")
            written += 1

        # Response body
        resp_text = entry.get("responseText", "")
        if resp_text:
            suffix = "view_response" if endpoint == "view" else "cmd_response"
            resp_file = OUTPUT_DIR / f"report_{slug}_{suffix}.txt"
            if dry_run:
                print(f"  [DRY] Would write {resp_file.name} ({len(resp_text):,} bytes)")
            else:
                resp_file.write_text(resp_text, encoding="utf-8")
                print(f"  WROTE {resp_file.name} ({len(resp_text):,} bytes)")
            written += 1

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Reports captured: {len(reports_seen)} / {len(REPORTS)}")
    print(f"Files {'would be ' if dry_run else ''}written: {written}")

    missing = set(REPORT_BY_ID.keys()) - reports_seen
    if missing:
        print(f"\nMissing reports ({len(missing)}):")
        for rid in sorted(missing):
            print(f"  - {REPORT_BY_ID[rid]} (id={rid})")


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    input_path = Path(args[0]) if args else DEFAULT_INPUT

    if not input_path.exists():
        print(f"ERROR: {input_path} not found")
        print(f"\nExpected workflow:")
        print(f"  1. Paste capture_hook.js into Chrome DevTools console")
        print(f"  2. Click through all 30 Informer reports")
        print(f"  3. Run _captureDownload() in console")
        print(f"  4. Save raw_captures.json to {OUTPUT_DIR}")
        print(f"  5. Run: python split_captures.py")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    split(input_path, dry_run=dry_run)


if __name__ == "__main__":
    main()
