"""
Extract spooled reports from KeyedIn MVI REPORT.IFRAME endpoint.

Proves the extraction pipeline for SO.CONTRACT and other report types.
Authenticates via LOGIN.START, then fetches REPORT.VIEW.INDEX for listings
and REPORT.IFRAME for actual report content.
"""

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
OUTPUT_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\spooled_samples")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ERP_BASE = "https://eaglesign.keyedinsign.com"
MVI_BASE = f"{ERP_BASE}/cgi-bin/mvi.exe"

load_dotenv(ENV_FILE)
USERNAME = os.environ.get("KEYEDIN_USERNAME", "")
PASSWORD = os.environ.get("KEYEDIN_PASSWORD", "")


def create_session() -> requests.Session:
    """Create authenticated MVI session."""
    s = requests.Session()
    s.verify = False
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
        }
    )

    # Step 1: Hit root to get initial cookies (ASP.NET_SessionId, SESSIONID)
    print("[1] Getting initial session cookies...")
    resp = s.get(f"{ERP_BASE}/", allow_redirects=True, timeout=30)
    print(f"    Cookies: {list(s.cookies.keys())}")

    # Step 2: POST login
    print("[2] Logging in as", USERNAME, "...")
    resp = s.post(
        f"{MVI_BASE}/LOGIN.START",
        data={"USERNAME": USERNAME, "PASSWORD": PASSWORD, "btnLogin": "Login"},
        allow_redirects=True,
        timeout=30,
    )
    print(f"    Status: {resp.status_code}, URL: {resp.url[:80]}")

    if "DASHBOARD" in resp.text.upper() or resp.status_code == 200:
        print("    Login successful!")
    else:
        print("    WARNING: Login may have failed")

    # Set additional cookies that MVI expects
    s.cookies.set("user", USERNAME.upper(), domain="eaglesign.keyedinsign.com")
    s.cookies.set("secure", "FALSE", domain="eaglesign.keyedinsign.com")

    return s


def fetch_report_index(session: requests.Session, history: str = "7") -> str:
    """Fetch REPORT.VIEW.INDEX with specified history range."""
    url = f"{MVI_BASE}/REPORT.VIEW.INDEX?REPORT_HISTORY={history}"
    print(f"\n[*] Fetching REPORT.VIEW.INDEX?REPORT_HISTORY={history} ...")
    resp = session.get(url, timeout=60)
    print(f"    Status: {resp.status_code}, Size: {len(resp.text)} bytes")
    return resp.text


def parse_report_listings(html: str) -> list[dict]:
    """Parse report entries from REPORT.VIEW.INDEX HTML.

    The HTML contains JavaScript calls like:
      openReport('USER*TYPE:DETAIL*DATE*TIME', startLine, endLine, 'location')
    or anchor tags with similar patterns.
    """
    entries = []

    # Pattern 1: openReport('ID', 'start', 'end', 'loc') — all args are quoted strings
    pattern1 = re.compile(
        r"openReport\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"](\d+)['\"]\s*,\s*['\"](\d+)['\"]\s*,\s*['\"]([^'\"]*)['\"]"
    )
    for m in pattern1.finditer(html):
        report_id, start, end, location = m.groups()
        entries.append(
            {
                "report_id": report_id,
                "start_line": int(start),
                "end_line": int(end),
                "location": location,
            }
        )

    # Pattern 2: href containing REPORT_ID= (fallback)
    if not entries:
        pattern2 = re.compile(
            r'REPORT_ID=([^&"\']+).*?START_LINE=(\d+).*?END_LINE=(\d+)',
            re.IGNORECASE,
        )
        for m in pattern2.finditer(html):
            report_id, start, end = m.groups()
            entries.append(
                {
                    "report_id": report_id,
                    "start_line": int(start),
                    "end_line": int(end),
                    "location": "",
                }
            )

    return entries


def classify_report(report_id: str) -> str:
    """Extract report type from ID like 'USER*TYPE:DETAIL*DATE*TIME'."""
    parts = report_id.split("*")
    if len(parts) >= 2:
        type_part = parts[1]
        # Strip the detail suffix after colon
        return type_part.split(":")[0]
    return "UNKNOWN"


def fetch_report_content(
    session: requests.Session,
    report_id: str,
    start_line: int = 1,
    end_line: int = 999999,
) -> str:
    """Fetch actual report content from REPORT.IFRAME."""
    url = (
        f"{MVI_BASE}/REPORT.IFRAME"
        f"?REPORT_ID={report_id}"
        f"&START_LINE={start_line}"
        f"&END_LINE={end_line}"
    )
    resp = session.get(url, timeout=60)
    return resp.text


def extract_text_from_iframe(html: str) -> str:
    """Extract plain text from REPORT.IFRAME HTML.

    Reports have one <pre> block per page (can be 235+ pages).
    Concatenate all <pre> blocks with page breaks.
    """
    pre_blocks = re.findall(
        r"<pre[^>]*>(.*?)</pre>", html, re.DOTALL | re.IGNORECASE
    )
    if pre_blocks:
        pages = []
        for block in pre_blocks:
            # Strip HTML tags within pre (spans for bold, etc.)
            text = re.sub(r"<[^>]+>", "", block)
            pages.append(text.strip())
        return "\n\n".join(pages)

    # Fallback: strip all HTML tags
    text = re.sub(r"<[^>]+>", "\n", html)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    # Suppress SSL warnings
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    if not USERNAME or not PASSWORD:
        print(f"ERROR: Set KEYEDIN_USERNAME and KEYEDIN_PASSWORD in {ENV_FILE}")
        sys.exit(1)

    session = create_session()

    # -----------------------------------------------------------------------
    # Test 1: REPORT_HISTORY=7 (7-day window)
    # -----------------------------------------------------------------------
    html_7day = fetch_report_index(session, "7")
    save_path = OUTPUT_DIR / "report_index_7day.html"
    save_path.write_text(html_7day, encoding="utf-8")
    print(f"    Saved to {save_path}")

    entries_7day = parse_report_listings(html_7day)
    print(f"    Parsed {len(entries_7day)} report entries")

    # Classify by type
    type_counts: dict[str, int] = {}
    for e in entries_7day:
        rtype = classify_report(e["report_id"])
        type_counts[rtype] = type_counts.get(rtype, 0) + 1

    print("\n    Report types (7-day):")
    for rtype, count in sorted(type_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"      {rtype}: {count}")

    # -----------------------------------------------------------------------
    # Test 2: REPORT_HISTORY=ALL
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    html_all = fetch_report_index(session, "ALL")
    save_path = OUTPUT_DIR / "report_index_ALL.html"
    save_path.write_text(html_all, encoding="utf-8")
    print(f"    Saved to {save_path}")

    entries_all = parse_report_listings(html_all)
    print(f"    Parsed {len(entries_all)} report entries (ALL history)")

    type_counts_all: dict[str, int] = {}
    for e in entries_all:
        rtype = classify_report(e["report_id"])
        type_counts_all[rtype] = type_counts_all.get(rtype, 0) + 1

    print("\n    Report types (ALL):")
    for rtype, count in sorted(type_counts_all.items(), key=lambda x: -x[1])[:20]:
        print(f"      {rtype}: {count}")

    # -----------------------------------------------------------------------
    # Test 3: Fetch 5 SO.CONTRACT reports
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("\n[*] Fetching 5 SO.CONTRACT sample reports...")

    so_contract_entries = [
        e for e in entries_7day if classify_report(e["report_id"]) == "SO.CONTRACT"
    ]
    print(f"    Found {len(so_contract_entries)} SO.CONTRACT entries in 7-day window")

    samples = so_contract_entries[:5]
    for i, entry in enumerate(samples, 1):
        report_id = entry["report_id"]
        start = entry["start_line"]
        end = entry["end_line"]
        print(f"\n  [{i}/5] Fetching: {report_id}")
        print(f"         Lines: {start}-{end}")

        html = fetch_report_content(session, report_id, start, end)
        text = extract_text_from_iframe(html)

        # Save raw HTML
        safe_name = report_id.replace("*", "_").replace(":", "_").replace("/", "_")
        html_path = OUTPUT_DIR / f"so_contract_{i}_{safe_name}.html"
        html_path.write_text(html, encoding="utf-8")

        # Save extracted text
        txt_path = OUTPUT_DIR / f"so_contract_{i}_{safe_name}.txt"
        txt_path.write_text(text, encoding="utf-8")

        print(f"         HTML size: {len(html)} bytes")
        print(f"         Text size: {len(text)} chars")
        print(f"         Saved: {txt_path.name}")

        # Show first 500 chars of text
        preview = text[:500].replace("\n", "\n         ")
        print(f"         Preview:\n         {preview}")

        time.sleep(0.3)  # Be gentle

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  7-day reports:  {len(entries_7day)} entries, {len(type_counts)} types")
    print(f"  ALL reports:    {len(entries_all)} entries, {len(type_counts_all)} types")
    print(f"  SO.CONTRACT:    {len(so_contract_entries)} in 7-day window")
    print(f"  Samples saved:  {len(samples)} files in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
