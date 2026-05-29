#!/usr/bin/env python3
"""
Deep Probe: Aggressive penetration testing of KeyedIn Legacy ERP + Informer BI.

Probes BOTH systems:
  1. Informer BI (port 8443) — all 18 GWT-RPC services, getData pagination, export URLs
  2. Legacy ERP (port 443) — CGI mvi.exe functions, spooled reports, form submissions

Usage:
  python deep_probe.py [--phase informer|erp|all] [--report-id ID]
  python deep_probe.py informer   # shorthand positional
"""

import json
import os
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

USERNAME = os.environ.get("KEYEDIN_USERNAME", "")
PASSWORD = os.environ.get("KEYEDIN_PASSWORD", "")
if not USERNAME or not PASSWORD:
    raise SystemExit("Set KEYEDIN_USERNAME and KEYEDIN_PASSWORD env vars")

ERP_BASE = "https://eaglesign.keyedinsign.com"
CGI_BASE = f"{ERP_BASE}/cgi-bin/mvi.exe"
INFORMER_BASE = "https://eaglesign.keyedinsign.com:8443"
INFORMER_PATH = "/eaglesign/informer"
MODULE_BASE = f"{INFORMER_BASE}{INFORMER_PATH}/"

RESULTS_DIR = Path("probe_results/deep_probe")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# GWT-RPC config
GWT_PERM = "02039603C43E026297DD31EE646FCF8D"
GWT_HEADERS = {
    "Content-Type": "text/x-gwt-rpc; charset=utf-8",
    "X-GWT-Permutation": GWT_PERM,
    "X-GWT-Module-Base": MODULE_BASE,
}

# All 18 RPC services with policy keys
SERVICES = {
    "auth": {
        "class": "com.entrinsik.informer.core.client.service.AuthenticationRPCService",
        "policy": "51B059033C002274BD4151F7D17FC702",
        "endpoint": "rpc/AuthenticationRPCService",
        "protected": False,
    },
    "report": {
        "class": "com.entrinsik.informer.core.client.service.ReportRPCService",
        "policy": "F94C0FA52A7B058D7077BFA6B82FF792",
        "endpoint": "rpc/protected/ReportRPCService",
        "protected": True,
    },
    "view": {
        "class": "com.entrinsik.informer.core.client.service.ViewRPCService",
        "policy": "327E0F303D0CA463050DC31340CFE01D",
        "endpoint": "rpc/protected/ViewRPCService",
        "protected": True,
    },
    "security": {
        "class": "com.entrinsik.informer.core.client.service.SecurityRPCService",
        "policy": "C65EE4D91C18819AD7AD3BC5B1224438",
        "endpoint": "rpc/protected/SecurityRPCService",
        "protected": True,
    },
    "schedule": {
        "class": "com.entrinsik.informer.core.client.service.ScheduleRPCService",
        "policy": "1B46C5976B2133B0B4202A00CC724742",
        "endpoint": "rpc/protected/ScheduleRPCService",
        "protected": True,
    },
    "logging": {
        "class": "com.entrinsik.informer.core.client.service.LoggingRPCService",
        "policy": "0B87B9E873221EFE85EAEE9D30FBC349",
        "endpoint": "rpc/protected/LoggingRPCService",
        "protected": True,
    },
    "doctmpl": {
        "class": "com.entrinsik.informer.core.client.service.DocumentTemplateRPCService",
        "policy": "05E06838523AECED1434383744A449D0",
        "endpoint": "rpc/protected/DocumentTemplateRPCService",
        "protected": True,
    },
    "principal": {
        "class": "com.entrinsik.informer.core.client.service.PrincipalRPCService",
        "policy": "6EE47C6C1D250A896C07F9741167B259",
        "endpoint": "rpc/protected/PrincipalRPCService",
        "protected": True,
    },
    "metadata": {
        "class": "com.entrinsik.informer.core.client.service.MetadataRPCService",
        "policy": "99D583DE22D980C0567CF546A0E4FCD8",
        "endpoint": "rpc/protected/MetadataRPCService",
        "protected": True,
    },
    "package": {
        "class": "com.entrinsik.informer.core.client.service.PackageRPCService",
        "policy": "222AA86B02ABDE7CF2054E3823C26E85",
        "endpoint": "rpc/protected/PackageRPCService",
        "protected": True,
    },
    "sysset": {
        "class": "com.entrinsik.informer.core.client.service.SystemSettingsRPCService",
        "policy": "C752E7C47470237B76735FEDCEEB7F79",
        "endpoint": "rpc/protected/SystemSettingsRPCService",
        "protected": True,
    },
    "license": {
        "class": "com.entrinsik.informer.core.client.service.LicenseRPCService",
        "policy": "72E3F9820082D04349A0302A5FCE31C5",
        "endpoint": "rpc/protected/LicenseRPCService",
        "protected": True,
    },
    "codefile": {
        "class": "com.entrinsik.informer.core.client.service.CodeFileRPCService",
        "policy": "4E542AE70B0756378B5BA7B43B2FC97F",
        "endpoint": "rpc/protected/CodeFileRPCService",
        "protected": True,
    },
    "function": {
        "class": "com.entrinsik.informer.core.client.service.FunctionRPCService",
        "policy": "4FA74308CF2271F760C833A6DA4C9DE3",
        "endpoint": "rpc/protected/FunctionRPCService",
        "protected": True,
    },
    "conversion": {
        "class": "com.entrinsik.informer.core.client.service.ConversionRPCService",
        "policy": "CD39099BC515DBEDC5E2D0BE9DC2BAB3",
        "endpoint": "rpc/protected/ConversionRPCService",
        "protected": True,
    },
    "archive": {
        "class": "com.entrinsik.informer.core.client.service.DataArchiveRPCService",
        "policy": "BB5D7963002A1473DC3687E07A1E48C7",
        "endpoint": "rpc/protected/DataArchiveRPCService",
        "protected": True,
    },
    "formattedtmpl": {
        "class": "com.entrinsik.informer.core.client.service.FormattedTemplateRPCService",
        "policy": "19302CEC848F0D842EC762C3DCED6B3A",
        "endpoint": "rpc/protected/FormattedTemplateRPCService",
        "protected": True,
    },
    "sysprop": {
        "class": "com.entrinsik.informer.core.client.service.SystemPropertiesRPCService",
        "policy": "5B200E0F329FC7A71E8727A4B74C1D2E",
        "endpoint": "rpc/protected/SystemPropertiesRPCService",
        "protected": True,
    },
}

# All 30 report IDs
REPORT_IDS = [
    1441842, 1441843, 1441844, 1441849, 1441850, 1441851, 1441852, 1441853,
    1441854, 1441855, 1441856, 1441857, 1441859, 1441860, 1441861, 1441862,
    1441865, 1441866, 1441868, 1441869, 1441870, 1441872, 1441873, 1441874,
    1441875, 1441877, 1441878, 1441883, 1441884, 1441887,
]

# ---------------------------------------------------------------------------
# GWT-RPC helpers
# ---------------------------------------------------------------------------


def gwt_escape(s):
    """Escape backslash and pipe for GWT-RPC payloads."""
    return s.replace("\\", "\\\\").replace("|", "\\!")


def build_gwt(strings, refs):
    parts = ["7", "0", str(len(strings))]
    parts.extend(gwt_escape(s) for s in strings)
    parts.extend(str(r) for r in refs)
    return "|".join(parts) + "|"


def send_rpc(session, svc_key, payload, auth_token=None, client_id=None):
    """Send GWT-RPC and return raw text."""
    svc = SERVICES[svc_key]
    url = f"{INFORMER_BASE}{INFORMER_PATH}/{svc['endpoint']}"
    if svc["protected"] and auth_token:
        url += f"?authToken={auth_token}&clientId={client_id}"
    headers = {**GWT_HEADERS, "X-GWT-Module-Base": MODULE_BASE}
    resp = session.post(url, data=payload, headers=headers, timeout=120, verify=False)
    return resp.text


def parse_strings(text):
    """Extract all strings from a GWT response."""
    return re.findall(r'"((?:[^"\\]|\\.)*)"', text)


def parse_uuids(text):
    """Extract UUIDs from GWT response."""
    strs = parse_strings(text)
    return [s for s in strs if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-", s)]


def extract_numbers(text):
    """Extract numeric data section from //OK response."""
    if not text.startswith("//OK["):
        return []
    # Find string table
    st = text.rfind(',[\"')
    if st == -1:
        return []
    data_section = text[5:st]  # after //OK[
    nums = []
    for part in data_section.split(","):
        part = part.strip().strip("'\"")
        if not part:
            continue
        try:
            nums.append(int(part))
        except ValueError:
            try:
                nums.append(float(part))
            except ValueError:
                pass
    return nums


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def authenticate(session):
    """Full 3-step auth: ERP login → SSO → GWT-RPC login."""
    print("=== AUTHENTICATING ===")

    # Step 1: ERP
    session.get(f"{ERP_BASE}/", timeout=30, verify=False)
    r = session.post(
        f"{CGI_BASE}/LOGIN.START",
        data={"USERNAME": USERNAME, "PASSWORD": PASSWORD, "SECURE": "TRUE"},
        allow_redirects=True, timeout=30, verify=False,
    )
    if "LICENSE QUOTA" in r.text.upper():
        print("  ERROR: License quota exceeded")
        return None, None
    print(f"  ERP login: {r.status_code} (quota_warning={'QUOTA' in r.text.upper()})")

    # Step 2: SSO
    r2 = session.get(
        f"{INFORMER_BASE}/eaglesign/sso?u={USERNAME.upper()}",
        timeout=30, allow_redirects=True, verify=False,
    )
    print(f"  SSO: {r2.status_code}, JSESSIONID={session.cookies.get('JSESSIONID') is not None}")

    # Step 3: GWT-RPC login (password FIRST, then username in refs)
    payload = build_gwt(
        [MODULE_BASE, SERVICES["auth"]["policy"],
         SERVICES["auth"]["class"], "login",
         "com.entrinsik.informer.core.domain.security.InformerAuthentication",
         "com.entrinsik.informer.core.domain.security."
         "UsernamePasswordAuthentication/2411241149",
         "Z", PASSWORD, USERNAME.upper()],
        [1, 2, 3, 4, 2, 5, 7, 6, 8, 9, 0],
    )
    headers = {**GWT_HEADERS, "X-GWT-Module-Base": MODULE_BASE}
    r3 = session.post(
        f"{INFORMER_BASE}{INFORMER_PATH}/{SERVICES['auth']['endpoint']}",
        data=payload, headers=headers, timeout=30, verify=False,
    )
    if not r3.text.startswith("//OK"):
        print(f"  AUTH FAILED: {r3.text[:300]}")
        print(f"  DEBUG: Cookies={dict(session.cookies)}")
        print(f"  DEBUG: Payload len={len(payload)}, first 100={payload[:100]}")
        print(f"  DEBUG: Headers={dict(r3.request.headers)}")
        return None, None

    uuids = parse_uuids(r3.text)
    if not uuids:
        print("  AUTH FAILED: no UUIDs in response")
        return None, None
    if len(uuids) < 3:
        print(f"  WARNING: only {len(uuids)} UUIDs found")
    auth_token = uuids[-1]
    client_id = uuids[1] if len(uuids) > 1 else uuids[0]
    print(f"  AUTH OK: token={auth_token[:20]}... client={client_id[:20]}...")
    return auth_token, client_id


# ---------------------------------------------------------------------------
# INFORMER PROBES
# ---------------------------------------------------------------------------


def probe_report_lookup_and_getdata(session, auth_token, client_id, report_id):
    """lookupReportAndSample → extract ViewToken → getData for full extraction."""
    # lookupReportAndSample
    payload = build_gwt(
        [MODULE_BASE, SERVICES["report"]["policy"],
         SERVICES["report"]["class"],
         "lookupReportAndSample",
         "J",  # long type
         str(report_id)],
        [1, 2, 3, 4, 1, 5, 6, 0],
    )
    resp = send_rpc(session, "report", payload, auth_token, client_id)

    if resp.startswith("//EX"):
        return {"report_id": report_id, "status": "ERROR", "error": resp[:200]}

    strs = parse_strings(resp)
    uuids = [s for s in strs if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-", s)]

    # Find report name
    name = "unknown"
    for s in strs:
        if len(s) > 3 and not s.startswith("com.") and not s.startswith("java.") and \
           not re.match(r"^[0-9a-f]{8}-", s) and not s.startswith("rO0") and \
           " " in s and len(s) < 60:
            name = s
            break

    # Find ViewToken — typically a UUID that appears after ViewToken class ref
    view_token = None
    for i, s in enumerate(strs):
        if "ViewToken" in s:
            # Next UUID after ViewToken class reference
            for j in range(i + 1, min(i + 5, len(strs))):
                if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-", strs[j]):
                    view_token = strs[j]
                    break
            break

    if not view_token and uuids:
        # Fallback: last UUID is often the ViewToken
        view_token = uuids[-1] if len(uuids) > 0 else None

    # Extract total count from numeric data
    nums = extract_numbers(resp)
    total_count = 0
    for n in nums:
        if isinstance(n, int) and 10 < n < 1000000:
            total_count = n
            break

    result = {
        "report_id": report_id,
        "name": name,
        "status": "OK",
        "view_token": view_token,
        "total_count": total_count,
        "sample_strings": len(strs),
        "uuid_count": len(uuids),
        "response_bytes": len(resp),
    }

    # If we have a ViewToken, try getData
    if view_token:
        try:
            gd_result = probe_getdata(session, auth_token, client_id, view_token, total_count)
            result["getdata"] = gd_result
        except Exception as e:
            result["getdata_error"] = str(e)

    return result


def probe_getdata(session, auth_token, client_id, view_token, expected_total=0):
    """Call ViewRPCService.getData to pull actual row data."""
    # Request page 1 (offset=0, limit=25)
    payload = build_gwt(
        [MODULE_BASE, SERVICES["view"]["policy"],
         SERVICES["view"]["class"],
         "getData",
         "com.entrinsik.gwt.data.shared.ViewToken/3777265110",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         view_token,
         "java.util.HashMap/1797211028",
         "en_US",
         "com.entrinsik.gwt.data.shared.Order/1651361273"],
        [1, 2, 3, 4, 2, 5, 6, 5, 7, 6, 8, 0, 0, 0, 0, 25, 9, 0, 10, 0, 0, 0, 0, 0],
    )
    resp = send_rpc(session, "view", payload, auth_token, client_id)

    if resp.startswith("//EX"):
        return {"status": "ERROR", "error": resp[:300]}

    strs = parse_strings(resp)
    nums = extract_numbers(resp)

    # Try to find field names (keys from row HashMap)
    field_names = []
    for s in strs:
        if s and not s.startswith("com.") and not s.startswith("java.") and \
           not re.match(r"^[0-9a-f]{8}-", s) and not s.startswith("rO0") and \
           len(s) < 50 and s not in ("en_US",):
            field_names.append(s)

    # Extract total count from response
    total_in_resp = 0
    for n in nums:
        if isinstance(n, int) and 10 < n < 1000000:
            total_in_resp = n
            break

    # Try page 2 to verify pagination works
    page2_payload = build_gwt(
        [MODULE_BASE, SERVICES["view"]["policy"],
         SERVICES["view"]["class"],
         "getData",
         "com.entrinsik.gwt.data.shared.ViewToken/3777265110",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         view_token,
         "java.util.HashMap/1797211028",
         "en_US",
         "com.entrinsik.gwt.data.shared.Order/1651361273"],
        [1, 2, 3, 4, 2, 5, 6, 5, 7, 6, 8, 0, 0, 0, 0, 25, 9, 0, 10, 0, 0, 0, 25, 0],
    )
    resp2 = send_rpc(session, "view", page2_payload, auth_token, client_id)
    page2_ok = resp2.startswith("//OK")
    page2_strs = parse_strings(resp2) if page2_ok else []

    return {
        "status": "OK",
        "page1_bytes": len(resp),
        "page1_strings": len(strs),
        "page2_ok": page2_ok,
        "page2_bytes": len(resp2) if page2_ok else 0,
        "page2_strings": len(page2_strs),
        "total_in_response": total_in_resp,
        "field_candidates": field_names[:30],
    }


def probe_export_urls(session, auth_token, client_id, view_token, report_id):
    """Try every export URL pattern with a real ViewToken."""
    patterns = [
        f"{INFORMER_BASE}{INFORMER_PATH}/export/csv?viewToken={view_token}",
        f"{INFORMER_BASE}{INFORMER_PATH}/export/{view_token}?format=csv",
        f"{INFORMER_BASE}{INFORMER_PATH}/protected/export?viewToken={view_token}&type=csv",
        f"{INFORMER_BASE}{INFORMER_PATH}/servlet/ExportServlet?viewToken={view_token}&format=csv",
        f"{INFORMER_BASE}{INFORMER_PATH}/view/export?viewToken={view_token}&format=csv",
        f"{INFORMER_BASE}/eaglesign/export?viewToken={view_token}&format=csv",
        f"{INFORMER_BASE}{INFORMER_PATH}/export/report/{report_id}/csv?authToken={auth_token}&clientId={client_id}",
        f"{INFORMER_BASE}{INFORMER_PATH}/export/report/{report_id}/json?authToken={auth_token}&clientId={client_id}",
        f"{INFORMER_BASE}{INFORMER_PATH}/export/report/{report_id}/xlsx?authToken={auth_token}&clientId={client_id}",
        # Try the exportView RPC method via GET
        f"{INFORMER_BASE}{INFORMER_PATH}/rpc/protected/ViewRPCService/exportView?viewToken={view_token}&authToken={auth_token}&clientId={client_id}",
        # DocumentTemplate export
        f"{INFORMER_BASE}{INFORMER_PATH}/protected/download?viewToken={view_token}&type=csv",
        f"{INFORMER_BASE}{INFORMER_PATH}/protected/download?viewToken={view_token}",
        # Informer 5 standard patterns
        f"{INFORMER_BASE}{INFORMER_PATH}/api/datasets/{report_id}/export/csv",
        f"{INFORMER_BASE}{INFORMER_PATH}/api/reports/{report_id}/export/csv",
        f"{INFORMER_BASE}/eaglesign/api/datasets/{report_id}/data?start=0&limit=50",
    ]
    results = []
    for url in patterns:
        try:
            r = session.get(url, timeout=30, allow_redirects=True)
            ct = r.headers.get("Content-Type", "")
            results.append({
                "url": url.replace(auth_token, "TOKEN").replace(client_id, "CID"),
                "status": r.status_code,
                "content_type": ct,
                "size": len(r.content),
                "has_data": len(r.content) > 200 and ("csv" in ct or "octet" in ct or "json" in ct or "excel" in ct),
                "preview": r.text[:200] if r.status_code == 200 and len(r.content) < 5000 else "",
            })
        except Exception as e:
            results.append({"url": url[:80], "error": str(e)})
    return results


def probe_rpc_service(session, auth_token, client_id, svc_key, method_name, payload_strings, payload_refs):
    """Generic RPC probe — returns parsed response."""
    try:
        payload = build_gwt(payload_strings, payload_refs)
        resp = send_rpc(session, svc_key, payload, auth_token, client_id)
        status = "OK" if resp.startswith("//OK") else "ERROR"
        strs = parse_strings(resp)
        return {
            "method": method_name,
            "status": status,
            "response_bytes": len(resp),
            "string_count": len(strs),
            "strings_preview": strs[:30],
            "raw_preview": resp[:500],
        }
    except Exception as e:
        return {"method": method_name, "status": "EXCEPTION", "error": str(e)}


def probe_all_informer_services(session, auth_token, client_id):
    """Probe every interesting getter method across all 18 services."""
    results = {}

    # --- ReportRPCService ---
    print("\n=== ReportRPCService ===")
    svc = SERVICES["report"]

    # getReports (list all reports)
    r = probe_rpc_service(session, auth_token, client_id, "report", "getReports",
        [MODULE_BASE, svc["policy"], svc["class"], "getReports",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getReports"] = r
    print(f"  getReports: {r['status']} ({r['response_bytes']} bytes, {r['string_count']} strings)")

    # getTags
    r = probe_rpc_service(session, auth_token, client_id, "report", "getTags",
        [MODULE_BASE, svc["policy"], svc["class"], "getTags"],
        [1, 2, 3, 4, 0])
    results["getTags"] = r
    print(f"  getTags: {r['status']} ({r['string_count']} strings)")

    # getDashboards
    r = probe_rpc_service(session, auth_token, client_id, "report", "getDashboards",
        [MODULE_BASE, svc["policy"], svc["class"], "getDashboards",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getDashboards"] = r
    print(f"  getDashboards: {r['status']} ({r['string_count']} strings)")

    # getDynamicExportConfigs
    r = probe_rpc_service(session, auth_token, client_id, "report", "getDynamicExportConfigs",
        [MODULE_BASE, svc["policy"], svc["class"], "getDynamicExportConfigs"],
        [1, 2, 3, 4, 0])
    results["getDynamicExportConfigs"] = r
    print(f"  getDynamicExportConfigs: {r['status']} ({r['string_count']} strings)")

    # getReportResults for a known report
    r = probe_rpc_service(session, auth_token, client_id, "report", "getReportResults",
        [MODULE_BASE, svc["policy"], svc["class"], "getReportResults",
         "J", str(REPORT_IDS[0])],
        [1, 2, 3, 4, 1, 5, 6, 0])
    results["getReportResults"] = r
    print(f"  getReportResults: {r['status']} ({r['string_count']} strings)")

    # --- SecurityRPCService ---
    print("\n=== SecurityRPCService ===")
    svc = SERVICES["security"]

    # canCreateReport
    r = probe_rpc_service(session, auth_token, client_id, "security", "canCreateReport",
        [MODULE_BASE, svc["policy"], svc["class"], "canCreateReport"],
        [1, 2, 3, 4, 0])
    results["canCreateReport"] = r
    print(f"  canCreateReport: {r['status']} ({r['string_count']} strings)")

    # getSecurityAudit
    r = probe_rpc_service(session, auth_token, client_id, "security", "getSecurityAudit",
        [MODULE_BASE, svc["policy"], svc["class"], "getSecurityAudit",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getSecurityAudit"] = r
    print(f"  getSecurityAudit: {r['status']} ({r['string_count']} strings)")

    # listSecurityArchives
    r = probe_rpc_service(session, auth_token, client_id, "security", "listSecurityArchives",
        [MODULE_BASE, svc["policy"], svc["class"], "listSecurityArchives"],
        [1, 2, 3, 4, 0])
    results["listSecurityArchives"] = r
    print(f"  listSecurityArchives: {r['status']} ({r['string_count']} strings)")

    # lookupAcl for a report
    r = probe_rpc_service(session, auth_token, client_id, "security", "lookupAcl",
        [MODULE_BASE, svc["policy"], svc["class"], "lookupAcl",
         "J", str(REPORT_IDS[0])],
        [1, 2, 3, 4, 1, 5, 6, 0])
    results["lookupAcl"] = r
    print(f"  lookupAcl: {r['status']} ({r['string_count']} strings)")

    # --- PrincipalRPCService ---
    print("\n=== PrincipalRPCService ===")
    svc = SERVICES["principal"]

    # getUsers
    r = probe_rpc_service(session, auth_token, client_id, "principal", "getUsers",
        [MODULE_BASE, svc["policy"], svc["class"], "getUsers",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getUsers"] = r
    print(f"  getUsers: {r['status']} ({r['string_count']} strings)")

    # getGroups
    r = probe_rpc_service(session, auth_token, client_id, "principal", "getGroups",
        [MODULE_BASE, svc["policy"], svc["class"], "getGroups",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getGroups"] = r
    print(f"  getGroups: {r['status']} ({r['string_count']} strings)")

    # getLocalUsers
    r = probe_rpc_service(session, auth_token, client_id, "principal", "getLocalUsers",
        [MODULE_BASE, svc["policy"], svc["class"], "getLocalUsers",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getLocalUsers"] = r
    print(f"  getLocalUsers: {r['status']} ({r['string_count']} strings)")

    # getLocalGroups
    r = probe_rpc_service(session, auth_token, client_id, "principal", "getLocalGroups",
        [MODULE_BASE, svc["policy"], svc["class"], "getLocalGroups",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getLocalGroups"] = r
    print(f"  getLocalGroups: {r['status']} ({r['string_count']} strings)")

    # getRepositories (LDAP/auth sources)
    r = probe_rpc_service(session, auth_token, client_id, "principal", "getRepositories",
        [MODULE_BASE, svc["policy"], svc["class"], "getRepositories"],
        [1, 2, 3, 4, 0])
    results["getRepositories"] = r
    print(f"  getRepositories: {r['status']} ({r['string_count']} strings)")

    # getUserFields
    r = probe_rpc_service(session, auth_token, client_id, "principal", "getUserFields",
        [MODULE_BASE, svc["policy"], svc["class"], "getUserFields"],
        [1, 2, 3, 4, 0])
    results["getUserFields"] = r
    print(f"  getUserFields: {r['status']} ({r['string_count']} strings)")

    # --- MetadataRPCService ---
    print("\n=== MetadataRPCService ===")
    svc = SERVICES["metadata"]

    # getDatasources
    r = probe_rpc_service(session, auth_token, client_id, "metadata", "getDatasources",
        [MODULE_BASE, svc["policy"], svc["class"], "getDatasources",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getDatasources"] = r
    print(f"  getDatasources: {r['status']} ({r['string_count']} strings)")

    # getNamespaces
    r = probe_rpc_service(session, auth_token, client_id, "metadata", "getNamespaces",
        [MODULE_BASE, svc["policy"], svc["class"], "getNamespaces"],
        [1, 2, 3, 4, 0])
    results["getNamespaces"] = r
    print(f"  getNamespaces: {r['status']} ({r['string_count']} strings)")

    # getReportableTables
    r = probe_rpc_service(session, auth_token, client_id, "metadata", "getReportableTables",
        [MODULE_BASE, svc["policy"], svc["class"], "getReportableTables",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getReportableTables"] = r
    print(f"  getReportableTables: {r['status']} ({r['string_count']} strings)")

    # --- SystemSettingsRPCService ---
    print("\n=== SystemSettingsRPCService ===")
    svc = SERVICES["sysset"]

    # loadSystemSettings
    r = probe_rpc_service(session, auth_token, client_id, "sysset", "loadSystemSettings",
        [MODULE_BASE, svc["policy"], svc["class"], "loadSystemSettings"],
        [1, 2, 3, 4, 0])
    results["loadSystemSettings"] = r
    print(f"  loadSystemSettings: {r['status']} ({r['string_count']} strings)")

    # getTimeZones
    r = probe_rpc_service(session, auth_token, client_id, "sysset", "getTimeZones",
        [MODULE_BASE, svc["policy"], svc["class"], "getTimeZones"],
        [1, 2, 3, 4, 0])
    results["getTimeZones"] = r
    print(f"  getTimeZones: {r['status']} ({r['string_count']} strings)")

    # getFieldDefinitions
    r = probe_rpc_service(session, auth_token, client_id, "sysset", "getFieldDefinitions",
        [MODULE_BASE, svc["policy"], svc["class"], "getFieldDefinitions",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getFieldDefinitions"] = r
    print(f"  getFieldDefinitions: {r['status']} ({r['string_count']} strings)")

    # getSupportEmailAddress
    r = probe_rpc_service(session, auth_token, client_id, "sysset", "getSupportEmailAddress",
        [MODULE_BASE, svc["policy"], svc["class"], "getSupportEmailAddress"],
        [1, 2, 3, 4, 0])
    results["getSupportEmailAddress"] = r
    print(f"  getSupportEmailAddress: {r['status']} ({r['string_count']} strings)")

    # --- LicenseRPCService ---
    print("\n=== LicenseRPCService ===")
    svc = SERVICES["license"]

    # getUserStore
    r = probe_rpc_service(session, auth_token, client_id, "license", "getUserStore",
        [MODULE_BASE, svc["policy"], svc["class"], "getUserStore",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getUserStore"] = r
    print(f"  getUserStore: {r['status']} ({r['string_count']} strings)")

    # getCurrentlyLicensedUsersCount
    r = probe_rpc_service(session, auth_token, client_id, "license", "getCurrentlyLicensedUsersCount",
        [MODULE_BASE, svc["policy"], svc["class"], "getCurrentlyLicensedUsersCount"],
        [1, 2, 3, 4, 0])
    results["getCurrentlyLicensedUsersCount"] = r
    print(f"  getCurrentlyLicensedUsersCount: {r['status']} ({r['string_count']} strings)")

    # --- CodeFileRPCService ---
    print("\n=== CodeFileRPCService ===")
    svc = SERVICES["codefile"]

    # getCodeFiles
    r = probe_rpc_service(session, auth_token, client_id, "codefile", "getCodeFiles",
        [MODULE_BASE, svc["policy"], svc["class"], "getCodeFiles",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getCodeFiles"] = r
    print(f"  getCodeFiles: {r['status']} ({r['string_count']} strings)")

    # --- FunctionRPCService ---
    print("\n=== FunctionRPCService ===")
    svc = SERVICES["function"]

    # getFunctionDefinitions
    r = probe_rpc_service(session, auth_token, client_id, "function", "getFunctionDefinitions",
        [MODULE_BASE, svc["policy"], svc["class"], "getFunctionDefinitions",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getFunctionDefinitions"] = r
    print(f"  getFunctionDefinitions: {r['status']} ({r['string_count']} strings)")

    # getFunctionDescriptors
    r = probe_rpc_service(session, auth_token, client_id, "function", "getFunctionDescriptors",
        [MODULE_BASE, svc["policy"], svc["class"], "getFunctionDescriptors"],
        [1, 2, 3, 4, 0])
    results["getFunctionDescriptors"] = r
    print(f"  getFunctionDescriptors: {r['status']} ({r['string_count']} strings)")

    # --- DataArchiveRPCService ---
    print("\n=== DataArchiveRPCService ===")
    svc = SERVICES["archive"]

    # getDataArchives
    r = probe_rpc_service(session, auth_token, client_id, "archive", "getDataArchives",
        [MODULE_BASE, svc["policy"], svc["class"], "getDataArchives",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getDataArchives"] = r
    print(f"  getDataArchives: {r['status']} ({r['string_count']} strings)")

    # --- PackageRPCService ---
    print("\n=== PackageRPCService ===")
    svc = SERVICES["package"]

    # getPackages
    r = probe_rpc_service(session, auth_token, client_id, "package", "getPackages",
        [MODULE_BASE, svc["policy"], svc["class"], "getPackages",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getPackages"] = r
    print(f"  getPackages: {r['status']} ({r['string_count']} strings)")

    # --- ScheduleRPCService ---
    print("\n=== ScheduleRPCService ===")
    svc = SERVICES["schedule"]

    # getScheduledReports
    r = probe_rpc_service(session, auth_token, client_id, "schedule", "getScheduledReports",
        [MODULE_BASE, svc["policy"], svc["class"], "getScheduledReports",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getScheduledReports"] = r
    print(f"  getScheduledReports: {r['status']} ({r['string_count']} strings)")

    # getJobHistory
    r = probe_rpc_service(session, auth_token, client_id, "schedule", "getJobHistory",
        [MODULE_BASE, svc["policy"], svc["class"], "getJobHistory",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getJobHistory"] = r
    print(f"  getJobHistory: {r['status']} ({r['string_count']} strings)")

    # --- LoggingRPCService ---
    print("\n=== LoggingRPCService ===")
    svc = SERVICES["logging"]

    # viewSettings
    r = probe_rpc_service(session, auth_token, client_id, "logging", "viewSettings",
        [MODULE_BASE, svc["policy"], svc["class"], "viewSettings"],
        [1, 2, 3, 4, 0])
    results["viewSettings"] = r
    print(f"  viewSettings: {r['status']} ({r['string_count']} strings)")

    # view
    r = probe_rpc_service(session, auth_token, client_id, "logging", "view",
        [MODULE_BASE, svc["policy"], svc["class"], "view",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["view_logs"] = r
    print(f"  view: {r['status']} ({r['string_count']} strings)")

    # --- SystemPropertiesRPCService ---
    print("\n=== SystemPropertiesRPCService ===")
    svc = SERVICES["sysprop"]

    # getSystemProperties
    r = probe_rpc_service(session, auth_token, client_id, "sysprop", "getSystemProperties",
        [MODULE_BASE, svc["policy"], svc["class"], "getSystemProperties"],
        [1, 2, 3, 4, 0])
    results["getSystemProperties"] = r
    print(f"  getSystemProperties: {r['status']} ({r['string_count']} strings)")

    # --- DocumentTemplateRPCService ---
    print("\n=== DocumentTemplateRPCService ===")
    svc = SERVICES["doctmpl"]

    # getDocumentTemplatesBasic
    r = probe_rpc_service(session, auth_token, client_id, "doctmpl", "getDocumentTemplatesBasic",
        [MODULE_BASE, svc["policy"], svc["class"], "getDocumentTemplatesBasic",
         "com.entrinsik.gwt.data.shared.LoadOptions/4020437150",
         "java.util.HashMap/1797211028", "en_US",
         "java.util.ArrayList/4159755760",
         "com.entrinsik.gwt.data.shared.Order/1651361273", "name"],
        [1, 2, 3, 4, 1, 5, 5, 6, 0, 0, 0, 0, -1, 7, 8, 1, 9, 1, 10, 0, 0, 0, 0, 0])
    results["getDocumentTemplatesBasic"] = r
    print(f"  getDocumentTemplatesBasic: {r['status']} ({r['string_count']} strings)")

    # --- ViewRPCService ---
    print("\n=== ViewRPCService (extra methods) ===")
    svc = SERVICES["view"]

    # exportView — requires ViewToken, try with first report's token
    # Will be tested separately with actual ViewTokens

    # --- ConversionRPCService ---
    print("\n=== ConversionRPCService ===")
    svc = SERVICES["conversion"]

    # convert (needs specific params — probe with empty to see error)
    r = probe_rpc_service(session, auth_token, client_id, "conversion", "convert",
        [MODULE_BASE, svc["policy"], svc["class"], "convert"],
        [1, 2, 3, 4, 0])
    results["convert"] = r
    print(f"  convert: {r['status']} ({r['string_count']} strings)")

    return results


# ---------------------------------------------------------------------------
# LEGACY ERP PROBES
# ---------------------------------------------------------------------------


def probe_erp_deep(session):
    """Deep probe of the legacy KeyedIn ERP via CGI/mvi.exe."""
    results = {}

    print("\n" + "=" * 60)
    print("=== LEGACY ERP DEEP PROBE ===")
    print("=" * 60)

    # 1. Spider REPORT.VIEW.INDEX (browse spooled reports)
    print("\n--- REPORT.VIEW.INDEX ---")
    r = session.get(f"{CGI_BASE}/APPLOAD?APP=REPORT.VIEW.INDEX", timeout=30)
    results["REPORT.VIEW.INDEX"] = {
        "status": r.status_code,
        "size": len(r.text),
        "has_table": "<table" in r.text.lower() or "<TABLE" in r.text,
        "links_found": len(re.findall(r'href=["\']([^"\']*)["\']', r.text, re.I)),
        "forms_found": len(re.findall(r'<form[^>]*>', r.text, re.I)),
    }
    # Save full HTML
    (RESULTS_DIR / "report_view_index.html").write_text(r.text, encoding="utf-8")
    print(f"  Status: {r.status_code}, Size: {len(r.text)}, Tables: {results['REPORT.VIEW.INDEX']['has_table']}")

    # Extract all links from the page
    links = re.findall(r'href=["\']([^"\']*mvi\.exe[^"\']*)["\']', r.text, re.I)
    print(f"  Links to mvi.exe: {len(links)}")
    for link in links[:10]:
        print(f"    {link}")

    # 2. Try DASHBOARD
    print("\n--- DASHBOARD ---")
    r = session.get(f"{CGI_BASE}/DASHBOARD", timeout=30)
    results["DASHBOARD"] = {
        "status": r.status_code,
        "size": len(r.text),
        "links": len(re.findall(r'href=["\']([^"\']*)["\']', r.text, re.I)),
    }
    # Extract menu items and links
    dash_links = re.findall(r'href=["\']([^"\']*mvi\.exe[^"\']*)["\']', r.text, re.I)
    results["DASHBOARD"]["mvi_links"] = dash_links[:50]
    print(f"  Status: {r.status_code}, Size: {len(r.text)}, MVI links: {len(dash_links)}")
    (RESULTS_DIR / "dashboard.html").write_text(r.text, encoding="utf-8")

    # 3. Spider all unique links from dashboard
    print("\n--- SPIDERING DASHBOARD LINKS ---")
    seen_urls = set()
    accessible = []
    unauthorized = []

    # Combine links from dashboard and REPORT.VIEW.INDEX
    all_links = set(dash_links + links)
    for link in all_links:
        if link in seen_urls:
            continue
        seen_urls.add(link)
        # Normalize URL
        if link.startswith("/"):
            full_url = f"{ERP_BASE}{link}"
        elif link.startswith("http"):
            full_url = link
        else:
            full_url = f"{CGI_BASE}/{link}"
        try:
            r = session.get(full_url, timeout=15)
            is_auth = "NOT AUTHORIZED" not in r.text.upper() and "UNAUTHORIZED" not in r.text.upper()
            entry = {
                "url": full_url,
                "status": r.status_code,
                "size": len(r.text),
                "authorized": is_auth,
                "has_table": "<table" in r.text.lower(),
                "has_form": "<form" in r.text.lower(),
            }
            if is_auth and r.status_code == 200:
                accessible.append(entry)
                print(f"  ✓ ACCESSIBLE: {full_url} ({len(r.text)} bytes)")
                # Save accessible pages
                safe_name = re.sub(r'[^\w]', '_', full_url.split("mvi.exe/")[-1] if "mvi.exe/" in full_url else "page")[:50]
                (RESULTS_DIR / f"erp_{safe_name}.html").write_text(r.text, encoding="utf-8")
            else:
                unauthorized.append(entry)
        except Exception:
            pass

    results["spidering"] = {
        "total_links": len(all_links),
        "accessible": len(accessible),
        "unauthorized": len(unauthorized),
        "accessible_pages": accessible,
    }
    print(f"\n  Total: {len(all_links)} links, {len(accessible)} accessible, {len(unauthorized)} unauthorized")

    # 4. Try specific ERP functions that might expose data
    print("\n--- DIRECT ERP FUNCTION PROBES ---")
    data_functions = [
        "REPORT.VIEW.INDEX", "USER.LOGOFF",
        # Try various menu/listing/search functions
        "MENU", "MAIN.MENU", "HOME", "INDEX",
        "CUSTOMER.LIST", "CUSTOMER.SEARCH", "CUST.LIST",
        "VENDOR.LIST", "VENDOR.SEARCH", "VEN.LIST",
        "INVENTORY.LIST", "INV.LIST", "ITEM.LIST",
        "SO.LIST", "SO.SEARCH", "SALES.ORDER.LIST",
        "PO.LIST", "PO.SEARCH", "PURCHASE.ORDER.LIST",
        "WO.LIST", "WO.SEARCH", "WORK.ORDER.LIST",
        "AR.LIST", "AP.LIST", "GL.LIST",
        "REPORT.LIST", "REPORT.INDEX",
        "HELP", "ABOUT", "SYSTEM.INFO",
        # BI-specific
        "BI.REPORTS", "INFORMER", "REPORT.MENU",
        # Admin/system
        "SYS.ADMIN", "ADMIN", "SETUP", "CONFIG",
        "USER.LIST", "USER.ADMIN", "SECURITY",
    ]
    func_results = {}
    for func in data_functions:
        try:
            r = session.get(f"{CGI_BASE}/APPLOAD?APP={func}", timeout=15)
            is_auth = "NOT AUTHORIZED" not in r.text.upper() and "UNAUTHORIZED" not in r.text.upper()
            func_results[func] = {
                "status": r.status_code,
                "size": len(r.text),
                "authorized": is_auth,
                "has_table": "<table" in r.text.lower(),
                "has_form": "<form" in r.text.lower(),
                "has_data": len(r.text) > 2000 and is_auth,
            }
            if is_auth and r.status_code == 200 and len(r.text) > 1000:
                print(f"  ✓ {func}: {len(r.text)} bytes, table={func_results[func]['has_table']}")
                safe_name = re.sub(r'[^\w]', '_', func)
                (RESULTS_DIR / f"func_{safe_name}.html").write_text(r.text, encoding="utf-8")
        except Exception as e:
            func_results[func] = {"error": str(e)}
    results["function_probes"] = func_results

    # 5. Try form submissions on accessible pages
    print("\n--- FORM SUBMISSION PROBES ---")
    form_tests = [
        # Try to load reports with date ranges
        {"url": f"{CGI_BASE}/REPORT.VIEW.INDEX", "method": "POST",
         "data": {"START_DATE": "01/01/2000", "END_DATE": "12/31/2099"}},
        # Try search/filter
        {"url": f"{CGI_BASE}/APPLOAD?APP=REPORT.VIEW.INDEX", "method": "GET",
         "params": {"page": "1", "limit": "100"}},
    ]
    for test in form_tests:
        try:
            if test.get("method") == "POST":
                r = session.post(test["url"], data=test.get("data", {}), timeout=30)
            else:
                r = session.get(test["url"], params=test.get("params", {}), timeout=30)
            results[f"form_{test['url'].split('/')[-1]}"] = {
                "status": r.status_code,
                "size": len(r.text),
                "has_data": len(r.text) > 2000,
            }
        except Exception:
            pass

    # 6. Try the Informer SSO link discovery from ERP
    print("\n--- SSO LINK DISCOVERY ---")
    sso_pages = [
        f"{CGI_BASE}/INFORMER",
        f"{CGI_BASE}/BI.REPORTS",
        f"{CGI_BASE}/MENU.REPORTS",
        f"{CGI_BASE}/APPLOAD?APP=INFORMER",
        f"{CGI_BASE}/APPLOAD?APP=BI.REPORTS",
    ]
    for url in sso_pages:
        try:
            r = session.get(url, timeout=15)
            sso_links = re.findall(r'["\']([^"\']*8443[^"\']*)["\']', r.text)
            sso_links += re.findall(r'["\']([^"\']*sso[^"\']*)["\']', r.text, re.I)
            if sso_links:
                print(f"  SSO links found on {url}:")
                for sl in sso_links[:5]:
                    print(f"    {sl}")
            results[f"sso_{url.split('/')[-1]}"] = {
                "status": r.status_code,
                "sso_links": sso_links[:10],
            }
        except Exception:
            pass

    # 7. Probe for hidden endpoints and API paths
    print("\n--- HIDDEN ENDPOINT PROBES ---")
    hidden_paths = [
        "/api/", "/rest/", "/ws/", "/graphql",
        "/swagger", "/docs", "/health", "/status",
        "/admin/", "/manage/", "/monitor/",
        "/cgi-bin/", "/scripts/",
        "/cgi-bin/mvi.exe/API", "/cgi-bin/mvi.exe/REST",
        "/cgi-bin/mvi.exe/EXPORT", "/cgi-bin/mvi.exe/DOWNLOAD",
        "/cgi-bin/mvi.exe/BATCH", "/cgi-bin/mvi.exe/BULK",
        "/cgi-bin/mvi.exe/REPORT.EXPORT",
        "/cgi-bin/mvi.exe/DATA.EXPORT",
        "/cgi-bin/mvi.exe/QUERY",
    ]
    for path in hidden_paths:
        try:
            r = session.get(f"{ERP_BASE}{path}", timeout=10, allow_redirects=False)
            if r.status_code not in (404, 500, 502, 503):
                print(f"  {path}: {r.status_code} ({len(r.text)} bytes)")
                results[f"hidden_{path.replace('/', '_')}"] = {
                    "status": r.status_code,
                    "size": len(r.text),
                    "redirect": r.headers.get("Location", ""),
                }
        except Exception:
            pass

    return results


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Deep probe KeyedIn ERP + Informer")
    parser.add_argument("--phase", default="all", choices=["informer", "erp", "all"])
    parser.add_argument("--report-id", type=int, default=None)
    parser.add_argument("positional_phase", nargs="?", default=None,
                        help="positional shorthand for --phase")
    args = parser.parse_args()
    phase = args.positional_phase or args.phase
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    session = requests.Session()
    session.verify = False
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0"})

    auth_token, client_id = authenticate(session)
    if not auth_token:
        print("Authentication failed!")
        sys.exit(1)

    all_results = {
        "timestamp": timestamp,
        "auth_token_prefix": auth_token[:8],
        "phase": phase,
    }

    if phase in ("informer", "all"):
        # --- INFORMER: Probe all services ---
        print("\n" + "=" * 60)
        print("=== INFORMER BI DEEP PROBE ===")
        print("=" * 60)

        svc_results = probe_all_informer_services(session, auth_token, client_id)
        all_results["informer_services"] = svc_results

        # Save detailed service results
        with open(RESULTS_DIR / "informer_services.json", "w") as f:
            json.dump(svc_results, f, indent=2, default=str)

        # --- INFORMER: Probe getData for first 5 reports ---
        print("\n" + "=" * 60)
        print("=== INFORMER: getData PROBE (first 5 reports) ===")
        print("=" * 60)

        report_results = {}
        for rid in REPORT_IDS[:5]:
            print(f"\n--- Report {rid} ---")
            try:
                r = probe_report_lookup_and_getdata(session, auth_token, client_id, rid)
                report_results[str(rid)] = r
                vt = r.get("view_token")
                gd = r.get("getdata", {})
                print(f"  Name: {r.get('name', '?')}")
                print(f"  ViewToken: {vt[:20] if vt else 'NONE'}...")
                print(f"  Total count: {r.get('total_count', 0)}")
                if gd:
                    print(f"  getData page1: {gd.get('page1_strings', 0)} strings, {gd.get('page1_bytes', 0)} bytes")
                    print(f"  getData page2: {'OK' if gd.get('page2_ok') else 'FAILED'}, {gd.get('page2_strings', 0)} strings")
                    print(f"  Fields: {gd.get('field_candidates', [])[:10]}")

                # Test export URLs with first report that has a ViewToken
                if vt and rid == REPORT_IDS[0]:
                    print(f"\n--- Export URL probes (report {rid}) ---")
                    export_results = probe_export_urls(session, auth_token, client_id, vt, rid)
                    all_results["export_probes"] = export_results
                    for er in export_results:
                        if er.get("has_data"):
                            print(f"  ✓ EXPORT FOUND: {er['url'][:80]} ({er['size']} bytes)")
                        elif er.get("status") == 200:
                            print(f"  ~ 200 but no data: {er['url'][:80]} ({er['size']} bytes)")
            except Exception as e:
                report_results[str(rid)] = {"error": str(e), "traceback": traceback.format_exc()}
                print(f"  ERROR: {e}")

        all_results["report_getdata"] = report_results

        # Save report results
        with open(RESULTS_DIR / "report_getdata.json", "w") as f:
            json.dump(report_results, f, indent=2, default=str)

    if phase in ("erp", "all"):
        # --- LEGACY ERP PROBE ---
        erp_results = probe_erp_deep(session)
        all_results["legacy_erp"] = erp_results

        with open(RESULTS_DIR / "legacy_erp.json", "w") as f:
            json.dump(erp_results, f, indent=2, default=str)

    # Save master results
    with open(RESULTS_DIR / f"deep_probe_{timestamp}.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    # Print summary
    print("\n" + "=" * 60)
    print("=== DEEP PROBE SUMMARY ===")
    print("=" * 60)

    if "informer_services" in all_results:
        ok_count = sum(1 for v in all_results["informer_services"].values() if v.get("status") == "OK")
        err_count = sum(1 for v in all_results["informer_services"].values() if v.get("status") != "OK")
        print(f"\nInformer RPC: {ok_count} methods returned data, {err_count} errors")
        print("Methods with data:")
        for method, info in all_results["informer_services"].items():
            if info.get("status") == "OK" and info.get("string_count", 0) > 5:
                print(f"  {method}: {info['string_count']} strings, {info['response_bytes']} bytes")

    if "report_getdata" in all_results:
        gd_ok = sum(1 for v in all_results["report_getdata"].values()
                     if isinstance(v, dict) and v.get("getdata", {}).get("status") == "OK")
        print(f"\ngetData: {gd_ok}/{len(all_results['report_getdata'])} reports returned paginated data")

    if "legacy_erp" in all_results:
        erp = all_results["legacy_erp"]
        spider = erp.get("spidering", {})
        print(f"\nLegacy ERP: {spider.get('accessible', 0)} accessible pages, {spider.get('unauthorized', 0)} unauthorized")

    print(f"\nResults saved to {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
