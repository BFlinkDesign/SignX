"""Informer BI GWT-RPC Data Extraction Script.

Authenticates to Entrinsik Informer BI via SSO, then uses GWT-RPC v7
protocol to extract report definitions and sample data.

Auth flow:
    1. SSO URL → JSESSIONID cookie
    2. getActiveSession(true) → authToken (string table position 19)
    3. Protected RPC calls use ?authToken=<uuid>&clientId=<uuid>

Usage:
    python informer_gwtrpc_extract.py --list          # List all reports
    python informer_gwtrpc_extract.py --report 1441869 # Get specific report
    python informer_gwtrpc_extract.py --all            # Get all reports
"""
import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path

import requests

# Configuration
ERP_BASE = "https://eaglesign.keyedinsign.com"
INFORMER_BASE = f"{ERP_BASE}:8443/eaglesign"
MODULE_BASE = f"{INFORMER_BASE}/informer/"
GWT_PERMUTATION = "6823F3E0DFFF554BC1A7951AA98B182D"
OUTPUT_DIR = Path(r"C:\Users\Brady.EAGLE\Desktop\SignX\SignX-Intake\recon\responses\informer_reports")

# RPC Service constants
AUTH_SERVICE = "com.entrinsik.informer.core.client.service.AuthenticationRPCService"
AUTH_POLICY = "51B059033C002274BD4151F7D17FC702"
REPORT_SERVICE = "com.entrinsik.informer.core.client.service.ReportRPCService"
REPORT_POLICY = "F94C0FA52A7B058D7077BFA6B82FF792"

# Known report ID range
REPORT_ID_MIN = 1441850
REPORT_ID_MAX = 1441879


def load_erp_session():
    """Load ERP session cookie from .env file."""
    env_path = Path(r"C:\Scripts\keyedin-capture\.env")
    username = password = None
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("KEYEDIN_USERNAME="):
                username = line.split("=", 1)[1].strip()
            elif line.startswith("KEYEDIN_PASSWORD="):
                password = line.split("=", 1)[1].strip()
    return username, password


def get_erp_session_cookie():
    """Get ERP SESSIONID from browser cookies or by logging in."""
    # Try to use existing session by testing WEB.MENU
    state_file = OUTPUT_DIR / "session_state.json"
    if state_file.exists():
        state = json.loads(state_file.read_text())
        session_id = state.get("erp_session_id")
        if session_id:
            # Verify still valid
            resp = requests.get(
                f"{ERP_BASE}/cgi-bin/mvi.exe/WEB.MENU",
                cookies={"SESSIONID": session_id, "user": "BRADYF", "secure": "TRUE"},
                timeout=15,
            )
            if resp.status_code == 200 and len(resp.text) > 1000:
                return session_id
    return None


def sso_authenticate(erp_session_id):
    """Authenticate to Informer via SSO and get JSESSIONID + authToken."""
    session = requests.Session()

    # Step 1: SSO URL → JSESSIONID
    sso_url = f"{INFORMER_BASE}/sso?u=BRADYF&t={erp_session_id}"
    resp = session.get(sso_url, allow_redirects=False, timeout=15, verify=True)
    jsessionid = None
    for cookie in resp.cookies:
        if cookie.name == "JSESSIONID":
            jsessionid = cookie.value
            break

    if not jsessionid:
        # Try from Set-Cookie header
        sc = resp.headers.get("Set-Cookie", "")
        m = re.search(r"JSESSIONID=([^;]+)", sc)
        if m:
            jsessionid = m.group(1)

    if not jsessionid:
        print("ERROR: No JSESSIONID from SSO")
        return None, None, None

    print(f"  JSESSIONID: {jsessionid[:20]}...")

    # Step 2: getActiveSession(true) → authToken
    payload = (
        f"7|0|5|{MODULE_BASE}|{AUTH_POLICY}|{AUTH_SERVICE}|getActiveSession|Z|"
        "1|2|3|4|1|5|1|"
    )
    resp = session.post(
        f"{MODULE_BASE}rpc/AuthenticationRPCService",
        data=payload,
        headers={
            "Content-Type": "text/x-gwt-rpc; charset=UTF-8",
            "X-GWT-Permutation": GWT_PERMUTATION,
        },
        cookies={"JSESSIONID": jsessionid},
        timeout=15,
    )

    if not resp.text.startswith("//OK"):
        print(f"ERROR: getActiveSession failed: {resp.text[:200]}")
        return jsessionid, None, None

    # Extract authToken - it's the UUID at string table position 19
    # (the third UUID in the response, a persistent per-user token)
    uuids = re.findall(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        resp.text,
    )
    auth_token = uuids[2] if len(uuids) >= 3 else None
    if not auth_token:
        print(f"ERROR: Could not extract authToken. UUIDs found: {uuids}")
        return jsessionid, None, None

    print(f"  authToken: {auth_token}")
    return jsessionid, auth_token, str(uuid.uuid4())


def gwt_rpc_call(jsessionid, auth_token, client_id, endpoint, payload):
    """Make a GWT-RPC call to a protected endpoint."""
    url = f"{MODULE_BASE}rpc/protected/{endpoint}"
    if auth_token:
        url += f"?authToken={auth_token}&clientId={client_id}"

    resp = requests.post(
        url,
        data=payload,
        headers={
            "Content-Type": "text/x-gwt-rpc; charset=UTF-8",
            "X-GWT-Permutation": GWT_PERMUTATION,
        },
        cookies={"JSESSIONID": jsessionid},
        timeout=30,
    )
    return resp.text


def lookup_report(jsessionid, auth_token, client_id, report_id, with_sample=False):
    """Call lookupReportAndSample for a specific report ID."""
    sample = "1" if with_sample else "0"
    payload = (
        f"7|0|6|{MODULE_BASE}|{REPORT_POLICY}|{REPORT_SERVICE}|"
        f"lookupReportAndSample|I|Z|"
        f"1|2|3|4|3|5|6|6|{report_id}|{sample}|{sample}|"
    )
    return gwt_rpc_call(jsessionid, auth_token, client_id, "ReportRPCService", payload)


def parse_report_response(resp_text):
    """Parse a GWT-RPC response to extract report metadata."""
    if not resp_text.startswith("//OK"):
        if "AccessDenied" in resp_text:
            return {"status": "ACCESS_DENIED"}
        if "Unauthenticated" in resp_text:
            return {"status": "UNAUTHENTICATED"}
        if "FinderE" in resp_text:
            return {"status": "NOT_FOUND"}
        return {"status": "ERROR", "message": resp_text[:200]}

    # Extract string table
    bracket_start = resp_text.rfind('["')
    if bracket_start < 0:
        return {"status": "PARSE_ERROR"}

    bracket_end = resp_text.find("]", bracket_start)
    string_section = resp_text[bracket_start : bracket_end + 1]
    strings = re.findall(r'"((?:[^"\\]|\\.)*)"', string_section)

    # Categorize strings
    columns = []
    report_name = None

    for s in strings:
        if s.startswith(("com.", "java.", "[L", "rO0", "{")):
            continue
        if "/" in s:
            continue

        # Column names (ALL CAPS with dots)
        if re.match(r"^[A-Z][A-Z0-9_.]+$", s) and 2 < len(s) < 30:
            columns.append(s)

    # Find report name
    for s in strings:
        if (
            5 < len(s) < 80
            and " " in s
            and s[0].isupper()
            and not any(s.startswith(p) for p in ("com.", "java.", "rO0", "G*", "font-"))
            and "/" not in s
        ):
            report_name = s
            break

    return {
        "status": "OK",
        "name": report_name or "Unknown",
        "columns": columns,
        "response_size": len(resp_text),
        "num_strings": len(strings),
    }


def scan_reports(jsessionid, auth_token, client_id):
    """Scan all report IDs and return inventory."""
    reports = {}
    for rid in range(REPORT_ID_MIN, REPORT_ID_MAX + 1):
        resp = lookup_report(jsessionid, auth_token, client_id, rid, with_sample=False)
        parsed = parse_report_response(resp)
        reports[str(rid)] = parsed
        status_char = (
            "+" if parsed["status"] == "OK"
            else "X" if parsed["status"] == "ACCESS_DENIED"
            else "?" if parsed["status"] == "NOT_FOUND"
            else "!"
        )
        name = parsed.get("name", parsed["status"])
        print(f"  [{status_char}] {rid}: {name}")

        if parsed["status"] == "UNAUTHENTICATED":
            print("  Session expired! Re-authenticate.")
            break

        # Save individual response
        outfile = OUTPUT_DIR / f"report_{rid}.txt"
        outfile.write_text(resp, encoding="utf-8")

    return reports


def main():
    parser = argparse.ArgumentParser(description="Informer BI GWT-RPC Extractor")
    parser.add_argument("--list", action="store_true", help="List all reports")
    parser.add_argument("--report", type=int, help="Get specific report by ID")
    parser.add_argument("--all", action="store_true", help="Get all reports")
    parser.add_argument("--erp-session", type=str, help="ERP SESSIONID cookie value")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    erp_session = args.erp_session or get_erp_session_cookie()
    if not erp_session:
        print("ERROR: No ERP session. Provide --erp-session <SESSIONID>")
        sys.exit(1)

    print("Authenticating to Informer via SSO...")
    jsessionid, auth_token, client_id = sso_authenticate(erp_session)
    if not auth_token:
        print("ERROR: Authentication failed")
        sys.exit(1)
    print(f"  clientId: {client_id}")
    print("  Authentication successful!")

    if args.list or args.all:
        print("\nScanning reports...")
        reports = scan_reports(jsessionid, auth_token, client_id)
        outfile = OUTPUT_DIR / "report_inventory.json"
        with open(outfile, "w") as f:
            json.dump(reports, f, indent=2)
        print(f"\nInventory saved to {outfile}")

        accessible = sum(1 for r in reports.values() if r["status"] == "OK")
        denied = sum(1 for r in reports.values() if r["status"] == "ACCESS_DENIED")
        print(f"\nSummary: {accessible} accessible, {denied} denied, {len(reports)} total")

    elif args.report:
        print(f"\nFetching report {args.report} with sample data...")
        resp = lookup_report(jsessionid, auth_token, client_id, args.report, with_sample=True)
        parsed = parse_report_response(resp)

        outfile = OUTPUT_DIR / f"report_{args.report}_sample.txt"
        outfile.write_text(resp, encoding="utf-8")

        if parsed["status"] == "OK":
            print(f"  Name: {parsed['name']}")
            print(f"  Columns: {', '.join(parsed['columns'][:10])}")
            print(f"  Response: {parsed['response_size']:,} chars")
            print(f"  Saved to: {outfile}")
        else:
            print(f"  Status: {parsed['status']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
