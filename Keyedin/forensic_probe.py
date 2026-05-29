#!/usr/bin/env python3
"""
KeyedIn ERP — Master Forensic Probe Script
===========================================

Tests EVERY access path to KeyedIn / Informer BI before the 33-day sunset.
Results are written to ./probe_results/ as JSON + markdown.

Phases covered:
  0. Network verification (DNS, TLS, ports)
  1. REST API & Swagger doc discovery
  1b. Direct REST auth (local login, HTTP Basic, ERP form, SSO)
  2. All 30 report IDs + 16 gap IDs via REST export
  3. SecurityRPCService role query
  4. Untested RPC service enumeration
  5. authToken persistence test
  6. Full Informer report extraction via GWT-RPC (30 reports)
  7. CGI function scraping (175+ ERP functions)
  8. Nagle Signs & GraphicFX tenant probes
  9. Warehouse data integrity verification

Usage:
    # Full probe (needs credentials for auth-dependent phases):
    python forensic_probe.py --username BRADYF --password <pw>

    # Network-only (no creds needed):
    python forensic_probe.py --phase 0

    # Specific phase:
    python forensic_probe.py --phase 1 --username BRADYF --password <pw>

Environment variables (alternative to CLI args):
    KEYEDIN_USERNAME, KEYEDIN_PASSWORD
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import socket
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import urllib3

# Suppress InsecureRequestWarning for self-signed cert on :8443
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------------------------
# Configuration (no hardcoded local paths — everything relative or env-based)
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = os.environ.get(
    "PROBE_RESULTS_DIR", str(SCRIPT_DIR / "probe_results")
)
RESULTS_PATH = Path(RESULTS_DIR)

BASE_HOST = "eaglesign.keyedinsign.com"
ERP_BASE = f"https://{BASE_HOST}"
CGI_BASE = f"{ERP_BASE}/cgi-bin/mvi.exe"

INFORMER_BASE = f"https://{BASE_HOST}:8443/eaglesign"
INFORMER_URL = f"{INFORMER_BASE}/informer"
SSO_URL = f"{INFORMER_BASE}/sso"

# RPC endpoints
RPC_BASE = f"{INFORMER_URL}/rpc/protected"
RPC_SERVICES = {
    "report": f"{RPC_BASE}/ReportRPCService",
    "view": f"{RPC_BASE}/ViewRPCService",
    "command": f"{RPC_BASE}/CommandRPCService",
    "doctmpl": f"{RPC_BASE}/DocumentTemplateRPCService",
    "codefile": f"{RPC_BASE}/CodeFileRPCService",
    "security": f"{RPC_BASE}/SecurityRPCService",
    "schedule": f"{RPC_BASE}/ScheduleRPCService",
    "logging": f"{RPC_BASE}/LoggingRPCService",
}

# Known policy keys (from serialization policy files)
KNOWN_POLICY_KEYS = {
    "command": "81D82B6C6154989542DE45F20CEB3EF0",
    "doctmpl": "05E06838523AECED1434383744A449D0",
    "report": "F94C0FA52A7B058D7077BFA6B82FF792",
    "view": "327E0F303D0CA463050DC31340CFE01D",
    "auth": "51B059033C002274BD4151F7D17FC702",
}

# All 30 known report IDs
REPORT_IDS = [
    1441842, 1441843, 1441844, 1441849, 1441850, 1441851, 1441852, 1441853,
    1441854, 1441855, 1441856, 1441857, 1441859, 1441860, 1441861, 1441862,
    1441865, 1441866, 1441868, 1441869, 1441870, 1441872, 1441873, 1441874,
    1441875, 1441877, 1441878, 1441883, 1441884, 1441887,
]

# 16 gap IDs (holes in the range that may be hidden/deleted reports)
GAP_IDS = [
    1441845, 1441846, 1441847, 1441848, 1441858, 1441863, 1441864, 1441867,
    1441871, 1441876, 1441879, 1441880, 1441881, 1441882, 1441885, 1441886,
]

REPORT_NAMES = {
    1441842: "AR Invoice Details",
    1441843: "AR Invoice Listing",
    1441844: "AR Open Invoices",
    1441849: "Cash Receipts",
    1441850: "Customer Listing",
    1441851: "Customer Listing Export",
    1441852: "Customer Location Listing",
    1441853: "Customer Location Listing Export",
    1441854: "Inventory List",
    1441855: "Inventory List Export",
    1441856: "Inventory Transaction History",
    1441857: "Invoice Register",
    1441859: "Open Sales Order Backlog",
    1441860: "Open Sales Orders",
    1441861: "Open Work Orders",
    1441862: "Planned Part Activity",
    1441865: "Purchase History",
    1441866: "Purchase Order Detail",
    1441868: "Purchased Part Variance",
    1441869: "Quote Status Report",
    1441870: "Sales Cost Detail Report",
    1441872: "Sales Order Bookings By Line Date",
    1441873: "Sales Order Bookings By SO Date",
    1441874: "Sales Order Detail",
    1441875: "Sales Order Status by Customer",
    1441877: "Sales Summary by Customer",
    1441878: "Sales Summary by Product Type",
    1441883: "Vendor Listing",
    1441884: "Vendor Listing Export",
    1441887: "Work Order Listing",
}

REQUEST_TIMEOUT = 30

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("forensic_probe")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def save_json(filename: str, data: dict | list) -> Path:
    """Save JSON to results dir."""
    path = RESULTS_PATH / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    log.info("  -> Saved: %s", path)
    return path


def save_text(filename: str, content: str) -> Path:
    """Save text to results dir."""
    path = RESULTS_PATH / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    log.info("  -> Saved: %s", path)
    return path


def save_binary(filename: str, content: bytes) -> Path:
    """Save binary data to results dir."""
    path = RESULTS_PATH / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    log.info("  -> Saved: %s (%d bytes)", path, len(content))
    return path


def ts() -> str:
    """Current UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


# =========================================================================
# PHASE 0: NETWORK VERIFICATION
# =========================================================================


def phase_0_network() -> dict:
    """Verify DNS, TLS, and port connectivity — no credentials needed."""
    log.info("=" * 70)
    log.info("PHASE 0: NETWORK VERIFICATION")
    log.info("=" * 70)

    results = {"phase": 0, "name": "network_verification", "timestamp": ts()}

    # DNS
    try:
        ip = socket.gethostbyname(BASE_HOST)
        results["dns_ip"] = ip
        octets = ip.split(".")
        is_private = (
            ip.startswith("10.")
            or ip.startswith("192.168.")
            or (ip.startswith("172.") and 16 <= int(octets[1]) <= 31)
            or ip.startswith("127.")
        )
        results["is_private_ip"] = is_private
        results["dns_verdict"] = "PRIVATE" if is_private else "PUBLIC"
        log.info("  DNS: %s -> %s (%s)", BASE_HOST, ip, results["dns_verdict"])
    except socket.gaierror as exc:
        results["dns_error"] = str(exc)
        results["dns_verdict"] = "FAILED"
        log.error("  DNS FAILED: %s", exc)

    # Port checks
    for port in [80, 443, 8443]:
        try:
            sock = socket.create_connection((BASE_HOST, port), timeout=10)
            sock.close()
            results[f"port_{port}"] = "OPEN"
            log.info("  Port %d: OPEN", port)
        except Exception as exc:
            results[f"port_{port}"] = f"CLOSED ({exc})"
            log.info("  Port %d: CLOSED (%s)", port, exc)

    # TLS cert info
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=BASE_HOST) as s:
            s.settimeout(10)
            s.connect((BASE_HOST, 443))
            cert = s.getpeercert()
            results["tls_subject"] = dict(x[0] for x in cert.get("subject", []))
            results["tls_issuer"] = dict(x[0] for x in cert.get("issuer", []))
            results["tls_not_after"] = cert.get("notAfter")
            results["tls_san"] = [
                v for t, v in cert.get("subjectAltName", [])
            ]
            log.info("  TLS cert CN: %s, expires: %s",
                     results["tls_subject"].get("commonName"),
                     results["tls_not_after"])
    except Exception as exc:
        results["tls_error"] = str(exc)
        log.warning("  TLS check error: %s", exc)

    # Quick HTTP probes (no auth)
    session = requests.Session()
    session.verify = True

    try:
        r = session.get(f"{ERP_BASE}/cgi-bin/mvi.exe/LOGIN.START", timeout=15)
        results["login_page"] = {
            "status": r.status_code,
            "size": len(r.text),
            "final_url": str(r.url),
        }
        log.info("  Login page: HTTP %d, %d bytes", r.status_code, len(r.text))
    except Exception as exc:
        results["login_page"] = {"error": str(exc)}

    try:
        r = session.get(f"{INFORMER_URL}/", timeout=15, verify=False)
        results["informer_dir"] = {
            "status": r.status_code,
            "size": len(r.text),
        }
        log.info("  Informer dir: HTTP %d, %d bytes", r.status_code, len(r.text))
    except Exception as exc:
        results["informer_dir"] = {"error": str(exc)}

    # VPN verdict — derive from actual check results
    dns_failed = results.get("dns_verdict") == "FAILED"
    is_private = results.get("is_private_ip", False)
    ports_closed = any(
        "CLOSED" in results.get(f"port_{p}", "")
        for p in [443, 8443]
    )
    if dns_failed or is_private or ports_closed:
        results["vpn_required"] = True
        results["vpn_verdict"] = (
            "VPN LIKELY REQUIRED — private IP or unreachable ports detected"
        )
    else:
        results["vpn_required"] = False
        results["vpn_verdict"] = (
            "VPN NOT REQUIRED — all endpoints publicly accessible"
        )

    save_json("phase0_network.json", results)

    md = f"""# Phase 0: Network Verification

**Date:** {ts()}
**Target:** {BASE_HOST}

## DNS
- IP: `{results.get('dns_ip', 'FAILED')}`
- Private: {results.get('is_private_ip', 'N/A')}
- **Verdict: {results.get('dns_verdict', 'UNKNOWN')}**

## Ports
| Port | Status |
|------|--------|
| 80   | {results.get('port_80', 'N/A')} |
| 443  | {results.get('port_443', 'N/A')} |
| 8443 | {results.get('port_8443', 'N/A')} |

## TLS
- Subject: `{results.get('tls_subject', {}).get('commonName', 'N/A')}`
- Expires: {results.get('tls_not_after', 'N/A')}

## VPN
**{results.get('vpn_verdict', 'UNKNOWN')}**
"""
    save_text("phase0_network.md", md)
    return results


# =========================================================================
# PHASE 1: REST API & SWAGGER DISCOVERY
# =========================================================================


def phase_1_rest_api(session: requests.Session) -> dict:
    """Probe for REST API, Swagger docs, and direct auth methods."""
    log.info("=" * 70)
    log.info("PHASE 1: REST API & SWAGGER DISCOVERY")
    log.info("=" * 70)

    results = {"phase": 1, "name": "rest_api_discovery", "timestamp": ts()}

    # Swagger / API documentation endpoints
    doc_urls = [
        f"{INFORMER_BASE}/documentation",
        f"{INFORMER_BASE}/api",
        f"{INFORMER_BASE}/api/v1",
        f"{INFORMER_BASE}/api/docs",
        f"{INFORMER_BASE}/swagger",
        f"{INFORMER_BASE}/swagger-ui.html",
        f"{INFORMER_BASE}/swagger.json",
        f"{INFORMER_BASE}/v2/api-docs",
        f"{INFORMER_BASE}/v3/api-docs",
        f"{INFORMER_BASE}/rest",
        f"{INFORMER_BASE}/rest/v1",
    ]

    results["documentation_probes"] = []
    for url in doc_urls:
        try:
            r = session.get(url, timeout=15, verify=False)
            probe = {
                "url": url,
                "status": r.status_code,
                "size": len(r.text),
                "content_type": r.headers.get("Content-Type", ""),
            }
            if r.status_code == 200 and len(r.text) > 100:
                probe["has_content"] = True
                save_text(
                    f"phase1_doc_{url.split('/')[-1] or 'root'}.html",
                    r.text[:50000],
                )
            log.info("  %s -> %d (%d bytes)", url, r.status_code, len(r.text))
        except Exception as exc:
            probe = {"url": url, "error": str(exc)}
            log.warning("  %s -> ERROR: %s", url, exc)
        results["documentation_probes"].append(probe)

    # REST API endpoints to test
    api_paths = [
        "/api/datasets",
        "/api/reports",
        "/api/queries",
        "/api/login/local",
        "/api/session",
        "/api/users/current",
        "/informer/api/datasets",
        "/informer/api/reports",
    ]

    results["api_endpoint_probes"] = []
    for path in api_paths:
        url = f"{INFORMER_BASE}{path}"
        try:
            r = session.get(url, timeout=15, verify=False)
            probe = {
                "url": url,
                "status": r.status_code,
                "size": len(r.text),
                "content_type": r.headers.get("Content-Type", ""),
                "snippet": r.text[:300] if r.status_code != 404 else "",
            }
            log.info("  GET %s -> %d", path, r.status_code)
        except Exception as exc:
            probe = {"url": url, "error": str(exc)}
            log.warning("  GET %s -> ERROR: %s", path, exc)
        results["api_endpoint_probes"].append(probe)

    save_json("phase1_rest_api.json", results)
    return results


# =========================================================================
# PHASE 1b: AUTH METHODS
# =========================================================================


def phase_1b_auth(
    session: requests.Session, username: str, password: str
) -> dict:
    """Try direct REST login, HTTP Basic, and form auth."""
    log.info("=" * 70)
    log.info("PHASE 1b: AUTHENTICATION METHODS")
    log.info("=" * 70)

    results = {"phase": "1b", "name": "auth_methods", "timestamp": ts()}

    # 1. Direct REST API login (bypasses SSO)
    log.info("  Testing REST API local login...")
    try:
        r = session.post(
            f"{INFORMER_BASE}/api/login/local",
            json={"username": username, "password": password},
            timeout=15,
            verify=False,
        )
        results["rest_login"] = {
            "status": r.status_code,
            "content_type": r.headers.get("Content-Type", ""),
            "snippet": r.text[:500],
        }
        log.info("  REST login: %d — %s", r.status_code, r.text[:200])
    except Exception as exc:
        results["rest_login"] = {"error": str(exc)}
        log.warning("  REST login error: %s", exc)

    # 2. HTTP Basic auth on datasets
    log.info("  Testing HTTP Basic auth on /api/datasets...")
    try:
        r = session.get(
            f"{INFORMER_BASE}/api/datasets",
            auth=(username, password),
            timeout=15,
            verify=False,
        )
        results["basic_auth_datasets"] = {
            "status": r.status_code,
            "content_type": r.headers.get("Content-Type", ""),
            "snippet": r.text[:500],
        }
        log.info("  Basic auth datasets: %d — %s", r.status_code, r.text[:200])
    except Exception as exc:
        results["basic_auth_datasets"] = {"error": str(exc)}

    # 3. Form POST to ERP login
    log.info("  Testing ERP form login...")
    erp_session = requests.Session()
    erp_session.verify = True
    try:
        r = erp_session.post(
            f"{CGI_BASE}/LOGIN.START",
            data={
                "USERNAME": username,
                "PASSWORD": password,
                "SECURE": "TRUE",
                "btnLogin": "Login",
            },
            allow_redirects=True,
            timeout=30,
        )
        cookies = {c.name: c.value for c in erp_session.cookies}
        results["erp_form_login"] = {
            "status": r.status_code,
            "final_url": str(r.url),
            "cookies": list(cookies.keys()),
            "cookie_count": len(cookies),
            "has_dashboard": "DASHBOARD" in r.text.upper(),
        }
        log.info(
            "  ERP form login: %d, cookies=%s, dashboard=%s",
            r.status_code,
            list(cookies.keys()),
            results["erp_form_login"]["has_dashboard"],
        )

        # If ERP login worked, try SSO handoff to Informer
        if cookies:
            log.info("  Attempting SSO handoff to Informer...")
            sso_test_url = f"{SSO_URL}?u={username}"
            try:
                r2 = erp_session.get(
                    sso_test_url, timeout=15, verify=False, allow_redirects=True
                )
                informer_cookies = {
                    c.name: c.value for c in erp_session.cookies
                    if "8443" in (c.domain or "") or c.name == "JSESSIONID"
                }
                results["sso_handoff"] = {
                    "status": r2.status_code,
                    "final_url": str(r2.url),
                    "informer_cookies": list(informer_cookies.keys()),
                    "snippet": r2.text[:500],
                }
                # Look for authToken and clientId in URL or response
                auth_match = re.search(
                    r"authToken=([a-f0-9\-]+)", str(r2.url) + r2.text
                )
                client_match = re.search(
                    r"clientId=([a-f0-9\-]+)", str(r2.url) + r2.text
                )
                if auth_match:
                    results["sso_handoff"]["auth_token"] = auth_match.group(1)
                    log.info("  Got authToken: %s...", auth_match.group(1)[:20])
                if client_match:
                    results["sso_handoff"]["client_id"] = client_match.group(1)
                    log.info("  Got clientId: %s...", client_match.group(1)[:20])

                log.info(
                    "  SSO handoff: %d -> %s",
                    r2.status_code,
                    str(r2.url)[:80],
                )
            except Exception as exc:
                results["sso_handoff"] = {"error": str(exc)}

        results["_erp_session_cookies"] = cookies
    except Exception as exc:
        results["erp_form_login"] = {"error": str(exc)}
        log.warning("  ERP form login error: %s", exc)

    save_json("phase1b_auth.json", results)
    return results


# =========================================================================
# PHASE 2: REPORT ENUMERATION (REST export + GWT-RPC)
# =========================================================================


def phase_2_enumerate_reports(
    session: requests.Session, auth_token: str | None, client_id: str | None
) -> dict:
    """Test all 30 report IDs + 16 gap IDs via REST export URLs."""
    log.info("=" * 70)
    log.info("PHASE 2: REPORT ENUMERATION — %d known + %d gaps",
             len(REPORT_IDS), len(GAP_IDS))
    log.info("=" * 70)

    results = {
        "phase": 2,
        "name": "report_enumeration",
        "timestamp": ts(),
        "reports": [],
        "summary": {"accessible": 0, "denied": 0, "error": 0, "gap_found": 0},
    }

    all_ids = REPORT_IDS + GAP_IDS

    for rid in all_ids:
        is_gap = rid in GAP_IDS
        name = REPORT_NAMES.get(rid, f"GAP-{rid}")
        report_result = {
            "id": rid,
            "name": name,
            "is_gap": is_gap,
            "exports": {},
        }

        # Test REST export URLs for each format
        for fmt in ["csv", "json", "xlsx"]:
            url = f"{INFORMER_URL}/export/report/{rid}/{fmt}"
            params = {}
            if auth_token and client_id:
                params["authToken"] = auth_token
                params["clientId"] = client_id

            try:
                r = session.get(
                    url,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                    verify=False,
                    stream=True,
                )
                content_type = r.headers.get("Content-Type", "")
                content_length = int(r.headers.get("Content-Length", 0))
                # Read up to 1MB
                body = r.raw.read(1024 * 1024)
                r.close()

                export_result = {
                    "status": r.status_code,
                    "content_type": content_type,
                    "size": len(body),
                    "content_length_header": content_length,
                }

                if r.status_code == 200 and len(body) > 100:
                    export_result["has_data"] = True
                    filename = f"exports/report_{rid}.{fmt}"
                    save_binary(filename, body)
                    results["summary"]["accessible"] += 1
                elif r.status_code in (401, 403):
                    export_result["has_data"] = False
                    export_result["denied"] = True
                    results["summary"]["denied"] += 1
                else:
                    export_result["has_data"] = False
                    results["summary"]["error"] += 1

                log.info(
                    "  Report %d (%s) %s: %d — %s — %d bytes",
                    rid, name[:25], fmt, r.status_code, content_type[:30],
                    len(body),
                )
            except Exception as exc:
                export_result = {"error": str(exc)}
                results["summary"]["error"] += 1
                log.warning("  Report %d %s: ERROR — %s", rid, fmt, exc)

            report_result["exports"][fmt] = export_result

        if is_gap and any(
            e.get("has_data") for e in report_result["exports"].values()
        ):
            results["summary"]["gap_found"] += 1

        results["reports"].append(report_result)
        time.sleep(0.5)  # Rate limiting

    save_json("phase2_report_enumeration.json", results)

    # Generate markdown summary
    md_lines = [
        "# Phase 2: Report Enumeration\n",
        f"**Date:** {ts()}\n",
        "## Summary",
        f"- Accessible: {results['summary']['accessible']}",
        f"- Denied: {results['summary']['denied']}",
        f"- Errors: {results['summary']['error']}",
        f"- Gap IDs with data: {results['summary']['gap_found']}\n",
        "## Detail\n",
        "| ID | Name | Gap? | CSV | JSON | XLSX |",
        "|-----|------|------|-----|------|------|",
    ]
    for rpt in results["reports"]:
        csv_s = rpt["exports"].get("csv", {}).get("status", "ERR")
        json_s = rpt["exports"].get("json", {}).get("status", "ERR")
        xlsx_s = rpt["exports"].get("xlsx", {}).get("status", "ERR")
        md_lines.append(
            f"| {rpt['id']} | {rpt['name'][:35]} | "
            f"{'YES' if rpt['is_gap'] else ''} | "
            f"{csv_s} | {json_s} | {xlsx_s} |"
        )

    save_text("phase2_report_enumeration.md", "\n".join(md_lines))
    return results


# =========================================================================
# PHASE 3: SecurityRPCService ROLE PROBE
# =========================================================================


def phase_3_security_rpc(session: requests.Session) -> dict:
    """Query SecurityRPCService to determine current user role."""
    log.info("=" * 70)
    log.info("PHASE 3: SecurityRPCService ROLE PROBE")
    log.info("=" * 70)

    results = {"phase": 3, "name": "security_rpc", "timestamp": ts()}

    # First, try to find the policy key by checking the .gwt.rpc files
    policy_files_url = f"{INFORMER_URL}/"
    try:
        r = session.get(policy_files_url, timeout=15, verify=False)
        # Extract all .gwt.rpc filenames
        rpc_files = re.findall(
            r'href="[^"]*?([A-F0-9]{32})\.gwt\.rpc"', r.text
        )
        results["gwt_rpc_policy_files"] = rpc_files
        log.info("  Found %d .gwt.rpc policy files", len(rpc_files))

        # Download each policy file and search for SecurityRPCService
        for pkey in rpc_files:
            try:
                pr = session.get(
                    f"{INFORMER_URL}/{pkey}.gwt.rpc",
                    timeout=15,
                    verify=False,
                )
                if "SecurityRPCService" in pr.text:
                    results["security_policy_key"] = pkey
                    results["security_policy_content"] = pr.text[:2000]
                    log.info("  SecurityRPCService found in policy: %s", pkey)
                    save_text(f"phase3_security_policy_{pkey}.txt", pr.text)
                    break
            except Exception:
                continue
    except Exception as exc:
        results["policy_discovery_error"] = str(exc)

    # Also probe the RPC endpoint directly
    for service_name, url in RPC_SERVICES.items():
        try:
            r = session.get(url, timeout=10, verify=False)
            results[f"rpc_{service_name}_get"] = {
                "status": r.status_code,
                "size": len(r.text),
                "snippet": r.text[:300],
            }
            log.info("  GET %s: %d (%d bytes)", service_name, r.status_code, len(r.text))
        except Exception as exc:
            results[f"rpc_{service_name}_get"] = {"error": str(exc)}
            log.warning("  GET %s: ERROR %s", service_name, exc)

    save_json("phase3_security_rpc.json", results)
    return results


# =========================================================================
# PHASE 4: UNTESTED RPC SERVICE ENUMERATION
# =========================================================================


def phase_4_rpc_services(session: requests.Session) -> dict:
    """Discover method signatures for all 6+ RPC services from cache.js."""
    log.info("=" * 70)
    log.info("PHASE 4: RPC SERVICE ENUMERATION")
    log.info("=" * 70)

    results = {"phase": 4, "name": "rpc_enumeration", "timestamp": ts()}

    # Find the main cache.js (the large ~5MB GWT permutation file)
    try:
        r = session.get(f"{INFORMER_URL}/", timeout=15, verify=False)
        cache_files = re.findall(
            r'href="[^"]*?([A-F0-9]{32})\.cache\.js"', r.text
        )
        results["cache_js_files"] = cache_files
        log.info("  Found %d cache.js files", len(cache_files))

        # Download the largest cache.js file (the main GWT permutation)
        if cache_files:
            # Pick first — they're all roughly the same size
            cache_key = cache_files[0]
            log.info("  Downloading %s.cache.js (this may take a moment)...", cache_key)
            r = session.get(
                f"{INFORMER_URL}/{cache_key}.cache.js",
                timeout=120,
                verify=False,
            )
            cache_content = r.text
            results["cache_js_size"] = len(cache_content)
            log.info("  Downloaded: %d bytes", len(cache_content))

            # Search for RPC service references
            service_names = [
                "SecurityRPCService",
                "CommandRPCService",
                "CodeFileRPCService",
                "ScheduleRPCService",
                "LoggingRPCService",
                "DocumentTemplateRPCService",
                "ReportRPCService",
                "ViewRPCService",
            ]

            results["service_references"] = {}
            for svc in service_names:
                # Find all method signatures near this service name
                occurrences = [
                    m.start() for m in re.finditer(re.escape(svc), cache_content)
                ]
                # Extract context around each occurrence
                contexts = []
                for pos in occurrences[:5]:
                    start = max(0, pos - 200)
                    end = min(len(cache_content), pos + 200)
                    contexts.append(cache_content[start:end])

                # Search for method names near service references
                method_pattern = rf'(?:"{svc}"[^"]*?"(\w+)")'
                methods = re.findall(method_pattern, cache_content)

                results["service_references"][svc] = {
                    "occurrence_count": len(occurrences),
                    "methods_found": list(set(methods))[:20],
                    "context_samples": contexts[:3],
                }
                log.info(
                    "  %s: %d occurrences, methods=%s",
                    svc, len(occurrences),
                    list(set(methods))[:10],
                )

            # Save a trimmed version of cache.js for reference
            save_text("phase4_cache_js_first_10k.txt", cache_content[:10000])
    except Exception as exc:
        results["cache_discovery_error"] = str(exc)
        log.error("  Cache discovery error: %s", exc)

    save_json("phase4_rpc_services.json", results)
    return results


# =========================================================================
# PHASE 5: authToken PERSISTENCE TEST
# =========================================================================


def phase_5_token_persistence(
    session: requests.Session,
    auth_token: str | None,
    client_id: str | None,
) -> dict:
    """Test whether authToken persists beyond the assumed 1-hour expiry."""
    log.info("=" * 70)
    log.info("PHASE 5: authToken PERSISTENCE")
    log.info("=" * 70)

    results = {"phase": 5, "name": "token_persistence", "timestamp": ts()}

    if not auth_token or not client_id:
        results["skipped"] = True
        results["reason"] = "No auth token available — run with credentials first"
        log.info("  SKIPPED — no auth token available")
        save_json("phase5_token_persistence.json", results)
        return results

    # Record the token and test it now
    results["token_recorded"] = {
        "auth_token": auth_token[:20] + "...",
        "client_id": client_id[:20] + "...",
        "recorded_at": ts(),
    }

    # Test with a known report
    test_url = f"{INFORMER_URL}/export/report/1441869/csv"
    try:
        r = session.get(
            test_url,
            params={"authToken": auth_token, "clientId": client_id},
            timeout=30,
            verify=False,
        )
        results["initial_test"] = {
            "status": r.status_code,
            "size": len(r.content),
            "works": r.status_code == 200 and len(r.content) > 100,
        }
        log.info("  Initial token test: %d (%d bytes)", r.status_code, len(r.content))
    except Exception as exc:
        results["initial_test"] = {"error": str(exc)}

    results["instruction"] = (
        "To test persistence: save this token, wait 2+ hours, "
        "then re-run: python forensic_probe.py --phase 5 "
        f"--token {auth_token} --client-id {client_id}"
    )

    save_json("phase5_token_persistence.json", results)
    return results


# =========================================================================
# GWT-RPC AUTHENTICATION HELPER
# =========================================================================


GWT_HEADERS = {
    "Content-Type": "text/x-gwt-rpc; charset=utf-8",
    "X-GWT-Permutation": "02039603C43E026297DD31EE646FCF8D",
}


def _build_gwt_payload(strings: list[str], refs: list[int]) -> str:
    """Build a GWT-RPC serialized payload."""
    parts = ["7", "0", str(len(strings))]
    # GWT-RPC escapes: \ -> \\, | -> \!
    parts.extend(s.replace("\\", "\\\\").replace("|", "\\!") for s in strings)
    parts.extend(str(r) for r in refs)
    return "|".join(parts) + "|"


def gwt_rpc_authenticate(
    session: requests.Session, username: str, password: str
) -> tuple[str, str]:
    """Full GWT-RPC authentication flow: ERP login → SSO → Informer login.

    Returns (auth_token, client_id).
    Raises RuntimeError on failure.
    """
    module_base = f"{INFORMER_URL}/"

    # Step 1: ERP login
    session.get(f"{ERP_BASE}/", timeout=30)
    session.post(
        f"{CGI_BASE}/LOGIN.START",
        data={"USERNAME": username, "PASSWORD": password, "SECURE": "TRUE"},
        allow_redirects=True,
        timeout=30,
    )

    # Step 2: SSO handoff
    session.get(
        f"{SSO_URL}?u={username}",
        timeout=30,
        verify=False,
        allow_redirects=True,
    )

    # Step 3: GWT-RPC login (password FIRST, then username)
    headers = {**GWT_HEADERS, "X-GWT-Module-Base": module_base}
    login_payload = _build_gwt_payload(
        strings=[
            module_base,
            KNOWN_POLICY_KEYS["auth"],
            "com.entrinsik.informer.core.client.service.AuthenticationRPCService",
            "login",
            "com.entrinsik.informer.core.domain.security.InformerAuthentication",
            "com.entrinsik.informer.core.domain.security."
            "UsernamePasswordAuthentication/2411241149",
            "Z",
            password,
            username.upper(),
        ],
        refs=[1, 2, 3, 4, 2, 5, 7, 6, 8, 9, 0],
    )

    r = session.post(
        f"{INFORMER_URL}/rpc/AuthenticationRPCService",
        data=login_payload,
        headers=headers,
        timeout=30,
        verify=False,
    )
    if not r.text.startswith("//OK"):
        raise RuntimeError(f"GWT-RPC login failed: {r.text[:200]}")

    all_strs = re.findall(r'"([^"]*)"', r.text)
    uuids = [
        s for s in all_strs
        if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-", s)
    ]
    if len(uuids) < 3:
        raise RuntimeError(f"Login response had {len(uuids)} UUIDs, expected ≥3")

    auth_token = uuids[-1]
    client_id = uuids[1]
    log.info("  GWT-RPC auth OK: token=%s...", auth_token[:12])
    return auth_token, client_id


# =========================================================================
# PHASE 6: FULL INFORMER REPORT EXTRACTION (GWT-RPC)
# =========================================================================


def phase_6_report_extraction(
    session: requests.Session,
    auth_token: str | None,
    client_id: str | None,
) -> dict:
    """Extract all 30 report metadata + sample data via GWT-RPC."""
    log.info("=" * 70)
    log.info("PHASE 6: REPORT DATA EXTRACTION (GWT-RPC)")
    log.info("=" * 70)

    results = {
        "phase": 6,
        "name": "report_extraction",
        "timestamp": ts(),
        "reports": {},
    }

    if not auth_token or not client_id:
        results["skipped"] = True
        results["reason"] = "No auth token — run with credentials"
        log.info("  SKIPPED — no auth token")
        save_json("phase6_extraction.json", results)
        return results

    module_base = f"{INFORMER_URL}/"
    headers = {**GWT_HEADERS, "X-GWT-Module-Base": module_base}
    rpc_url = (
        f"{INFORMER_URL}/rpc/protected/ReportRPCService"
        f"?authToken={auth_token}&clientId={client_id}"
    )

    reports_dir = RESULTS_PATH / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    csv_dir = RESULTS_PATH / "extracted_csv"
    csv_dir.mkdir(parents=True, exist_ok=True)

    ok_count = 0
    for i, rid in enumerate(REPORT_IDS):
        payload = _build_gwt_payload(
            strings=[
                module_base,
                KNOWN_POLICY_KEYS["report"],
                "com.entrinsik.informer.core.client.service.ReportRPCService",
                "lookupReportAndSample",
                "I",
                "Z",
                "Z",
            ],
            refs=[1, 2, 3, 4, 3, 5, 6, 7, rid, 1, 1],
        )

        try:
            r = session.post(
                rpc_url, data=payload, headers=headers, timeout=60, verify=False
            )
            r.close()
        except Exception as exc:
            results["reports"][str(rid)] = {"status": "ERROR", "error": str(exc)}
            log.warning("  [%d/30] %d: ERROR — %s", i + 1, rid, exc)
            continue

        if r.text.startswith("//OK"):
            # Save raw response
            raw_path = reports_dir / f"report_{rid}_raw.txt"
            raw_path.write_text(r.text, encoding="utf-8")

            # Parse string table
            rstrings = re.findall(r'"([^"]*)"', r.text)

            # Extract column names (UPPER_CASE with dots, 2-25 chars)
            skip = {
                "BRADYF", "ADMIN", "ACCOUNTING", "MANAGEMENT",
                "EVERYONE", "LLC", "ALL", "OPEN", "CLOSED",
            }
            columns = [
                s for s in rstrings
                if re.match(r"^[A-Z][A-Z0-9._]+$", s)
                and 2 <= len(s) <= 25
                and s not in skip
                and not s.startswith("com.")
            ]

            # Parse data values for numeric content
            data_section = r.text[4:]
            str_start = data_section.rfind(",[")
            if str_start > 0:
                raw_vals = data_section[:str_start].strip("[]").split(",")
                numerics = []
                for v in raw_vals:
                    v = v.strip()
                    try:
                        fv = float(v)
                        if fv != 0 and abs(fv) < 1e9:
                            numerics.append(fv)
                    except ValueError:
                        pass
            else:
                numerics = []

            results["reports"][str(rid)] = {
                "status": "OK",
                "size": len(r.text),
                "num_strings": len(rstrings),
                "columns": columns[:20],
                "numeric_values_count": len(numerics),
                "name": REPORT_NAMES.get(rid, "Unknown"),
            }
            ok_count += 1

            # Save extracted data
            extraction = {
                "report_id": rid,
                "name": REPORT_NAMES.get(rid, "Unknown"),
                "columns": columns,
                "numeric_sample": numerics[:100],
                "total_strings": len(rstrings),
            }
            (csv_dir / f"report_{rid}_extracted.json").write_text(
                json.dumps(extraction, indent=2), encoding="utf-8"
            )

            log.info(
                "  [%d/30] %d: OK (%d bytes, %d cols) — %s",
                i + 1, rid, len(r.text), len(columns),
                REPORT_NAMES.get(rid, "?")[:30],
            )
        else:
            error_strs = re.findall(r'"([^"]*)"', r.text)
            results["reports"][str(rid)] = {
                "status": "FAIL",
                "error": error_strs[:3] if error_strs else r.text[:200],
            }
            log.warning("  [%d/30] %d: FAIL", i + 1, rid)

        time.sleep(0.5)

    results["summary"] = {
        "total": len(REPORT_IDS),
        "ok": ok_count,
        "failed": len(REPORT_IDS) - ok_count,
    }

    save_json("phase6_extraction.json", results)
    log.info("  Phase 6 complete: %d/%d reports extracted", ok_count, len(REPORT_IDS))
    return results


# =========================================================================
# PHASE 7: CGI FUNCTION SCRAPING
# =========================================================================


def phase_7_cgi_functions(
    session: requests.Session,
    username: str | None,
    password: str | None,
) -> dict:
    """Scrape all known CGI functions from the ERP."""
    log.info("=" * 70)
    log.info("PHASE 7: CGI FUNCTION SCRAPING")
    log.info("=" * 70)

    results = {"phase": 7, "name": "cgi_functions", "timestamp": ts(), "functions": {}}

    if not username or not password:
        results["skipped"] = True
        results["reason"] = "No credentials — run with --username/--password"
        log.info("  SKIPPED — no credentials")
        save_json("phase7_cgi.json", results)
        return results

    # Login to ERP
    erp = requests.Session()
    erp.verify = False
    try:
        erp.get(f"{ERP_BASE}/", timeout=30)
        r = erp.post(
            f"{CGI_BASE}/LOGIN.START",
            data={
                "USERNAME": username,
                "PASSWORD": password,
                "SECURE": "TRUE",
                "btnLogin": "Login",
            },
            allow_redirects=True,
            timeout=30,
        )
        if len(r.text) < 5000:
            results["erp_login"] = "FAILED"
            log.warning("  ERP login failed — dashboard not returned")
            save_json("phase7_cgi.json", results)
            return results
        log.info("  ERP login OK")
    except Exception as exc:
        results["erp_login_error"] = str(exc)
        save_json("phase7_cgi.json", results)
        return results

    # Load function codes from keyedin-mcp data if available
    func_codes_file = Path(
        os.environ.get("KEYEDIN_MCP_DIR", "/home/ubuntu/keyedin-mcp")
    ) / "data" / "keyedin_complete_network_analysis.json"

    test_codes: list[dict] = []
    if func_codes_file.exists():
        try:
            with open(func_codes_file) as f:
                network = json.load(f)
            by_cat = network.get("all_functions", {}).get("by_category", {})
            for cat_name, funcs in by_cat.items():
                for func in funcs:
                    test_codes.append({
                        "code": func.get("code", ""),
                        "name": func.get("name", ""),
                        "is_bi": func.get("is_bi", False),
                        "category": cat_name,
                    })
            log.info("  Loaded %d function codes from network analysis", len(test_codes))
        except Exception as exc:
            log.warning("  Could not load function codes: %s", exc)

    if not test_codes:
        log.info("  No function codes file — using built-in set")
        for code in [
            "MY.PROFILE.MAINT", "CHANGE.PASSWORD", "REPORT.VIEW.INDEX",
            "USER.LOGOFF",
        ]:
            test_codes.append({"code": code, "name": code, "is_bi": False, "category": "BUILT_IN"})

    cgi_dir = RESULTS_PATH / "cgi_functions"
    cgi_dir.mkdir(parents=True, exist_ok=True)

    accessible = 0
    unauthorized = 0
    frontend_only = 0

    for i, func in enumerate(test_codes):
        code = func["code"]

        if code.startswith("#"):
            results["functions"][code] = {
                "status": "FRONTEND_ONLY",
                "name": func["name"],
            }
            frontend_only += 1
            continue

        url = f"{CGI_BASE}/{code}"
        try:
            r = erp.get(url, timeout=15)
            r.close()
            size = len(r.text)
            is_unauth = "NOT AUTHORIZED" in r.text.upper()
            has_content = size > 100 and not is_unauth

            if has_content:
                status = "ACCESSIBLE"
                accessible += 1
                (cgi_dir / f"{code.replace('.', '_')}.html").write_text(
                    r.text, encoding="utf-8"
                )
            elif is_unauth:
                status = "UNAUTHORIZED"
                unauthorized += 1
            else:
                status = "EMPTY"

            results["functions"][code] = {
                "status": status,
                "name": func["name"],
                "is_bi": func["is_bi"],
                "size": size,
            }
        except Exception as exc:
            results["functions"][code] = {
                "status": "ERROR",
                "error": str(exc),
            }

        if (i + 1) % 50 == 0:
            log.info("  [%d/%d] processed", i + 1, len(test_codes))
        time.sleep(0.3)

    results["summary"] = {
        "total": len(test_codes),
        "accessible": accessible,
        "unauthorized": unauthorized,
        "frontend_only": frontend_only,
    }

    save_json("phase7_cgi.json", results)
    log.info(
        "  Phase 7 complete: %d accessible, %d unauthorized, %d frontend-only",
        accessible, unauthorized, frontend_only,
    )
    return results


# =========================================================================
# PHASE 9: WAREHOUSE DATA INTEGRITY VERIFICATION
# =========================================================================


def phase_9_warehouse_verify() -> dict:
    """Inventory and verify existing warehouse data files."""
    log.info("=" * 70)
    log.info("PHASE 9: WAREHOUSE DATA INTEGRITY VERIFICATION")
    log.info("=" * 70)

    results = {"phase": 9, "name": "warehouse_verify", "timestamp": ts()}

    warehouse_dir = SCRIPT_DIR / "warehouse" / "warehouse"
    if not warehouse_dir.exists():
        results["skipped"] = True
        results["reason"] = f"Warehouse directory not found: {warehouse_dir}"
        log.info("  SKIPPED — warehouse directory not found")
        save_json("phase9_warehouse.json", results)
        return results

    total_size = 0
    file_count = 0
    dirs: dict[str, list[dict]] = {}

    for root, _subdirs, files in os.walk(warehouse_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, warehouse_dir)
            size = os.path.getsize(fpath)
            total_size += size
            file_count += 1

            subdir = os.path.dirname(rel) or "root"
            dirs.setdefault(subdir, []).append({
                "file": fname,
                "size": size,
                "path": rel,
            })

    results["total_size_bytes"] = total_size
    results["total_size_mb"] = round(total_size / 1024 / 1024, 1)
    results["file_count"] = file_count
    results["directory_count"] = len(dirs)
    results["directories"] = {k: len(v) for k, v in dirs.items()}

    # Check CSV file integrity
    data_files = []
    for subdir, files in dirs.items():
        for finfo in files:
            if finfo["file"].endswith((".csv", ".tsv", ".txt")):
                fpath = warehouse_dir / finfo["path"]
                try:
                    with open(fpath, encoding="utf-8", errors="replace") as fh:
                        lines = fh.readlines()
                    header = lines[0].strip() if lines else ""
                    data_files.append({
                        "file": finfo["path"],
                        "rows": len(lines) - 1,
                        "header_preview": header[:100],
                        "size": finfo["size"],
                    })
                except Exception as exc:
                    data_files.append({
                        "file": finfo["path"],
                        "error": str(exc),
                    })

    results["data_files"] = data_files
    results["data_file_count"] = len(data_files)

    log.info(
        "  Warehouse: %.1f MB, %d files, %d dirs, %d data files",
        results["total_size_mb"],
        file_count,
        len(dirs),
        len(data_files),
    )

    save_json("phase9_warehouse.json", results)
    return results


# =========================================================================
# PHASE 8: NAGLE SIGNS & GRAPHICFX TENANT PROBES
# =========================================================================


def phase_8_tenants(session: requests.Session) -> dict:
    """Probe Nagle Signs and GraphicFX tenant endpoints."""
    log.info("=" * 70)
    log.info("PHASE 8: TENANT PROBES (Nagle Signs, GraphicFX)")
    log.info("=" * 70)

    results = {"phase": 8, "name": "tenant_probes", "timestamp": ts(), "tenants": {}}

    tenant_paths = {
        "naglesigns": "Nagle Signs",
        "graphicfx": "GraphicFX",
        "eaglesign": "Eagle Sign (control)",
    }

    for tenant_path, tenant_name in tenant_paths.items():
        tenant_result = {"name": tenant_name}
        tenant_base = f"https://{BASE_HOST}:8443/{tenant_path}"

        # Informer portal
        try:
            r = session.get(
                f"{tenant_base}/informer/",
                timeout=15,
                verify=False,
            )
            tenant_result["informer"] = {
                "status": r.status_code,
                "size": len(r.text),
                "accessible": r.status_code == 200,
            }
            log.info("  %s /informer/: %d", tenant_name, r.status_code)
        except Exception as exc:
            tenant_result["informer"] = {"error": str(exc)}

        # Swagger/docs
        try:
            r = session.get(
                f"{tenant_base}/documentation",
                timeout=15,
                verify=False,
            )
            tenant_result["documentation"] = {
                "status": r.status_code,
                "size": len(r.text),
            }
            log.info("  %s /documentation: %d", tenant_name, r.status_code)
        except Exception as exc:
            tenant_result["documentation"] = {"error": str(exc)}

        # REST API login
        try:
            r = session.post(
                f"{tenant_base}/api/login/local",
                json={"username": "test", "password": "test"},
                timeout=15,
                verify=False,
            )
            tenant_result["api_login"] = {
                "status": r.status_code,
                "snippet": r.text[:300],
            }
            log.info("  %s /api/login/local: %d", tenant_name, r.status_code)
        except Exception as exc:
            tenant_result["api_login"] = {"error": str(exc)}

        # SSO endpoint
        try:
            r = session.get(
                f"{tenant_base}/sso",
                timeout=15,
                verify=False,
            )
            tenant_result["sso"] = {
                "status": r.status_code,
                "size": len(r.text),
            }
            log.info("  %s /sso: %d", tenant_name, r.status_code)
        except Exception as exc:
            tenant_result["sso"] = {"error": str(exc)}

        results["tenants"][tenant_path] = tenant_result

    save_json("phase8_tenants.json", results)
    return results


# =========================================================================
# MAIN ORCHESTRATOR
# =========================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="KeyedIn ERP Forensic Probe — test all access paths"
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("KEYEDIN_USERNAME"),
        help="KeyedIn username (or set KEYEDIN_USERNAME env var)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("KEYEDIN_PASSWORD"),
        help="KeyedIn password (or set KEYEDIN_PASSWORD env var)",
    )
    parser.add_argument(
        "--phase",
        type=int,
        default=None,
        help="Run only this phase (0-9). Default: run all.",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Existing authToken for persistence test (phase 5)",
    )
    parser.add_argument(
        "--client-id",
        default=None,
        help="Existing clientId for persistence test (phase 5)",
    )
    args = parser.parse_args()

    RESULTS_PATH.mkdir(parents=True, exist_ok=True)
    log.info("Results directory: %s", RESULTS_PATH)
    log.info("Target: %s", BASE_HOST)
    log.info("Time: %s", ts())

    # Shared session for authenticated phases
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0",
    })

    auth_token = args.token
    client_id = args.client_id
    all_results = {}

    phases_to_run = (
        [args.phase] if args.phase is not None else [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    )

    # Phase 0: Network (always safe, no creds)
    if 0 in phases_to_run:
        all_results["phase_0"] = phase_0_network()

    # Phase 1: REST API discovery (no creds needed for probe)
    if 1 in phases_to_run:
        all_results["phase_1"] = phase_1_rest_api(session)

        # Phase 1b: Auth methods (needs creds)
        if args.username and args.password:
            auth_results = phase_1b_auth(session, args.username, args.password)
            all_results["phase_1b"] = auth_results

            # Extract auth token if SSO handoff succeeded
            sso = auth_results.get("sso_handoff", {})
            if not auth_token and sso.get("auth_token"):
                auth_token = sso["auth_token"]
                client_id = sso.get("client_id")
                log.info("Acquired authToken from SSO handoff")
        else:
            log.info("  Skipping auth tests — no credentials provided")

    # Phase 2: Report enumeration
    if 2 in phases_to_run:
        all_results["phase_2"] = phase_2_enumerate_reports(
            session, auth_token, client_id
        )

    # Phase 3: SecurityRPCService
    if 3 in phases_to_run:
        all_results["phase_3"] = phase_3_security_rpc(session)

    # Phase 4: RPC service enumeration
    if 4 in phases_to_run:
        all_results["phase_4"] = phase_4_rpc_services(session)

    # Phase 5: Token persistence
    if 5 in phases_to_run:
        all_results["phase_5"] = phase_5_token_persistence(
            session, auth_token, client_id
        )

    # GWT-RPC auth for phases 6+ (if not already authenticated)
    if (
        not auth_token
        and args.username
        and args.password
        and any(p in phases_to_run for p in [6, 7])
    ):
        try:
            auth_token, client_id = gwt_rpc_authenticate(
                session, args.username, args.password
            )
        except RuntimeError as exc:
            log.error("  GWT-RPC auth failed: %s", exc)

    # Phase 6: Full report extraction (GWT-RPC)
    if 6 in phases_to_run:
        all_results["phase_6"] = phase_6_report_extraction(
            session, auth_token, client_id
        )

    # Phase 7: CGI function scraping
    if 7 in phases_to_run:
        all_results["phase_7"] = phase_7_cgi_functions(
            session, args.username, args.password
        )

    # Phase 8: Tenant probes (no creds needed for basic probing)
    if 8 in phases_to_run:
        all_results["phase_8"] = phase_8_tenants(session)

    # Phase 9: Warehouse data integrity verification
    if 9 in phases_to_run:
        all_results["phase_9"] = phase_9_warehouse_verify()

    # Save combined results
    save_json("ALL_PROBE_RESULTS.json", all_results)

    # Print summary
    log.info("=" * 70)
    log.info("PROBE COMPLETE")
    log.info("=" * 70)
    log.info("Results saved to: %s", RESULTS_PATH)

    if "phase_0" in all_results:
        net = all_results["phase_0"]
        log.info(
            "  Network: %s (IP: %s)",
            net.get("vpn_verdict", "?"),
            net.get("dns_ip", "?"),
        )

    if "phase_1" in all_results:
        docs = all_results["phase_1"].get("documentation_probes", [])
        found = [d for d in docs if d.get("status") == 200 and d.get("size", 0) > 100]
        log.info("  REST API docs found: %d endpoints responded", len(found))

    if "phase_2" in all_results:
        s = all_results["phase_2"].get("summary", {})
        log.info(
            "  Reports: %d accessible, %d denied, %d errors, %d gaps with data",
            s.get("accessible", 0),
            s.get("denied", 0),
            s.get("error", 0),
            s.get("gap_found", 0),
        )

    if "phase_6" in all_results:
        s = all_results["phase_6"].get("summary", {})
        log.info(
            "  Report extraction: %d/%d OK",
            s.get("ok", 0),
            s.get("total", 0),
        )

    if "phase_7" in all_results:
        s = all_results["phase_7"].get("summary", {})
        log.info(
            "  CGI functions: %d accessible, %d unauthorized",
            s.get("accessible", 0),
            s.get("unauthorized", 0),
        )

    if "phase_8" in all_results:
        tenants = all_results["phase_8"].get("tenants", {})
        for t, data in tenants.items():
            inf = data.get("informer", {})
            log.info(
                "  Tenant %s: informer=%s",
                t,
                inf.get("status", inf.get("error", "?")),
            )

    if "phase_9" in all_results:
        log.info(
            "  Warehouse: %.1f MB, %d files",
            all_results["phase_9"].get("total_size_mb", 0),
            all_results["phase_9"].get("file_count", 0),
        )


if __name__ == "__main__":
    main()
