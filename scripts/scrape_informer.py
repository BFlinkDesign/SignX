"""
Phase 2: Informer BI Report Extraction via Direct HTTP
=======================================================

Extracts all 30 Informer BI reports using direct GWT RPC over HTTP.
No browser automation — pure Python requests.

Flow:
  1. Login to KeyedIn ERP via form POST
  2. SSO handoff to Informer BI (port 8443)
  3. For each report: RunReportCommand → paginate → parse → CSV

Prerequisites:
  - .env file with KEYEDIN_USERNAME and KEYEDIN_PASSWORD
  - Network access to eaglesign.keyedinsign.com (VPN if needed)

Usage:
  python scrape_informer.py [--report REPORT_ID] [--list]
"""

import csv
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# Fixed GWT parser with right-to-left row extraction
from gwt_parser import (
    GwtParseError,
    discover_field_names as gwt_discover_field_names,
    extract_rows as gwt_extract_rows,
    extract_total_count as gwt_extract_total_count,
    extract_view_token as gwt_extract_view_token,
    parse_gwt_response as gwt_parse_response,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ENV_FILE = Path(r"C:\Scripts\keyedin-capture\.env")
OUTPUT_DIR = Path(r"C:\Scripts\signx-warehouse\warehouse\raw")
SESSION_FILE = Path(r"C:\Scripts\signx-warehouse\warehouse\raw\informer_session.json")
GETDATA_TEMPLATE_FILE = Path(
    r"C:\Scripts\keyedin-capture\reports\report_data_page2_req118_request.txt"
)

# KeyedIn ERP
ERP_BASE = "https://eaglesign.keyedinsign.com"
LOGIN_URL = f"{ERP_BASE}/cgi-bin/mvi.exe/LOGIN.START"
DASHBOARD_URL = f"{ERP_BASE}/cgi-bin/mvi.exe/DASHBOARD"

# Informer BI
INFORMER_BASE = "https://eaglesign.keyedinsign.com:8443"
INFORMER_PATH = "/eaglesign/informer"
MODULE_BASE = f"{INFORMER_BASE}{INFORMER_PATH}/"
GWT_PERMUTATION = "6823F3E0DFFF554BC1A7951AA98B182D"

# RPC Endpoints
RPC_ENDPOINTS = {
    "auth": f"{INFORMER_PATH}/rpc/AuthenticationRPCService",
    "report": f"{INFORMER_PATH}/rpc/protected/ReportRPCService",
    "view": f"{INFORMER_PATH}/rpc/protected/ViewRPCService",
    "command": f"{INFORMER_PATH}/commandService",
    "doctmpl": f"{INFORMER_PATH}/rpc/protected/DocumentTemplateRPCService",
}

# Policy Keys (from serialization policy files)
POLICY_KEYS = {
    "auth": "51B059033C002274BD4151F7D17FC702",
    "report": "F94C0FA52A7B058D7077BFA6B82FF792",
    "view": "327E0F303D0CA463050DC31340CFE01D",
    "command": "81D82B6C6154989542DE45F20CEB3EF0",
    "doctmpl": "05E06838523AECED1434383744A449D0",
}

# All 30 reports from reports_manifest.json
REPORTS = [
    {"id": 1441842, "name": "AR Invoice Details", "tag": "Accounts Receivable"},
    {"id": 1441843, "name": "AR Invoice Listing", "tag": "Accounts Receivable"},
    {"id": 1441844, "name": "AR Open Invoices", "tag": "Accounts Receivable"},
    {"id": 1441849, "name": "Cash Receipts", "tag": "Accounts Receivable"},
    {"id": 1441850, "name": "Customer Listing", "tag": "Accounts Receivable"},
    {"id": 1441851, "name": "Customer Listing Export", "tag": "Export"},
    {"id": 1441852, "name": "Customer Location Listing", "tag": "Accounts Receivable"},
    {"id": 1441853, "name": "Customer Location Listing Export", "tag": "Export"},
    {"id": 1441854, "name": "Inventory List", "tag": "Inventory and Parts"},
    {"id": 1441855, "name": "Inventory List Export", "tag": "Export"},
    {"id": 1441856, "name": "Inventory Transaction History", "tag": "Inventory and Parts"},
    {"id": 1441857, "name": "Invoice Register", "tag": "Invoicing"},
    {"id": 1441859, "name": "Open Sales Order Backlog", "tag": "Sales Orders"},
    {"id": 1441860, "name": "Open Sales Orders", "tag": "Sales Orders"},
    {"id": 1441861, "name": "Open Work Orders", "tag": "Production"},
    {"id": 1441862, "name": "Planned Part Activity", "tag": "Inventory and Parts"},
    {"id": 1441865, "name": "Purchase History", "tag": "Purchasing"},
    {"id": 1441866, "name": "Purchase Order Detail", "tag": "Purchasing"},
    {"id": 1441868, "name": "Purchased Part Variance", "tag": "Accounts Payable"},
    {"id": 1441869, "name": "Quote Status Report", "tag": "Estimating"},
    {"id": 1441870, "name": "Sales Cost Detail Report", "tag": "Sales Analysis"},
    {"id": 1441872, "name": "Sales Order Bookings By Line Date", "tag": "Sales Orders"},
    {"id": 1441873, "name": "Sales Order Bookings By SO Date", "tag": "Sales Orders"},
    {"id": 1441874, "name": "Sales Order Detail", "tag": "Sales Orders"},
    {"id": 1441875, "name": "Sales Order Status by Customer", "tag": "Sales Orders"},
    {"id": 1441877, "name": "Sales Summary by Customer", "tag": "Sales Analysis"},
    {"id": 1441878, "name": "Sales Summary by Product Type", "tag": "Sales Analysis"},
    {"id": 1441883, "name": "Vendor Listing", "tag": "Accounts Payable"},
    {"id": 1441884, "name": "Vendor Listing Export", "tag": "Export"},
    {"id": 1441887, "name": "Work Order Listing", "tag": "Production"},
]

# Prefer "Export" variants where available (formatted for CSV extraction)
EXPORT_VARIANTS = {
    1441850: 1441851,  # Customer Listing → Export version
    1441852: 1441853,  # Customer Location → Export version
    1441854: 1441855,  # Inventory List → Export version
    1441883: 1441884,  # Vendor Listing → Export version
}

PAGE_SIZE = 25  # Keep Informer default page size (getData template uses 25)
REQUEST_TIMEOUT = 120

# Old auth tokens from capture session (used to find-and-replace in templates)
CAPTURED_AUTH_TOKEN = "6728f894-940d-4611-85e7-a40d225d58eb"
CAPTURED_CLIENT_ID = "cf4f5ce2-8fb2-456e-b23f-3755434cfdf0"
CAPTURED_VIEW_TOKEN = "52a0a4c6-2ca7-40cf-9d79-15a008c76149"

# ---------------------------------------------------------------------------
# Field names per report
# ---------------------------------------------------------------------------
# Each report needs its GWT field names so the RTL parser can extract rows.
# These are the HashMap key names from the GWT Row serialisation.

REPORT_FIELDS: dict[int, list[str]] = {
    # Quote Status Report (ID: 1441869)
    1441869: [
        "quoteno",
        "salesperson",
        "qtDate",
        "defaultShip",
        "expDate",
        "acctid",
        "company",
        "specInst",
        "extPrice",
        "salesStage2",
        "statusCode&Description",
        "currStatusDate2",
        "statusTime_2",
        "wono",
        "inactiveMsg",
        "currStatus",
        "quoteStatusCodes_assoc_descr",
        "salesStage",
        "quoteSalesStage_assoc_descr",
        "qtyOrdered",
        "salesTotal",
        "sellingPrice",
        "classifyAsLoss",
        "inactive",
        "inactive2",
        "specInst2",
        "currStatusDate",
        "descr",
    ],
    # Customer Listing (ID: 1441850)
    1441850: [
        "custNo",
        "name",
        "address",
        "address_2",
        "city",
        "state",
        "zip",
        "phone",
        "contact",
        "taxCode",
        "desc",
        "linkToSalesperson_assoc_name",
        "customer",
        "linkToPymtTerms_assoc_desc",
    ],
    # Customer Listing Export (ID: 1441851) -- same fields
    1441851: [
        "custNo",
        "name",
        "address",
        "address_2",
        "city",
        "state",
        "zip",
        "phone",
        "contact",
        "taxCode",
        "desc",
        "linkToSalesperson_assoc_name",
        "customer",
        "linkToPymtTerms_assoc_desc",
    ],
}

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("informer")


# ---------------------------------------------------------------------------
# GWT RPC Protocol Helpers
# ---------------------------------------------------------------------------


class GwtRpcError(Exception):
    """GWT RPC returned an exception response."""

    def __init__(self, response_text):
        self.response_text = response_text
        # Try to extract error message from //EX response
        match = re.search(r'"([^"]+)"', response_text)
        msg = match.group(1) if match else response_text[:200]
        super().__init__(f"GWT RPC Error: {msg}")


def build_gwt_payload(strings: list[str], refs: list[int | str]) -> str:
    """Build a GWT RPC v7 pipe-delimited payload.

    Args:
        strings: String table entries (MODULE_BASE, policy key, service, method, types, values)
        refs: Reference section (indices into string table + literal values)

    Returns:
        Pipe-delimited GWT RPC v7 payload string.
    """
    parts = ["7", "0", str(len(strings))]
    parts.extend(strings)
    parts.extend(str(r) for r in refs)
    return "|".join(parts) + "|"


def parse_gwt_response(text: str) -> dict:
    """Parse a GWT RPC //OK[...] response into structured data.

    Returns dict with:
        - 'data': raw data values (list of mixed int/float/str)
        - 'strings': string table
        - 'offset': integer offset
        - 'version': protocol version
    """
    text = text.strip()

    if text.startswith("//EX"):
        raise GwtRpcError(text)

    if not text.startswith("//OK"):
        raise ValueError(f"Not a GWT response: {text[:80]}")

    # Remove //OK prefix
    inner = text[4:]

    # The response is: [data_values, ["string1","string2",...], offset, version]
    # We need to carefully parse this because data_values can contain
    # strings with commas and quotes.

    # Find the string table — it's the last [...] before the final ,offset,version]
    # Strategy: find the last occurrence of ,["
    str_table_start = inner.rfind(',["')
    if str_table_start == -1:
        # No string table — might be a simple response
        return {"data": [], "strings": [], "raw": inner}

    # Find the matching closing bracket for the string table
    # The string table ends with "],offset,version]"
    bracket_depth = 0
    str_table_end = -1
    i = str_table_start + 1  # Start after the comma
    while i < len(inner):
        ch = inner[i]
        if ch == "[":
            bracket_depth += 1
        elif ch == "]":
            bracket_depth -= 1
            if bracket_depth == 0:
                str_table_end = i
                break
        elif ch == '"':
            # Skip quoted string (handle escaped quotes)
            i += 1
            while i < len(inner) and inner[i] != '"':
                if inner[i] == "\\":
                    i += 1  # Skip escaped char
                i += 1
        i += 1

    if str_table_end == -1:
        raise ValueError("Could not find end of string table")

    # Parse string table
    str_table_raw = inner[str_table_start + 1 : str_table_end + 1]
    strings = _parse_string_table(str_table_raw)

    # Parse data values (everything before the string table within the outer [...])
    data_raw = inner[1:str_table_start]  # Skip leading '['
    data_values = _parse_data_values(data_raw)

    # Parse offset and version (after string table)
    trailer = inner[str_table_end + 1 :].rstrip("]")
    trailer_parts = [p.strip() for p in trailer.split(",") if p.strip()]
    offset = int(trailer_parts[0]) if len(trailer_parts) > 0 else 0
    version = int(trailer_parts[1]) if len(trailer_parts) > 1 else 7

    return {
        "data": data_values,
        "strings": strings,
        "offset": offset,
        "version": version,
    }


def _parse_string_table(raw: str) -> list[str]:
    """Parse a JSON-like string array: ["str1","str2",...]"""
    try:
        # Handle GWT-specific escaping: \x3D -> =, \x27 -> ', etc.
        cleaned = raw.replace("\\x3D", "=").replace("\\x3d", "=")
        cleaned = cleaned.replace("\\x27", "'").replace("\\x26", "&")
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: regex extraction
        return re.findall(r'"((?:[^"\\]|\\.)*)"', raw)


def _parse_data_values(raw: str) -> list:
    """Parse comma-separated data values (ints, floats, quoted strings)."""
    values = []
    if not raw.strip():
        return values

    # Split on commas, but respect quoted strings
    i = 0
    current = ""
    in_quote = False

    for ch in raw:
        if ch == "'" and not in_quote:
            in_quote = True
            current += ch
        elif ch == "'" and in_quote:
            in_quote = False
            current += ch
        elif ch == "," and not in_quote:
            current = current.strip()
            if current:
                values.append(_parse_value(current))
            current = ""
        else:
            current += ch

    current = current.strip()
    if current:
        values.append(_parse_value(current))

    return values


def _parse_value(s: str):
    """Parse a single GWT data value."""
    if not s:
        return None
    # Quoted string
    if s.startswith("'") and s.endswith("'"):
        return s[1:-1]
    # Float
    if "." in s:
        try:
            return float(s)
        except ValueError:
            pass
    # Integer
    try:
        return int(s)
    except ValueError:
        pass
    return s


# Old extract_rows_from_gwt and extract_report_data_from_gwt removed --
# replaced by gwt_parser module (gwt_extract_rows, gwt_extract_view_token,
# gwt_extract_total_count).


# ---------------------------------------------------------------------------
# Informer GWT RPC Client
# ---------------------------------------------------------------------------


class InformerClient:
    """HTTP client for Entrinsik Informer 4.x GWT RPC."""

    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False  # Self-signed cert on port 8443
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0",
            }
        )
        self.auth_token = None
        self.client_id = None
        self.jsessionid = None

    # ----- Authentication -----

    def login_erp(self, username: str, password: str) -> bool:
        """Step 1: Login to KeyedIn ERP via form POST."""
        log.info("Logging into KeyedIn ERP...")

        # POST login credentials
        resp = self.session.post(
            LOGIN_URL,
            data={"USERNAME": username, "PASSWORD": password, "btnLogin": "Login"},
            allow_redirects=True,
            timeout=REQUEST_TIMEOUT,
        )

        if resp.status_code != 200:
            log.error(f"ERP login failed: HTTP {resp.status_code}")
            return False

        # Check if we landed on dashboard
        if "DASHBOARD" in resp.url.upper() or "DASHBOARD" in resp.text.upper():
            log.info("  ERP login successful (dashboard loaded)")
            return True

        # Check for error indicators
        if "invalid" in resp.text.lower() or "error" in resp.text.lower():
            log.error("  ERP login failed — invalid credentials")
            return False

        log.warning(f"  ERP login status uncertain. URL: {resp.url}")
        return True  # Proceed anyway

    def discover_sso_url(self) -> str | None:
        """Step 2: Find the Informer SSO link on the KeyedIn dashboard."""
        log.info("Discovering Informer SSO link...")

        # Try the dashboard page
        resp = self.session.get(DASHBOARD_URL, timeout=REQUEST_TIMEOUT)

        # Look for SSO link pattern: href containing 8443 or /sso
        patterns = [
            r'href=["\']([^"\']*8443[^"\']*)["\']',
            r'href=["\']([^"\']*sso[^"\']*)["\']',
            r'href=["\']([^"\']*informer[^"\']*)["\']',
            r'href=["\']([^"\']*Informer[^"\']*)["\']',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, resp.text, re.IGNORECASE)
            for match in matches:
                if "8443" in match or "sso" in match.lower():
                    log.info(f"  Found SSO link: {match[:80]}...")
                    return match

        # Try looking for JavaScript-based redirects or SSO token generation
        # Pattern: window.open('https://...8443/eaglesign/sso?...')
        js_patterns = [
            r"window\.open\(['\"]([^'\"]*8443[^'\"]*)['\"]",
            r"location\.href\s*=\s*['\"]([^'\"]*8443[^'\"]*)['\"]",
            r"['\"]([^'\"]*eaglesign/sso[^'\"]*)['\"]",
        ]

        for pattern in js_patterns:
            matches = re.findall(pattern, resp.text, re.IGNORECASE)
            for match in matches:
                log.info(f"  Found SSO URL in JS: {match[:80]}...")
                return match

        # Try known KeyedIn BI Reports menu page
        bi_pages = [
            f"{ERP_BASE}/cgi-bin/mvi.exe/INFORMER",
            f"{ERP_BASE}/cgi-bin/mvi.exe/BI.REPORTS",
            f"{ERP_BASE}/cgi-bin/mvi.exe/MENU.REPORTS",
        ]

        for page_url in bi_pages:
            try:
                resp = self.session.get(page_url, timeout=REQUEST_TIMEOUT)
                for pattern in patterns:
                    matches = re.findall(pattern, resp.text, re.IGNORECASE)
                    for match in matches:
                        if "8443" in match:
                            log.info(f"  Found SSO link on {page_url}: {match[:80]}...")
                            return match
            except Exception:
                continue

        log.warning("  Could not find SSO link. Will try direct Informer login.")
        return None

    def sso_to_informer(self, sso_url: str) -> bool:
        """Step 3: Follow SSO link to Informer to establish session."""
        log.info("Following SSO to Informer...")

        resp = self.session.get(sso_url, timeout=REQUEST_TIMEOUT, allow_redirects=True)

        # Check for JSESSIONID in cookies
        for cookie in self.session.cookies:
            if cookie.name == "JSESSIONID":
                self.jsessionid = cookie.value
                log.info(f"  Got JSESSIONID: {self.jsessionid[:20]}...")
                return True

        log.warning("  No JSESSIONID found after SSO redirect")
        return False

    def login_informer_direct(self, username: str, password: str) -> bool:
        """Alternative: Login to Informer directly via GWT RPC.

        Used if SSO link discovery fails.
        """
        log.info("Attempting direct Informer login via GWT RPC...")

        # First, hit the Informer page to get a JSESSIONID
        informer_url = f"{INFORMER_BASE}/eaglesign/Informer.html?locale=en_US"
        resp = self.session.get(informer_url, timeout=REQUEST_TIMEOUT)

        for cookie in self.session.cookies:
            if cookie.name == "JSESSIONID":
                self.jsessionid = cookie.value
                log.info(f"  Got JSESSIONID from page load: {self.jsessionid[:20]}...")
                break

        if not self.jsessionid:
            log.error("  No JSESSIONID obtained")
            return False

        # Try GWT RPC login
        # Method: AuthenticationRPCService.login(String username, String password)
        payload = build_gwt_payload(
            strings=[
                MODULE_BASE,
                POLICY_KEYS["auth"],
                "com.entrinsik.informer.core.client.service.AuthenticationRPCService",
                "login",
                "java.lang.String/2004016611",
                username.upper(),  # Informer uses uppercase usernames
                password,
            ],
            refs=[1, 2, 3, 4, 2, 5, 5, 6, 7],
        )

        try:
            resp = self._send_rpc("auth", payload)
            if resp.startswith("//OK"):
                log.info("  Direct Informer login successful")
                return self._extract_auth_from_response(resp)
            else:
                log.error(f"  Direct login failed: {resp[:200]}")
                return False
        except GwtRpcError as e:
            log.error(f"  Direct login GWT error: {e}")
            # Try SSO-based authentication method
            return self._try_sso_auth(username, password)

    def _try_sso_auth(self, username: str, password: str) -> bool:
        """Try SSO authentication via SingleSignOnAuthentication."""
        log.info("  Trying SSO authentication method...")

        payload = build_gwt_payload(
            strings=[
                MODULE_BASE,
                POLICY_KEYS["auth"],
                "com.entrinsik.informer.core.client.service.AuthenticationRPCService",
                "authenticate",
                "com.entrinsik.informer.core.domain.security.UsernamePasswordAuthentication/3747181498",
                username.upper(),
                password,
            ],
            refs=[1, 2, 3, 4, 1, 5, 5, 6, 7],
        )

        try:
            resp = self._send_rpc("auth", payload)
            if resp.startswith("//OK"):
                log.info("  SSO auth successful")
                return self._extract_auth_from_response(resp)
        except GwtRpcError as e:
            log.error(f"  SSO auth failed: {e}")

        return False

    def get_active_session(self) -> bool:
        """Check for active session and extract auth tokens."""
        log.info("Checking active Informer session...")

        payload = build_gwt_payload(
            strings=[
                MODULE_BASE,
                POLICY_KEYS["auth"],
                "com.entrinsik.informer.core.client.service.AuthenticationRPCService",
                "getActiveSession",
                "Z",  # boolean type
            ],
            refs=[1, 2, 3, 4, 1, 5, 1],  # 1 param, type Z, value 1 (true)
        )

        try:
            resp = self._send_rpc("auth", payload)
            if resp.startswith("//OK"):
                return self._extract_auth_from_response(resp)
        except GwtRpcError:
            pass

        return False

    def _extract_auth_from_response(self, response_text: str) -> bool:
        """Extract authToken and clientId from an auth response."""
        try:
            parsed = parse_gwt_response(response_text)
            strings = parsed["strings"]

            # Look for UUID-formatted strings (authToken, clientId)
            uuids = []
            for s in strings:
                if re.match(
                    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                    s,
                ):
                    uuids.append(s)

            if len(uuids) >= 3:
                # getActiveSession returns 3 UUIDs:
                #   [0] = session token (not used for commands)
                #   [1] = clientId
                #   [2] = authToken (used for commandService)
                self.auth_token = uuids[-1]   # Last UUID is the auth token
                self.client_id = uuids[1]
                log.info(f"  authToken: {self.auth_token[:20]}...")
                log.info(f"  clientId: {self.client_id[:20]}...")
                return True
            elif len(uuids) == 2:
                self.auth_token = uuids[-1]
                self.client_id = uuids[0]
                log.info(f"  authToken: {self.auth_token[:20]}...")
                log.info(f"  clientId: {self.client_id[:20]}...")
                return True
            elif len(uuids) == 1:
                self.auth_token = uuids[0]
                log.info(f"  authToken: {self.auth_token[:20]}...")
                log.warning("  Only one UUID found -- clientId may be missing")
                return True

            log.error("  Could not extract auth tokens from response")
            return False

        except Exception as e:
            log.error(f"  Failed parsing auth response: {e}")
            return False

    # ----- RPC Communication -----

    def _send_rpc(self, service_key: str, payload: str) -> str:
        """Send a GWT RPC request and return raw response text."""
        url = f"{INFORMER_BASE}{RPC_ENDPOINTS[service_key]}"

        # Add auth params to URL for protected services
        if self.auth_token and service_key != "auth":
            url += f"?authToken={self.auth_token}&clientId={self.client_id}"

        headers = {
            "Content-Type": "text/x-gwt-rpc; charset=UTF-8",
            "X-GWT-Permutation": GWT_PERMUTATION,
            "X-GWT-Module-Base": MODULE_BASE,
        }

        resp = self.session.post(
            url,
            data=payload.encode("utf-8"),
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        if resp.status_code != 200:
            log.error(f"RPC failed: HTTP {resp.status_code}")
            log.error(f"Response: {resp.text[:500]}")
            raise GwtRpcError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        return resp.text

    # ----- Report Operations -----

    def get_reports_list(self) -> list[dict]:
        """Get the list of available reports via ReportRPCService.getReports."""
        log.info("Fetching report list...")

        payload = build_gwt_payload(
            strings=[
                MODULE_BASE,
                POLICY_KEYS["report"],
                "com.entrinsik.informer.core.client.service.ReportRPCService",
                "getReports",
                "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
                "java.util.HashMap/1797211028",
                "en_US",
                "java.util.ArrayList/4159755760",
                "com.entrinsik.gwt.data.shared.Order/1651361273",
                "name",
            ],
            refs=[
                1,
                2,
                3,
                4,
                1,
                5,
                5,
                6,
                0,
                0,
                0,
                0,
                -1,  # limit=-1 (all)
                7,
                8,
                1,
                9,
                1,
                10,
                0,
                0,
                0,
                0,
                0,
            ],
        )

        try:
            resp = self._send_rpc("report", payload)
            parsed = parse_gwt_response(resp)

            # Extract report names and IDs from string table
            reports = []
            strings = parsed["strings"]
            for idx, s in enumerate(strings):
                # Look for report IDs (integers in string table following Report type)
                pass

            log.info(f"  Got report list response ({len(strings)} strings)")
            return reports

        except GwtRpcError as e:
            log.error(f"  Failed to get reports: {e}")
            return []

    def run_report_command(self, report_payload: str) -> tuple[str, str]:
        """Send a RunReportCommand and return (response_text, view_token).

        Args:
            report_payload: Complete GWT RPC payload for the RunReportCommand.

        Returns:
            Tuple of (raw response text, ViewToken UUID).
        """
        log.info("  Sending RunReportCommand...")

        resp = self._send_rpc("command", report_payload)

        # Extract ViewToken from response
        parsed = parse_gwt_response(resp)
        view_token = None
        for idx, s in enumerate(parsed["strings"]):
            if "ViewToken" in s and idx + 1 < len(parsed["strings"]):
                candidate = parsed["strings"][idx + 1]
                if re.match(
                    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                    candidate,
                ):
                    view_token = candidate
                    break

        if view_token:
            log.info(f"  ViewToken: {view_token}")
        else:
            log.warning("  No ViewToken found in response")

        return resp, view_token

    def replay_view_rpc(self, view_payload: str) -> tuple[str, str]:
        """Send a captured ViewRPCService payload and return (response_text, view_token).

        This replays payloads captured from the browser's ViewRPCService POST,
        as opposed to run_report_command() which uses commandService.

        Args:
            view_payload: Complete GWT RPC payload for ViewRPCService.

        Returns:
            Tuple of (raw response text, ViewToken UUID or None).
        """
        log.info("  Sending ViewRPCService replay...")

        resp = self._send_rpc("view", view_payload)

        # Extract ViewToken from response (same logic as run_report_command).
        view_token = gwt_extract_view_token(resp)

        if view_token:
            log.info(f"  ViewToken: {view_token}")
        else:
            log.warning("  No ViewToken found in ViewRPCService response")

        return resp, view_token

    def get_view_data(self, view_token: str, offset: int, limit: int) -> str:
        """Fetch a page of data from a ViewToken via ViewRPCService.getData.

        Uses array-based parameter types: getData(ViewToken[], LoadOptions[])
        which matches the server's actual method signature (captured from browser).
        Includes a wildcard search filter (name MATCHES **) and ReportSearchOptions
        as the browser does.
        """
        payload = build_gwt_payload(
            strings=[
                MODULE_BASE,                                                          # 1
                POLICY_KEYS["view"],                                                  # 2
                "com.entrinsik.informer.core.client.service.ViewRPCService",          # 3
                "getData",                                                            # 4
                "[Lcom.entrinsik.gwt.data.shared.ViewToken;/2990910562",              # 5
                "[Lcom.entrinsik.gwt.data.shared.LoadOptions;/2486573562",            # 6
                "com.entrinsik.gwt.data.shared.ViewToken/3777265110",                 # 7
                view_token,                                                           # 8
                "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",               # 9
                "java.util.HashMap/1797211028",                                       # 10
                "com.entrinsik.gwt.data.shared.criteria.impl.JunctionImpl/346417575", # 11
                "java.util.ArrayList/4159755760",                                     # 12
                "com.entrinsik.gwt.data.shared.criteria.Operator/2483661797",         # 13
                "com.entrinsik.gwt.data.shared.criteria.impl.ValueExpressionImpl/3874770769",  # 14
                "name",                                                               # 15
                "com.entrinsik.gwt.data.shared.criteria.Quantifier/3325804167",       # 16
                "com.entrinsik.gwt.data.shared.values.StringValue/2414534542",        # 17
                "**",                                                                 # 18
                "com.entrinsik.informer.core.domain.report.ReportSearchOptions/1133289605",    # 19
                "en_US",                                                              # 20
                "com.entrinsik.gwt.data.shared.Order/1651361273",                     # 21
                "com.entrinsik.gwt.data.shared.values.NullValue/2880996259",          # 22
            ],
            refs=[
                1, 2, 3, 4,         # header: moduleBase, policyKey, service, method
                2, 5, 6,            # 2 params, types: ViewToken[], LoadOptions[]
                5, 1, 7, 8,         # ViewToken array: size=1, ViewToken(uuid)
                6, 1,               # LoadOptions array: size=1
                9, 10, 0,           # LoadOptions, HashMap(0 entries)
                11, 12, 2,          # JunctionImpl(AND), ArrayList(size=2)
                11, 12, 1,          #   inner JunctionImpl, ArrayList(size=1)
                11, 12, 0,          #     innermost JunctionImpl, ArrayList(size=0)
                13, 9,              #   Operator(MATCHES)
                13, 8,              #   Operator(LIKE)
                14, 1,              #   ValueExpressionImpl
                13, 2,              #   Operator(EQ)
                15, 16,             #   "name", Quantifier
                0, 17, 18,          #   0, StringValue("**")
                -13, 0,             #   backreference, 0
                19,                 # ReportSearchOptions
                12, 0, 0, 0, 0,    # ArrayList, 4 zeros
                offset, limit,      # pagination: offset, limit
                20,                 # "en_US"
                12, 1, 21, 1,      # ArrayList(size=1), Order, direction=1
                15, 1,              # "name", ascending=1
                0, 22, 0, 0,       # 0, NullValue, 0, 0 (trailing)
            ],
        )

        return self._send_rpc("view", payload)

    def get_row_count(self, view_token: str) -> int:
        """Get total row count via ViewRPCService.createSubQuery + ROW_COUNT projection."""
        # Step 1: Create sub-query
        payload = build_gwt_payload(
            strings=[
                MODULE_BASE,
                POLICY_KEYS["view"],
                "com.entrinsik.informer.core.client.service.ViewRPCService",
                "createSubQuery",
                "com.entrinsik.gwt.data.shared.ViewToken/3777265110",
                view_token,
            ],
            refs=[1, 2, 3, 4, 1, 5, 5, 6],
        )

        resp = self._send_rpc("view", payload)
        parsed = parse_gwt_response(resp)

        # Extract the new ViewToken for the sub-query
        sub_token = None
        for idx, s in enumerate(parsed["strings"]):
            if "ViewToken" in s and idx + 1 < len(parsed["strings"]):
                candidate = parsed["strings"][idx + 1]
                if re.match(
                    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                    candidate,
                ) and candidate != view_token:
                    sub_token = candidate
                    break

        if not sub_token:
            log.warning("  Could not create sub-query for row count")
            return 0

        # Step 2: getData with ROW_COUNT projection
        payload = build_gwt_payload(
            strings=[
                MODULE_BASE,
                POLICY_KEYS["view"],
                "com.entrinsik.informer.core.client.service.ViewRPCService",
                "getData",
                "com.entrinsik.gwt.data.shared.ViewToken/3777265110",
                "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
                sub_token,
                "java.util.HashMap/1797211028",
                "com.entrinsik.gwt.data.shared.Query/630488762",
                "com.entrinsik.gwt.data.shared.criteria.impl.JunctionImpl/346417575",
                "java.util.ArrayList/4159755760",
                "com.entrinsik.gwt.data.shared.criteria.Operator/2483661797",
                "com.entrinsik.gwt.data.shared.projections.AliasedProjection/79816854",
                "ROW_COUNT",
                "com.entrinsik.gwt.data.shared.projections.RowCountProjection/1174077417",
                "en_US",
                "com.entrinsik.gwt.data.shared.Order/1651361273",
            ],
            refs=[
                1,
                2,
                3,
                4,
                2,
                5,
                6,
                5,
                7,
                6,
                8,
                0,
                0,
                0,
                9,
                10,
                11,
                0,
                12,
                8,
                -1,
                11,
                0,
                11,
                0,
                -1,
                11,
                0,
                13,
                14,
                15,
                0,
                0,
                0,
                10,
                16,
                11,
                1,
                17,
                0,
                14,
                1,
                0,
                0,
                0,
                0,
            ],
        )

        resp = self._send_rpc("view", payload)
        parsed = parse_gwt_response(resp)

        # The row count appears as a numeric value in the data
        for val in parsed["data"]:
            if isinstance(val, (int, float)) and val > 0:
                count = int(val)
                if count > 1:  # Skip small values that are likely metadata
                    log.info(f"  Total rows: {count:,}")
                    return count

        return 0

    def try_export_csv(self, view_token: str) -> bytes | None:
        """Try known Informer export URL patterns to download CSV directly.

        This is the fastest extraction method if the export servlet exists.
        """
        export_patterns = [
            f"{INFORMER_BASE}{INFORMER_PATH}/export/csv?viewToken={view_token}",
            f"{INFORMER_BASE}{INFORMER_PATH}/export/{view_token}?format=csv",
            f"{INFORMER_BASE}{INFORMER_PATH}/protected/export?viewToken={view_token}&type=csv",
            f"{INFORMER_BASE}{INFORMER_PATH}/servlet/ExportServlet?viewToken={view_token}&format=csv",
            f"{INFORMER_BASE}{INFORMER_PATH}/view/export?viewToken={view_token}&format=csv",
            f"{INFORMER_BASE}/eaglesign/export?viewToken={view_token}&format=csv",
        ]

        params = {}
        if self.auth_token:
            params = {"authToken": self.auth_token, "clientId": self.client_id}

        for url in export_patterns:
            try:
                resp = self.session.get(
                    url,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                    allow_redirects=True,
                )
                content_type = resp.headers.get("Content-Type", "")

                if resp.status_code == 200 and (
                    "csv" in content_type
                    or "octet-stream" in content_type
                    or "text/plain" in content_type
                ):
                    if len(resp.content) > 100:  # Non-trivial response
                        log.info(f"  Export URL found: {url}")
                        return resp.content
            except Exception:
                continue

        return None


# ---------------------------------------------------------------------------
# Report Payload Templates (from captured GWT RPC traffic)
# ---------------------------------------------------------------------------


def load_captured_payload(report_id: int) -> tuple[str, str] | None:
    """Load a captured GWT RPC payload from the captures directory.

    Prefers ViewRPCService payloads (``_view_request.txt``) over commandService
    payloads (``_cmd_request.txt``). Returns a tuple of (payload_text, payload_type)
    where payload_type is ``"view"`` or ``"command"``.

    Returns:
        Tuple of (payload_text, payload_type), or None if no payload found.
    """
    captures_dir = Path(r"C:\Scripts\keyedin-capture\reports")
    if not captures_dir.is_dir():
        return None

    for r in REPORTS:
        if r["id"] == report_id:
            slug = re.sub(r"[^\w\s-]", "", r["name"]).strip().replace(" ", "_").lower()
            # Prefer ViewRPCService payload (from browser capture).
            view_path = captures_dir / f"report_{slug}_view_request.txt"
            if view_path.exists():
                return view_path.read_text(encoding="utf-8"), "view"
            # Fall back to commandService payload.
            cmd_path = captures_dir / f"report_{slug}_cmd_request.txt"
            if cmd_path.exists():
                return cmd_path.read_text(encoding="utf-8"), "command"
            break

    return None


def update_payload_auth(
    payload: str,
    old_auth_token: str,
    new_auth_token: str,
    old_client_id: str,
    new_client_id: str,
) -> str:
    """Replace old auth tokens in a captured payload with fresh ones."""
    updated = payload.replace(old_auth_token, new_auth_token)
    updated = updated.replace(old_client_id, new_client_id)
    return updated


# ---------------------------------------------------------------------------
# Main Extraction Logic
# ---------------------------------------------------------------------------


def load_session_file(client: InformerClient) -> bool:
    """Fast-auth: load saved session from informer_session.json.

    Returns True if the session file exists and credentials were loaded.
    This skips the full ERP login / SSO dance.
    """
    if not SESSION_FILE.exists():
        log.info("No session file at %s", SESSION_FILE)
        return False

    try:
        data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Could not read session file: %s", exc)
        return False

    jsessionid = data.get("jsessionid")
    auth_token = data.get("auth_token")
    client_id = data.get("client_id")

    if not jsessionid or not auth_token:
        log.warning("Session file missing jsessionid or auth_token")
        return False

    client.session.cookies.set("JSESSIONID", jsessionid)
    client.jsessionid = jsessionid
    client.auth_token = auth_token
    client.client_id = client_id or ""

    log.info("Loaded session from %s", SESSION_FILE)
    log.info("  jsessionid : %s...", jsessionid[:20])
    log.info("  auth_token : %s...", auth_token[:20])
    log.info("  client_id  : %s...", (client_id or "")[:20])
    return True


def load_getdata_template() -> str | None:
    """Load the captured getData GWT payload template.

    Returns the raw pipe-delimited payload string, or None if the file
    is missing.
    """
    if not GETDATA_TEMPLATE_FILE.exists():
        log.warning("getData template not found: %s", GETDATA_TEMPLATE_FILE)
        return None

    template = GETDATA_TEMPLATE_FILE.read_text(encoding="utf-8").strip()
    log.info("Loaded getData template (%d chars)", len(template))
    return template


def prepare_getdata_payload(
    template: str,
    auth_token: str,
    client_id: str,
    view_token: str,
    offset: int,
) -> str:
    """Prepare a getData payload from the captured template.

    Replaces the old captured auth/view tokens and sets the pagination
    offset (the second-to-last pipe field).

    Args:
        template: Raw captured getData payload.
        auth_token: Fresh auth token.
        client_id: Fresh client ID (unused in getData URL but kept for consistency).
        view_token: Fresh ViewToken from RunReportCommand response.
        offset: Row offset for pagination (0, 25, 50, ...).

    Returns:
        Ready-to-send payload string.
    """
    payload = template

    # Replace captured ViewToken with fresh one
    payload = payload.replace(CAPTURED_VIEW_TOKEN, view_token)

    # Replace the offset: it is the SECOND-TO-LAST pipe-delimited value.
    # The template has |25| (page 2 offset) near the end; we replace it.
    # Split on pipe, set second-to-last numeric value.
    parts = payload.split("|")

    # Walk backwards to find the second-to-last integer field.
    # Pattern at tail: ...|<offset>|<trailing>|
    # The last element is empty (trailing pipe), second-to-last is a small
    # int (the trailing flags), third-to-last is the offset.
    # From the captured template the tail looks like:
    #   ...|145|25|0|  (where 25 is the offset, 0 is ordering flag)
    # Actually examining the template more carefully, the offset is encoded
    # as part of the LoadOptions refs section.  Let's find it by scanning
    # from the end for the value "25" (the captured offset).
    #
    # More robust: find the captured offset value "25" near the end.
    # The getData LoadOptions encodes offset as the second-to-last ref
    # before the trailing zeros.

    # Strategy: the captured template has offset=25 (page 2).
    # The offset appears near the end of the refs section.
    # We need to find and replace it.  Since the template is for page 2,
    # the offset "25" appears as a pipe field near the end.

    # Find from the right: skip empty trailing, then look for "25"
    # which is the captured page-2 offset.
    found_offset = False
    for i in range(len(parts) - 1, -1, -1):
        if parts[i].strip() == "25":
            # Verify it's in the refs section (index > string table count)
            # The string table count is parts[2] in GWT v7 format
            try:
                str_count = int(parts[2])
                # Refs start at index 3 + str_count
                refs_start = 3 + str_count
                if i >= refs_start:
                    parts[i] = str(offset)
                    found_offset = True
                    break
            except (ValueError, IndexError):
                pass

    if not found_offset:
        log.warning("Could not locate offset field in getData template")

    return "|".join(parts)


def authenticate(client: InformerClient, username: str, password: str) -> bool:
    """Full authentication flow: session file → ERP login → SSO → Informer."""

    # Method 0 (fast path): Load saved session from informer_session.json
    if load_session_file(client):
        # Refresh the auth token via getActiveSession (tokens are per-session)
        if client.get_active_session():
            log.info("Session file loaded + auth token refreshed")
            return True
        else:
            log.warning("Session file loaded but getActiveSession failed (expired?)")
            # Clear stale credentials so we fall through to full login
            client.auth_token = None
            client.client_id = None

    # Method 1: Login to ERP, find SSO link, follow to Informer
    if client.login_erp(username, password):
        sso_url = client.discover_sso_url()
        if sso_url:
            if client.sso_to_informer(sso_url):
                if client.get_active_session():
                    return True
                log.warning("SSO succeeded but no active session")

    # Method 2: Direct Informer login (if Informer has separate auth)
    log.info("Trying direct Informer authentication...")
    if client.login_informer_direct(username, password):
        return True

    # Method 3: Manual JSESSIONID from environment
    manual_jsessionid = os.environ.get("INFORMER_JSESSIONID")
    manual_auth = os.environ.get("INFORMER_AUTH_TOKEN")
    manual_client = os.environ.get("INFORMER_CLIENT_ID")

    if manual_jsessionid and manual_auth:
        log.info("Using manual session credentials from environment...")
        client.session.cookies.set("JSESSIONID", manual_jsessionid)
        client.jsessionid = manual_jsessionid
        client.auth_token = manual_auth
        client.client_id = manual_client or ""
        return True

    log.error(
        "All authentication methods failed.\n"
        "Set these env vars for manual auth:\n"
        "  INFORMER_JSESSIONID=<from browser>\n"
        "  INFORMER_AUTH_TOKEN=<from browser>\n"
        "  INFORMER_CLIENT_ID=<from browser>"
    )
    return False


def extract_report(
    client: InformerClient,
    report: dict,
    output_dir: Path,
) -> dict:
    """Extract a single report to CSV.

    Returns extraction result dict.
    """
    report_id = report["id"]
    report_name = report["name"]
    safe_name = re.sub(r"[^\w\s-]", "", report_name).strip().replace(" ", "_").lower()
    csv_path = output_dir / f"informer_{safe_name}.csv"

    result = {
        "report_id": report_id,
        "report_name": report_name,
        "status": "PENDING",
        "csv_path": str(csv_path),
        "row_count": 0,
        "elapsed": 0,
    }

    start = time.time()
    log.info(f"\n{'='*60}")
    log.info(f"Extracting: {report_name} (ID: {report_id})")

    # Resolve field names for this report (3-tier fallback)
    field_names = REPORT_FIELDS.get(report_id)
    fields_source = "REPORT_FIELDS" if field_names else None

    if not field_names:
        # Tier 2: Try manifest file saved by capture_all_reports.py
        manifest_path = Path(
            r"C:\Scripts\keyedin-capture\reports\field_names_manifest.json"
        )
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                field_names = manifest.get(str(report_id))
                if field_names:
                    fields_source = "manifest"
                    log.info("  Field names loaded from manifest (%d fields)", len(field_names))
            except (json.JSONDecodeError, OSError) as exc:
                log.debug("  Could not read manifest: %s", exc)

    # Tier 3 (auto-discovery) deferred until after RunReportCommand response
    auto_discover = field_names is None
    if auto_discover:
        log.info("  No pre-configured fields -- will auto-discover from response")

    try:
        # Check for captured payload (prefers ViewRPCService over commandService).
        loaded = load_captured_payload(report_id)

        if not loaded:
            result["status"] = "NO_PAYLOAD"
            result["elapsed"] = round(time.time() - start, 1)
            log.warning(
                f"  No captured payload for report {report_id}. "
                "Run capture_all_reports.py first."
            )
            return result

        payload, payload_type = loaded
        log.info("  Using captured %s payload", payload_type)

        # Update auth tokens in captured payload.
        if client.auth_token:
            payload = update_payload_auth(
                payload,
                CAPTURED_AUTH_TOKEN,
                client.auth_token,
                CAPTURED_CLIENT_ID,
                client.client_id or "",
            )

        # Execute the report via the appropriate endpoint.
        if payload_type == "view":
            resp_text, _ = client.replay_view_rpc(payload)
        else:
            resp_text, _ = client.run_report_command(payload)

        # Tier 3: Auto-discover field names from response if needed
        if auto_discover:
            field_names = gwt_discover_field_names(resp_text)
            if field_names:
                fields_source = "auto-discovery"
                log.info(
                    "  Auto-discovered %d fields: %s", len(field_names), field_names
                )
            else:
                result["status"] = "NO_FIELDS"
                result["elapsed"] = round(time.time() - start, 1)
                log.warning("  Auto-discovery found no fields in response")
                return result

        log.info("  Fields source: %s (%d fields)", fields_source, len(field_names))

        # Extract ViewToken and total count using gwt_parser
        view_token = gwt_extract_view_token(resp_text)
        total_count = gwt_extract_total_count(resp_text)

        if not view_token:
            result["status"] = "NO_VIEWTOKEN"
            result["elapsed"] = round(time.time() - start, 1)
            log.error("  No ViewToken found in RunReportCommand response")
            return result

        log.info(f"  ViewToken: {view_token}")
        log.info(f"  Total rows: {total_count:,}")

        # Extract first page (embedded in RunReportCommand response)
        first_page_rows = gwt_extract_rows(resp_text, field_names)
        log.info(f"  Page 1: {len(first_page_rows)} rows from RunReportCommand")

        all_rows: list[dict] = list(first_page_rows)

        # Paginate remaining pages using getData template
        if total_count > len(first_page_rows):
            more_rows = _paginate_report(
                client, view_token, total_count, field_names, len(first_page_rows)
            )
            all_rows.extend(more_rows)

        if all_rows:
            _write_csv(csv_path, all_rows)
            result["row_count"] = len(all_rows)
            result["status"] = "OK"
            log.info(f"  Total extracted: {len(all_rows):,} rows")
        else:
            result["status"] = "NO_DATA"

    except GwtRpcError as e:
        result["status"] = "RPC_ERROR"
        result["error"] = str(e)
        log.error(f"  GWT RPC error: {e}")
    except GwtParseError as e:
        result["status"] = "PARSE_ERROR"
        result["error"] = str(e)
        log.error(f"  GWT parse error: {e}")
    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)
        log.error(f"  Error: {e}")

    result["elapsed"] = round(time.time() - start, 1)
    log.info(f"  Result: {result['status']} ({result['elapsed']}s)")
    return result


def _paginate_report(
    client: InformerClient,
    view_token: str,
    total_rows: int,
    field_names: list[str],
    rows_already: int = 0,
) -> list[dict]:
    """Paginate through remaining report pages using captured getData template.

    Uses the captured getData GWT payload template with token/offset
    replacement.  Each page is parsed with gwt_parser.extract_rows().

    Args:
        client: Authenticated InformerClient.
        view_token: Fresh ViewToken from RunReportCommand response.
        total_rows: Total row count from RunReportCommand response.
        field_names: Column field names for this report.
        rows_already: Number of rows already extracted from page 1.

    Returns:
        List of row dicts from pages 2..N.
    """
    template = load_getdata_template()
    if not template:
        log.warning("  No getData template -- falling back to ViewRPCService.getData")
        return _paginate_report_rpc(client, view_token, total_rows, field_names, rows_already)

    all_rows: list[dict] = []
    offset = rows_already  # Start where page 1 left off (typically 25)
    page = 1  # Page 1 was the RunReportCommand response

    while offset < total_rows:
        page += 1
        log.info(
            f"  Fetching page {page} (offset={offset}/{total_rows})..."
        )

        try:
            payload = prepare_getdata_payload(
                template,
                client.auth_token or "",
                client.client_id or "",
                view_token,
                offset,
            )

            # Send via the ViewRPCService endpoint with auth params
            url = f"{INFORMER_BASE}{RPC_ENDPOINTS['view']}"
            if client.auth_token:
                url += f"?authToken={client.auth_token}&clientId={client.client_id}"

            headers = {
                "Content-Type": "text/x-gwt-rpc; charset=UTF-8",
                "X-GWT-Permutation": GWT_PERMUTATION,
                "X-GWT-Module-Base": MODULE_BASE,
            }

            resp = client.session.post(
                url,
                data=payload.encode("utf-8"),
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )

            if resp.status_code != 200:
                log.error(f"  getData HTTP {resp.status_code} at offset {offset}")
                break

            resp_text = resp.text

            if resp_text.startswith("//EX"):
                log.error(f"  getData error at offset {offset}: {resp_text[:200]}")
                break

            # Parse rows with the gwt_parser RTL algorithm
            page_rows = gwt_extract_rows(resp_text, field_names)
            log.info(f"  Page {page}: {len(page_rows)} rows")

            if not page_rows:
                log.info(f"  No more data at offset {offset}")
                break

            all_rows.extend(page_rows)
            offset += len(page_rows)

            # Safety: stop if we got fewer rows than expected page size
            if len(page_rows) < PAGE_SIZE:
                log.info(f"  Last page (got {len(page_rows)} < {PAGE_SIZE})")
                break

        except GwtParseError as e:
            log.error(f"  Parse error at offset {offset}: {e}")
            break
        except Exception as e:
            log.error(f"  Error at offset {offset}: {e}")
            break

    return all_rows


def _paginate_report_rpc(
    client: InformerClient,
    view_token: str,
    total_rows: int,
    field_names: list[str],
    rows_already: int = 0,
) -> list[dict]:
    """Fallback pagination using ViewRPCService.getData (built payloads).

    Used when the captured getData template is not available.
    """
    all_rows: list[dict] = []
    offset = rows_already
    page = 1

    while offset < total_rows:
        page += 1
        log.info(
            f"  [RPC fallback] page {page} (offset={offset}/{total_rows})..."
        )

        try:
            resp_text = client.get_view_data(view_token, offset, PAGE_SIZE)

            page_rows = gwt_extract_rows(resp_text, field_names)
            log.info(f"  Page {page}: {len(page_rows)} rows")

            if not page_rows:
                break

            all_rows.extend(page_rows)
            offset += len(page_rows)

            if len(page_rows) < PAGE_SIZE:
                break

        except (GwtRpcError, GwtParseError) as e:
            log.error(f"  Error at offset {offset}: {e}")
            break
        except Exception as e:
            log.error(f"  Error at offset {offset}: {e}")
            break

    return all_rows


def _write_csv(path: Path, rows: list[dict]) -> None:
    """Write rows to CSV file."""
    if not rows:
        return

    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    log.info(f"  Wrote {len(rows):,} rows to {path}")


# ---------------------------------------------------------------------------
# Capture Helper — for reports without saved payloads
# ---------------------------------------------------------------------------


def capture_report_payloads_guide():
    """Print instructions for capturing GWT RPC payloads for all 30 reports."""
    print(
        """
=== Report Payload Capture Guide ===

To extract reports without captured payloads, we need to record the
GWT RPC RunReportCommand payload for each report. This is a one-time
capture process.

Option A: Browser DevTools (manual)
  1. Open Chrome DevTools (F12) → Network tab
  2. Navigate to Informer
  3. Click on each report → Run
  4. Filter network requests by "commandService"
  5. Copy the request payload → save to:
     C:\\Scripts\\keyedin-capture\\reports\\report_{name}_cmd_request.txt

Option B: Automated capture script (recommended)
  Run: python capture_report_payloads.py
  This uses Playwright to login, navigate to each report, trigger Run,
  and capture the GWT RPC payload via CDP network interception.

Option C: Use INFORMER_JSESSIONID env var (fast, session-based)
  1. Login to Informer in your browser
  2. Open DevTools → Application → Cookies → JSESSIONID
  3. Also get authToken and clientId from any network request URL
  4. Set environment variables:
     set INFORMER_JSESSIONID=<value>
     set INFORMER_AUTH_TOKEN=<value>
     set INFORMER_CLIENT_ID=<value>
  5. Re-run this script
"""
    )


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract Informer BI reports via HTTP GWT RPC"
    )
    parser.add_argument(
        "--report", type=int, help="Extract single report by ID"
    )
    parser.add_argument(
        "--list", action="store_true", help="List all available reports"
    )
    parser.add_argument(
        "--guide", action="store_true", help="Show payload capture guide"
    )
    parser.add_argument(
        "--test-auth", action="store_true", help="Test authentication only"
    )
    args = parser.parse_args()

    if args.guide:
        capture_report_payloads_guide()
        return

    if args.list:
        print(f"\n{'ID':>10}  {'Name':<45}  {'Tag'}")
        print("-" * 75)
        for r in REPORTS:
            print(f"{r['id']:>10}  {r['name']:<45}  {r['tag']}")
        print(f"\nTotal: {len(REPORTS)} reports")
        return

    # Load credentials
    load_dotenv(ENV_FILE)
    username = os.environ.get("KEYEDIN_USERNAME")
    password = os.environ.get("KEYEDIN_PASSWORD")

    if not username or not password:
        log.error(f"Missing credentials. Set KEYEDIN_USERNAME and KEYEDIN_PASSWORD in {ENV_FILE}")
        sys.exit(1)

    # Suppress SSL warnings for self-signed cert
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Create output directory
    timestamp = datetime.now().strftime("%Y-%m-%dT%H%M")
    output_dir = OUTPUT_DIR / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize client
    client = InformerClient()

    # Authenticate
    log.info("=" * 60)
    log.info("PHASE 2: Informer BI Report Extraction")
    log.info("=" * 60)

    if not authenticate(client, username, password):
        log.error("Authentication failed. Exiting.")
        sys.exit(1)

    if args.test_auth:
        log.info("Authentication test passed!")
        return

    # Determine which reports to extract
    if args.report:
        targets = [r for r in REPORTS if r["id"] == args.report]
        if not targets:
            log.error(f"Report {args.report} not found. Use --list to see available reports.")
            sys.exit(1)
    else:
        targets = REPORTS

    # Extract reports
    results = []
    start_time = time.time()

    for report in targets:
        result = extract_report(client, report, output_dir)
        results.append(result)

    # Write manifest
    elapsed = time.time() - start_time
    manifest = {
        "phase": "Phase 2 — Informer BI Extraction",
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "output_dir": str(output_dir),
        "reports_attempted": len(targets),
        "reports_ok": sum(1 for r in results if r["status"] == "OK"),
        "reports_failed": sum(1 for r in results if r["status"] not in ("OK", "NO_PAYLOAD")),
        "reports_no_payload": sum(1 for r in results if r["status"] == "NO_PAYLOAD"),
        "total_rows": sum(r["row_count"] for r in results),
        "results": results,
    }

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # Summary
    log.info(f"\n{'='*60}")
    log.info("EXTRACTION SUMMARY")
    log.info(f"{'='*60}")
    log.info(f"  Output: {output_dir}")
    log.info(f"  Reports attempted: {manifest['reports_attempted']}")
    log.info(f"  Reports OK: {manifest['reports_ok']}")
    log.info(f"  Reports no payload: {manifest['reports_no_payload']}")
    log.info(f"  Reports failed: {manifest['reports_failed']}")
    log.info(f"  Total rows: {manifest['total_rows']:,}")
    log.info(f"  Elapsed: {elapsed:.1f}s")

    if manifest["reports_no_payload"] > 0:
        log.info(f"\n  {manifest['reports_no_payload']} reports need captured payloads.")
        log.info("  Run: python scrape_informer.py --guide")


if __name__ == "__main__":
    main()
