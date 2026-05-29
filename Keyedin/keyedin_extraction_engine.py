#!/usr/bin/env python3
"""
KeyedIn Full-System Extraction Engine (Hardened)

Production-grade extraction framework for cloning KeyedIn Legacy ERP + Informer BI
before system sunset. Features:
  - Exponential backoff retry for all network operations
  - Session health monitoring (license quota, timeouts, stale sessions)
  - Checkpointing and resume (picks up where it left off)
  - Data integrity verification (checksums, row counts)
  - Rate limiting to avoid overloading the server
  - Structured logging with extraction manifests
  - Idempotent operations (re-running won't duplicate data)

Systems:
  1. KeyedIn Legacy ERP (port 443) — CGI/mvi.exe, 19 modules, 240 functions
  2. Informer BI (port 8443) — GWT-RPC, 30 reports, 18 RPC services

Usage:
  python keyedin_extraction_engine.py --mode spider     # Map all menus/submenus
  python keyedin_extraction_engine.py --mode extract     # Extract all data
  python keyedin_extraction_engine.py --mode reports     # Extract spooled reports
  python keyedin_extraction_engine.py --mode informer    # Informer CSV exports
  python keyedin_extraction_engine.py --mode verify      # Verify extraction integrity
  python keyedin_extraction_engine.py --mode all         # Full pipeline
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

USERNAME = os.environ.get("KEYEDIN_USERNAME", "")
PASSWORD = os.environ.get("KEYEDIN_PASSWORD", "")
CDP_URL = os.environ.get("CDP_URL", "http://localhost:29229")

ERP_BASE = "https://eaglesign.keyedinsign.com"
CGI_BASE = f"{ERP_BASE}/cgi-bin/mvi.exe"
INFORMER_BASE = "https://eaglesign.keyedinsign.com:8443/eaglesign"

# Directories
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "extraction_output"
CHECKPOINT_DIR = OUTPUT_DIR / ".checkpoints"
MANIFEST_FILE = OUTPUT_DIR / "extraction_manifest.json"
SPIDER_MAP_FILE = OUTPUT_DIR / "system_map.json"
REPORT_DIR = OUTPUT_DIR / "spooled_reports"
INFORMER_DIR = OUTPUT_DIR / "informer_exports"
CGI_DIR = OUTPUT_DIR / "cgi_data"
LOG_FILE = OUTPUT_DIR / "extraction.log"

# Rate limiting
REQUEST_DELAY_S = 1.5  # seconds between requests to avoid overload
BATCH_DELAY_S = 5.0    # seconds between batches of reports

# Retry config
MAX_RETRIES = 5
INITIAL_BACKOFF_S = 2.0
MAX_BACKOFF_S = 60.0
BACKOFF_MULTIPLIER = 2.0

# Session health
SESSION_CHECK_INTERVAL = 300  # check session every 5 min
LICENSE_RETRY_INTERVAL = 30   # retry login every 30s if quota exceeded
MAX_LICENSE_RETRIES = 60      # try for up to 30 minutes

# All 240 functions organized by module (from keyedin-mcp analysis)
ERP_MODULES = {
    "FAVORITES": [
        "CRM.CONTACT.MGT", "OPEN.SO", "EST.RESET.EXP.DATE", "PURCHASE",
        "EST.PROP.RESET.DATE", "PART.PRICES", "SO.CONTRACT", "STOCK",
        "EST.QUOTE.STATUS",
    ],
    "CRM": [
        "CHANGE.SC.ACCOUNT", "SERVICE.CALL.STATUS.REPORT", "CRM.NOTES.REPORT",
        "CRM.ATTACHMENTS.DELETE", "IMPORT.CRM.NEW",
        "ACCOUNT.TYPE.CODE.LISTING", "CALL.METHOD.CODES.LISTING",
        "CALL.TYPE.CODES.LISTING", "LEAD.SOURCE.EVENT.LISTING",
        "SERVICE.CALL.STATUS.CODE.LISTING", "CRM.SOLUTIONS.LISTING",
    ],
    "PROJECT_MANAGEMENT": [
        "#PROJECT.LISTING", "#PROJECT.DETAILS", "#PROJECT.MILESTONE.TRACKING",
        "#PROJECT.QUOTES", "#PROJECT.LOCATIONS", "#PROJECT.PROPOSALS",
        "#PROJECT.SALES.ORDERS", "#PROJECT.WORK.ORDERS", "#PROJECT.POS",
        "#PROJECT.SHIPMENTS", "#PROJECT.CONTACTS", "#PROJECT.VENDORS",
        "#PROJECT.NOTES", "#PROJECT.ATTACHMENTS", "PM.INSURANCE.LISTING",
        "LANDLORD.MALL.TC.LISTING", "PROJECT.MILESTONE.CODES.LISTING",
        "PROJECT.STATUS.CODES.LISTING", "PROJECT.TYPE.CODES.LISTING",
    ],
    "ESTIMATING_AND_PROPOSALS": [
        "EST.QUOTE.ENTRY", "QUOTE.ENTRY.LIMITED", "EST.CHANGE.ACCTID",
        "EST.QUOTE.PRINT", "EST.QUOTE.COPY", "EST.PROP.PRINT",
        "EST.PROP.REPRINT", "EST.PROP.DELETE", "QUOTE.PIPELINE.REPORT",
        "EST.SIGN.TEMPLATE.MAINT", "EST.BATCH.INACTIVE",
        "IMPORT.SIGN.TEMPLATE", "QUOTE.MASS.UPDATE", "QUOTE.MASS.COPY",
        "CONVERT.QUOTE.TO.MFG", "QUOTE.MASS.DELETE", "QUOTE.LISTING",
        "SIGN.TEMPLATE.LISTING", "EST.TEMPLATE.PRINT", "EST.PROPOSAL.STATUS",
        "EST.QUOTE.STATUS.CODE.LIST", "WORK.DEPT.LIST", "WORK.CODE.LIST",
        "SIGN.TYPE.CODES.LISTING", "QUOTE.SALES.STAGE.CODE.LISTING",
        "PREPLAN.REPORT",
    ],
    "SALES_ORDER_ENTRY": [
        "ORDER.ENTRY", "EST.CREATE.SO", "SO.PRINT", "LSO", "LOOK.SO",
        "DAY.SALES", "SO.COMMIT", "EXTRA.CHARGES.LIST", "ORDER.CLASSES.LIST",
        "ORDER.TYPES.LIST", "PRICE.CLASS.CODE.LIST", "PRICE.CODES.LIST",
        "REASON.CODES.LIST", "SALES.CODES.LIST", "SALESPERSONS.LIST",
        "SALES.TAXES.LIST", "TERRITORY.CODES.LIST", "STATES.LIST",
        "COUNTRY.LIST",
    ],
    "SHIPPING_TRACKING": [
        "SHIPLISTS", "SHIPMENTS", "SHIPMENTS.TRACKING", "DAILY.SHIP.REPORT",
    ],
    "SALES_ANALYSIS": [
        "PROD.SUM", "CUST.SUM", "CUST.PROD", "CUST.PROD.EXPORT",
        "GM.BY.PROD", "GM.BY.INV", "GM.BY.INV.EXPORT", "PROD.CUST",
        "SA.BY.STATE", "SLSPER.PROD", "SLSPER.PROD.EXPORT",
        "TAX.BY.TYPE.REPORT", "QUOTE.SALES.DIFFS", "SALES.TERRITORY",
        "GM.DET.PROD.PART", "GM.PROJECT",
    ],
    "PURCHASING": [
        "QV.PRINT", "PO.CHANGE", "PUR.PRINT", "PO.RECEIPTS", "PO.CLOSE",
        "PO.ACTIONS", "PO.ACTION.RELEASE", "PO.REQ.RELEASE", "PO.REQ.DELETE",
        "VENDORS", "SHOW.PO", "PUR.HISTORY", "WO.OPEN.PO", "SHOW.BUYERS",
        "PO.INQUIRY", "PUR.COMMIT", "PUR.PART.VAR", "PUR.PO.DEL.ANALYSIS",
        "PUR.PO.SCHED.ANALYSIS", "PUR.PO.VAR.ANALYSIS", "WSA.PURCHASE.REPORT",
    ],
    "INVENTORY_AND_PARTS": [
        "FIRST.ISSUE", "ISSUE", "RAW.MATL.MAINT", "ASSEMBLY.MAINT",
        "WIP.RECEIPTS", "ADJUST", "TRANSFER", "BOM", "COPY.BILL",
        "BOM.DELETE", "SHOW.PS", "ROUTING.MAINT", "CHG.VALUE", "COST.POST",
        "PART.COSTS", "CUST.PRICE.MAINT", "OBSOLETE", "IMPORT.BOM",
        "IMPORT.ROUTING", "IMPORT.PARTS", "CHECK.ISSUE", "IT.HISTORY",
        "SHOW.ACTIVITY", "SHOW.ADJUST.CODE", "SHOW.ISSUE.REASON.CODES",
        "MATL.RECEIVED", "MATL.ISSUED", "USAGE.ANAL.FILE",
        "SHOW.ENGR.STATUS.CODES", "SHOW.INV.TYPES", "SHOW.UM.CODES",
        "PRINT.RT", "BILL.COMPARE", "COMPLETE.BILL", "COMPLETE.WU",
        "ITEM.MASTER.LIST", "SUM.BILL", "COMPLETE.WC.WU", "COMPLETE.RT",
        "COMPLETE.GROUP", "COMPLETE.TOOL.LIST", "STOCK.STATUS",
        "PART.COST.LIST", "PART.PRICE.LIST", "COST.INQ", "SHOW.PART.PRICES",
    ],
    "JOB_COST": [
        "WO.PRICE.CALC", "WO.HISTORY", "WO.STATUS.SUM", "WO.STATUS.MATL",
        "WO.STATUS.LABR", "WO.STATUS.LDTL", "WO.STATUS.LDTL.LIMITED",
        "WO.STATUS.OUTP", "WO.STATUS.MATDIR", "WO.STATUS.BILL",
        "WO.STATUS.GLTRANS", "WO.GROUP.ANALYSIS", "SHOW.WO.PRICE.CALC",
        "WIP.RETRO", "EXPORT.WO.LABOR.ANALYSIS",
    ],
    "MRP": [
        "MRP.RUN", "MRP.STATUS",
    ],
    "PRODUCTION_SHOP_FLOOR": [
        "WO.ENTRY", "WO.PRINT", "WO.INQUIRY", "WO.LISTING", "WO.RELEASE",
        "WO.CLOSE", "WO.REOPEN", "PROD.CALENDAR", "PROD.SCHEDULE",
        "WO.STATUS.REPORT", "PROD.ROUTE.LISTING",
    ],
    "RESOURCE_SCHEDULING": [
        "RS.SCHEDULING", "RS.RESOURCE.MAINT",
    ],
    "LABOR_AND_PAYROLL": [
        "LABOR.ENTRY", "LABOR.IMPORT", "PAYROLL.REPORT",
    ],
    "ACCOUNTS_PAYABLE": [
        "AP.INVOICE.ENTRY", "AP.CHECK.PRINT", "AP.VENDOR.REPORT",
        "LIST.AP.DET", "AP.AGING",
    ],
    "ACCOUNTS_RECEIVABLE": [
        "AR.CASH.RECEIPTS", "AR.INVOICE.PRINT", "AR.AGING",
        "AR.STATEMENT.PRINT",
    ],
    "REPORT_ADMIN": [
        "REPORT.VIEW.INDEX", "REPORT.ADMIN",
    ],
    "ADMINISTRATION": [
        "USER.ADMIN", "SYSTEM.ADMIN",
    ],
    "SYSTEM_MANAGEMENT": [
        "USER.LOGOFF",
    ],
}

# Informer report IDs
INFORMER_REPORT_IDS = [
    1441842, 1441843, 1441844, 1441849, 1441850, 1441851, 1441852,
    1441853, 1441854, 1441855, 1441856, 1441857, 1441859, 1441860,
    1441861, 1441862, 1441865, 1441866, 1441868, 1441869, 1441870,
    1441872, 1441873, 1441874, 1441875, 1441877, 1441878, 1441883,
    1441884, 1441887,
]

# Gap IDs to also probe
INFORMER_GAP_IDS = [
    1441845, 1441846, 1441847, 1441848, 1441858, 1441863, 1441864,
    1441867, 1441871, 1441876, 1441879, 1441880, 1441881, 1441882,
    1441885, 1441886,
]

# BI function codes that generate reports (need REPORT.IFRAME extraction)
BI_FUNCTIONS = [
    "OPEN.SO", "EST.QUOTE.STATUS", "SERVICE.CALL.STATUS.REPORT",
    "EST.PROPOSAL.STATUS", "QUOTE.LISTING", "LSO", "DAY.SALES",
    "SO.COMMIT", "DAILY.SHIP.REPORT", "PROD.SUM", "CUST.SUM",
    "CUST.PROD", "CUST.PROD.EXPORT", "GM.BY.PROD", "GM.BY.INV",
    "GM.BY.INV.EXPORT", "PROD.CUST", "SA.BY.STATE", "SLSPER.PROD",
    "SLSPER.PROD.EXPORT", "TAX.BY.TYPE.REPORT", "SALES.TERRITORY",
    "GM.DET.PROD.PART", "PUR.HISTORY", "PO.INQUIRY", "PUR.PART.VAR",
    "PUR.PO.SCHED.ANALYSIS", "PUR.PO.VAR.ANALYSIS", "IT.HISTORY",
    "SHOW.ACTIVITY", "MATL.RECEIVED", "MATL.ISSUED", "ITEM.MASTER.LIST",
    "WIP.RETRO",
]


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    """Configure structured logging to file and console."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("keyedin_extraction")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


log = setup_logging()


# ---------------------------------------------------------------------------
# Utility: Retry with exponential backoff
# ---------------------------------------------------------------------------

async def retry_async(
    func,
    *args,
    max_retries: int = MAX_RETRIES,
    initial_backoff: float = INITIAL_BACKOFF_S,
    max_backoff: float = MAX_BACKOFF_S,
    multiplier: float = BACKOFF_MULTIPLIER,
    operation_name: str = "operation",
    **kwargs,
):
    """Execute an async function with exponential backoff retry."""
    last_error = None
    backoff = initial_backoff

    for attempt in range(1, max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt == max_retries:
                log.error(
                    "%s failed after %d attempts: %s",
                    operation_name, max_retries, e,
                )
                raise
            log.warning(
                "%s attempt %d/%d failed: %s — retrying in %.1fs",
                operation_name, attempt, max_retries, e, backoff,
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * multiplier, max_backoff)

    raise last_error  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Checkpointing
# ---------------------------------------------------------------------------

class CheckpointManager:
    """Manages extraction progress checkpoints for resume capability."""

    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._state: dict[str, Any] = self._load()

    def _state_file(self) -> Path:
        return self.checkpoint_dir / "extraction_state.json"

    def _load(self) -> dict[str, Any]:
        sf = self._state_file()
        if sf.exists():
            try:
                with open(sf, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                log.warning("Corrupt checkpoint file, starting fresh")
        return {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_items": {},
            "failed_items": {},
            "in_progress": None,
        }

    def _save(self) -> None:
        self._state["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(self._state_file(), "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2)

    def is_completed(self, item_key: str) -> bool:
        return item_key in self._state["completed_items"]

    def mark_completed(
        self, item_key: str, metadata: dict[str, Any] | None = None,
    ) -> None:
        self._state["completed_items"][item_key] = {
            "completed_at": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }
        self._state["in_progress"] = None
        self._save()

    def mark_failed(self, item_key: str, error: str) -> None:
        self._state["failed_items"][item_key] = {
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "error": error,
        }
        self._state["in_progress"] = None
        self._save()

    def mark_in_progress(self, item_key: str) -> None:
        self._state["in_progress"] = item_key
        self._save()

    @property
    def completed_count(self) -> int:
        return len(self._state["completed_items"])

    @property
    def failed_count(self) -> int:
        return len(self._state["failed_items"])

    def summary(self) -> dict[str, Any]:
        return {
            "completed": self.completed_count,
            "failed": self.failed_count,
            "in_progress": self._state.get("in_progress"),
            "started_at": self._state.get("started_at"),
            "updated_at": self._state.get("updated_at"),
        }


# ---------------------------------------------------------------------------
# Data Integrity
# ---------------------------------------------------------------------------

def compute_file_checksum(filepath: Path) -> str:
    """Compute SHA-256 checksum for a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_file_integrity(filepath: Path, expected_checksum: str) -> bool:
    """Verify a file matches its expected checksum."""
    actual = compute_file_checksum(filepath)
    return actual == expected_checksum


class ExtractionManifest:
    """Tracks all extracted files with checksums and metadata."""

    def __init__(self, manifest_path: Path):
        self.path = manifest_path
        self.entries: list[dict[str, Any]] = []
        if manifest_path.exists():
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    data = json.load(f)
                    self.entries = data.get("files", [])
            except (json.JSONDecodeError, OSError):
                pass

    def add_entry(
        self,
        filepath: Path,
        source: str,
        source_id: str,
        data_type: str,
        row_count: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Record an extracted file in the manifest."""
        entry = {
            "file": str(filepath.relative_to(OUTPUT_DIR)),
            "source": source,
            "source_id": source_id,
            "data_type": data_type,
            "size_bytes": filepath.stat().st_size,
            "checksum_sha256": compute_file_checksum(filepath),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }
        if row_count is not None:
            entry["row_count"] = row_count
        if extra:
            entry.update(extra)
        self.entries.append(entry)
        self.save()

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": "2.0",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "total_files": len(self.entries),
                    "total_bytes": sum(e.get("size_bytes", 0) for e in self.entries),
                    "files": self.entries,
                },
                f,
                indent=2,
            )

    def verify_all(self) -> tuple[int, int, list[str]]:
        """Verify all files in manifest. Returns (passed, failed, errors)."""
        passed = 0
        failed = 0
        errors: list[str] = []
        for entry in self.entries:
            fp = OUTPUT_DIR / entry["file"]
            if not fp.exists():
                errors.append(f"MISSING: {entry['file']}")
                failed += 1
            elif not verify_file_integrity(fp, entry["checksum_sha256"]):
                errors.append(f"CHECKSUM MISMATCH: {entry['file']}")
                failed += 1
            else:
                passed += 1
        return passed, failed, errors


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Token bucket rate limiter for controlling request frequency."""

    def __init__(self, min_interval: float = REQUEST_DELAY_S):
        self.min_interval = min_interval
        self._last_request_time = 0.0

    async def wait(self) -> None:
        """Wait until we can make the next request."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self._last_request_time = time.monotonic()


# ---------------------------------------------------------------------------
# Session Health Monitor
# ---------------------------------------------------------------------------

class SessionHealthMonitor:
    """Monitors browser session health and handles recovery."""

    def __init__(self):
        self.last_check = 0.0
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3
        self.is_healthy = True
        self.license_retries = 0

    async def check_health(self, page) -> bool:
        """Check if the current browser session is still valid."""
        try:
            content = await page.content()

            # Check for license quota exceeded
            if "EXCEEDED YOUR LICENSE QUOTA" in content.upper():
                log.warning("License quota exceeded — session invalid")
                self.is_healthy = False
                return False

            # Check for login page redirect (session expired)
            if "LOGIN.START" in page.url or "login" in page.url.lower():
                log.warning("Session expired — redirected to login")
                self.is_healthy = False
                return False

            # Check for error pages
            if "USER IS NOT AUTHORIZED" in content:
                log.warning("Authorization error detected")
                # This is normal for restricted functions, not a session issue
                return True

            self.consecutive_failures = 0
            self.is_healthy = True
            return True

        except Exception as e:
            self.consecutive_failures += 1
            log.warning(
                "Health check failed (%d/%d): %s",
                self.consecutive_failures,
                self.max_consecutive_failures,
                e,
            )
            if self.consecutive_failures >= self.max_consecutive_failures:
                self.is_healthy = False
            return False

    async def wait_for_healthy(self, page, reauth_func) -> bool:
        """Wait until session is healthy, attempting reauth if needed."""
        if self.is_healthy:
            return True

        log.info("Session unhealthy — attempting recovery...")
        for attempt in range(MAX_LICENSE_RETRIES):
            try:
                await reauth_func(page)
                if await self.check_health(page):
                    log.info("Session recovered after %d attempts", attempt + 1)
                    return True
            except Exception as e:
                log.warning("Recovery attempt %d failed: %s", attempt + 1, e)

            await asyncio.sleep(LICENSE_RETRY_INTERVAL)

        log.error("Session recovery failed after %d attempts", MAX_LICENSE_RETRIES)
        return False


# ---------------------------------------------------------------------------
# Browser Automation Core
# ---------------------------------------------------------------------------

class KeyedInBrowser:
    """Hardened browser automation for KeyedIn ERP + Informer."""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.rate_limiter = RateLimiter()
        self.health = SessionHealthMonitor()
        self.checkpoint = CheckpointManager(CHECKPOINT_DIR)
        self.manifest = ExtractionManifest(MANIFEST_FILE)
        self._playwright = None

    async def connect(self):
        """Connect to existing Chrome browser via CDP.

        Creates a fresh page for extraction work to avoid conflicts with
        existing tabs/framesets that cause execution context destruction.
        """
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.connect_over_cdp(CDP_URL)
        contexts = self.browser.contexts
        if not contexts:
            raise RuntimeError("No browser contexts found — is Chrome running?")
        self.context = contexts[0]

        # Create a fresh page for our extraction work to avoid
        # conflicts with existing frameset tabs
        self.page = await self.context.new_page()
        log.info("Connected to Chrome via CDP at %s (new page created)", CDP_URL)

    async def disconnect(self):
        """Cleanly disconnect from browser."""
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        log.info("Disconnected from browser")

    async def authenticate(self) -> bool:
        """Authenticate to ERP via login form, handling license quota.

        Checks if already authenticated first (via existing browser session).
        Falls back to form-based login with license quota retry loop.
        """
        log.info("Authenticating as %s...", USERNAME)

        # Check if session cookies from other tabs give us auth
        try:
            # Navigate and don't wait for full load (framesets never finish)
            try:
                await self.page.goto(
                    f"{CGI_BASE}/REPORT.VIEW.INDEX",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
            except Exception:
                pass  # framesets often ERR_ABORTED or timeout
            await asyncio.sleep(5)

            # Gather text from all frames
            all_text = ""
            try:
                for frame in self.page.frames:
                    try:
                        fc = await frame.content()
                        all_text += fc
                    except Exception:
                        pass
                content = await self.page.content()
                all_text += content
            except Exception:
                pass

            # Signs we're authenticated
            if any(marker in all_text for marker in [
                "Eagle Sign", "Report Title", "Click on a report",
                "Selection Criteria", "Add to Favorites",
            ]):
                log.info("Already authenticated (session cookies valid)")
                self.health.is_healthy = True
                return True

        except Exception as e:
            log.debug("Pre-auth check failed: %s", e)

        for attempt in range(MAX_LICENSE_RETRIES):
            try:
                try:
                    await self.page.goto(
                        f"{CGI_BASE}/LOGIN.START",
                        wait_until="domcontentloaded",
                        timeout=30000,
                    )
                except Exception:
                    pass  # framesets often cause navigation errors
                await asyncio.sleep(3)

                # Check all frames for the login form
                target_frame = self.page
                for frame in self.page.frames:
                    try:
                        fc = await frame.content()
                        if "USERNAME" in fc and "PASSWORD" in fc:
                            target_frame = frame
                            break
                    except Exception:
                        pass

                # Fill login form
                username_field = target_frame.locator('input[name="USERNAME"]')
                password_field = target_frame.locator('input[name="PASSWORD"]')

                if await username_field.count() > 0:
                    await username_field.fill(USERNAME)
                    await password_field.fill(PASSWORD)

                    # Submit
                    submit = target_frame.locator(
                        'input[type="submit"], button[type="submit"]'
                    )
                    if await submit.count() > 0:
                        await submit.first.click()
                    else:
                        await password_field.press("Enter")

                    try:
                        await self.page.wait_for_load_state(
                            "domcontentloaded", timeout=15000,
                        )
                    except Exception:
                        pass
                    await asyncio.sleep(3)

                # Check for license quota (search all frames)
                all_content = ""
                try:
                    for frame in self.page.frames:
                        try:
                            all_content += await frame.content()
                        except Exception:
                            pass
                    all_content += await self.page.content()
                except Exception:
                    pass
                if "EXCEEDED YOUR LICENSE QUOTA" in all_content.upper():
                    log.warning(
                        "License quota exceeded (attempt %d/%d) — waiting %ds...",
                        attempt + 1, MAX_LICENSE_RETRIES, LICENSE_RETRY_INTERVAL,
                    )
                    await asyncio.sleep(LICENSE_RETRY_INTERVAL)
                    continue

                # Check for successful login
                if "LOGIN.START" not in self.page.url:
                    log.info("Authentication successful")
                    self.health.is_healthy = True
                    return True

                # Already logged in (no login form found)
                if await username_field.count() == 0:
                    log.info("Already authenticated")
                    self.health.is_healthy = True
                    return True

            except Exception as e:
                log.warning("Auth attempt %d failed: %s", attempt + 1, e)
                if attempt < MAX_LICENSE_RETRIES - 1:
                    await asyncio.sleep(LICENSE_RETRY_INTERVAL)

        log.error("Authentication failed after %d attempts", MAX_LICENSE_RETRIES)
        return False

    async def navigate_to_function(self, function_code: str) -> str:
        """Navigate to a CGI function and return the page content."""
        await self.rate_limiter.wait()

        # Handle hash-route functions (e.g., #PROJECT.LISTING)
        if function_code.startswith("#"):
            url = f"{ERP_BASE}/{function_code}"
        else:
            url = f"{CGI_BASE}/APPLOAD?APP={function_code}"

        try:
            response = await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as nav_err:
            # ERR_ABORTED often means a redirect or non-navigable response;
            # the page may still have useful content in the current DOM
            if "ERR_ABORTED" in str(nav_err):
                log.debug(
                    "Navigation to %s aborted (redirect/frameset) — reading DOM",
                    function_code,
                )
            else:
                log.warning("Navigation to %s failed: %s", function_code, nav_err)
                raise

        await asyncio.sleep(2)

        # Robust content extraction with multiple retries for context issues
        for content_attempt in range(3):
            try:
                all_content: list[str] = []
                try:
                    main_content = await self.page.content()
                    all_content.append(main_content)
                except Exception:
                    pass

                for frame in self.page.frames:
                    try:
                        frame_content = await frame.content()
                        all_content.append(frame_content)
                    except Exception:
                        pass

                if all_content:
                    return "\n<!-- FRAME_SEPARATOR -->\n".join(all_content)

            except Exception:
                if content_attempt < 2:
                    await asyncio.sleep(2)
                    continue

        # Last resort: return whatever we can get
        try:
            return await self.page.content()
        except Exception as e:
            log.warning("Content extraction for %s failed: %s", function_code, e)
            raise

    async def extract_report_iframe(self, function_code: str) -> str | None:
        """Extract content from REPORT.IFRAME for BI report functions."""
        try:
            content = await self.page.content()

            # Look for REPORT.IFRAME
            for frame in self.page.frames:
                frame_url = frame.url
                if "REPORT.IFRAME" in frame_url or "idFrame" in frame.name:
                    try:
                        frame_content = await frame.content()
                        # Extract <pre> tags (verbatim report data)
                        pre_blocks = re.findall(
                            r"<pre[^>]*>(.*?)</pre>",
                            frame_content,
                            re.DOTALL | re.IGNORECASE,
                        )
                        if pre_blocks:
                            return "\n".join(pre_blocks)
                        return frame_content
                    except Exception as e:
                        log.warning(
                            "Failed to read iframe for %s: %s", function_code, e
                        )

            return None

        except Exception as e:
            log.warning("Report iframe extraction for %s failed: %s", function_code, e)
            return None

    async def extract_spooled_report(self, report_id: str) -> str | None:
        """Extract a full spooled report by ID from REPORT.VIEW."""
        await self.rate_limiter.wait()

        url = f"{CGI_BASE}/REPORT.VIEW?REPORT_ID={report_id}"
        try:
            await self.page.goto(url, wait_until="load", timeout=30000)
            await asyncio.sleep(2)

            # The report data is in <pre> tags within frames
            all_pre_content: list[str] = []

            for frame in self.page.frames:
                try:
                    frame_content = await frame.content()
                    pre_blocks = re.findall(
                        r"<pre[^>]*>(.*?)</pre>",
                        frame_content,
                        re.DOTALL | re.IGNORECASE,
                    )
                    all_pre_content.extend(pre_blocks)
                except Exception:
                    pass

            # Also check main page
            main_content = await self.page.content()
            pre_blocks = re.findall(
                r"<pre[^>]*>(.*?)</pre>",
                main_content,
                re.DOTALL | re.IGNORECASE,
            )
            all_pre_content.extend(pre_blocks)

            if all_pre_content:
                return "\n".join(all_pre_content)
            return None

        except Exception as e:
            log.warning("Spooled report %s extraction failed: %s", report_id, e)
            return None

    async def get_spooled_report_index(self) -> list[dict[str, str]]:
        """Get the full index of spooled reports from REPORT.VIEW.INDEX."""
        await self.rate_limiter.wait()

        url = f"{CGI_BASE}/APPLOAD?APP=REPORT.VIEW.INDEX"
        await self.page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)

        # Extract report list from the page
        reports: list[dict[str, str]] = []

        # Parse the report links via JS
        report_data = await self.page.evaluate("""
            () => {
                const reports = [];
                // Look for links that contain REPORT.VIEW or openReport
                const links = document.querySelectorAll('a[href*="REPORT"], a[onclick*="openReport"]');
                links.forEach(link => {
                    const href = link.getAttribute('href') || '';
                    const onclick = link.getAttribute('onclick') || '';
                    const text = link.textContent.trim();
                    reports.push({href, onclick, text});
                });

                // Also look in all frames
                for (const frame of document.querySelectorAll('iframe')) {
                    try {
                        const fdoc = frame.contentDocument;
                        if (fdoc) {
                            fdoc.querySelectorAll('a[href*="REPORT"], a[onclick*="openReport"]').forEach(link => {
                                const href = link.getAttribute('href') || '';
                                const onclick = link.getAttribute('onclick') || '';
                                const text = link.textContent.trim();
                                reports.push({href, onclick, text, frame: frame.name || frame.id});
                            });
                        }
                    } catch(e) {}
                }
                return reports;
            }
        """)

        # Parse report IDs from the links
        for item in report_data:
            href = item.get("href", "")
            onclick = item.get("onclick", "")
            text = item.get("text", "")

            # Extract REPORT_ID from href or onclick
            rid_match = re.search(r"REPORT_ID=([^&\"']+)", href + onclick)
            if rid_match:
                report_id = rid_match.group(1)
                reports.append({"report_id": report_id, "text": text})

        log.info("Found %d spooled reports in index", len(reports))
        return reports

    async def spider_erp_menu(self) -> dict[str, Any]:
        """Spider the ERP by probing each known function code directly.

        The ERP uses a frameset-based layout; there's no single menu page.
        We probe each function code via /APPLOAD?APP=<code> and classify
        the response to build a complete system map.
        """
        log.info("Spidering ERP menu structure...")
        menu_map: dict[str, Any] = {}

        # Systematically test each known function code
        for module_name, functions in ERP_MODULES.items():
            log.info("Probing module: %s (%d functions)", module_name, len(functions))
            module_results: dict[str, Any] = {}

            for func_code in functions:
                item_key = f"spider_{module_name}_{func_code}"
                if self.checkpoint.is_completed(item_key):
                    log.debug("Skipping %s (already completed)", func_code)
                    continue

                self.checkpoint.mark_in_progress(item_key)
                try:
                    content = await retry_async(
                        self.navigate_to_function,
                        func_code,
                        operation_name=f"navigate_{func_code}",
                        max_retries=3,
                    )

                    # Classify the response
                    response_type = classify_response(content, func_code)

                    # Extract any sub-links/submenus from the page
                    sub_links = await self.page.evaluate("""
                        () => {
                            const links = [];
                            const allFrames = [document, ...Array.from(
                                document.querySelectorAll('iframe')
                            ).map(f => { try { return f.contentDocument } catch(e) { return null } }).filter(Boolean)];

                            for (const doc of allFrames) {
                                doc.querySelectorAll('a, button, input[type="submit"], [onclick]').forEach(el => {
                                    const text = el.textContent.trim().substring(0, 200);
                                    const href = el.getAttribute('href') || '';
                                    const onclick = el.getAttribute('onclick') || '';
                                    const type = el.tagName.toLowerCase();
                                    const name = el.getAttribute('name') || '';
                                    if (text || href || onclick) {
                                        links.push({text, href, onclick, type, name});
                                    }
                                });
                            }
                            return links;
                        }
                    """)

                    # Extract form fields
                    form_fields = await self.page.evaluate("""
                        () => {
                            const fields = [];
                            const allFrames = [document, ...Array.from(
                                document.querySelectorAll('iframe')
                            ).map(f => { try { return f.contentDocument } catch(e) { return null } }).filter(Boolean)];

                            for (const doc of allFrames) {
                                doc.querySelectorAll('input, select, textarea').forEach(el => {
                                    fields.push({
                                        type: el.type || el.tagName.toLowerCase(),
                                        name: el.name || '',
                                        id: el.id || '',
                                        value: el.value || '',
                                        placeholder: el.placeholder || '',
                                    });
                                });
                            }
                            return fields;
                        }
                    """)

                    module_results[func_code] = {
                        "url": self.page.url,
                        "response_type": response_type,
                        "content_length": len(content),
                        "sub_links_count": len(sub_links),
                        "form_fields_count": len(form_fields),
                        "sub_links": sub_links[:50],  # cap to avoid bloat
                        "form_fields": form_fields[:50],
                    }

                    self.checkpoint.mark_completed(item_key, {
                        "response_type": response_type,
                        "content_length": len(content),
                    })
                    log.info(
                        "  %s: %s (%d bytes, %d links, %d fields)",
                        func_code, response_type, len(content),
                        len(sub_links), len(form_fields),
                    )

                except Exception as e:
                    module_results[func_code] = {
                        "error": str(e),
                        "response_type": "error",
                    }
                    self.checkpoint.mark_failed(item_key, str(e))
                    log.warning("  %s: ERROR — %s", func_code, e)

            menu_map[module_name] = module_results

        return menu_map

    async def extract_all_cgi_data(self) -> dict[str, Any]:
        """Extract verbatim data from every accessible CGI function."""
        log.info("Extracting CGI data from all accessible functions...")
        CGI_DIR.mkdir(parents=True, exist_ok=True)

        results: dict[str, Any] = {}

        for module_name, functions in ERP_MODULES.items():
            for func_code in functions:
                item_key = f"cgi_extract_{func_code}"
                if self.checkpoint.is_completed(item_key):
                    continue

                self.checkpoint.mark_in_progress(item_key)
                try:
                    content = await retry_async(
                        self.navigate_to_function,
                        func_code,
                        operation_name=f"extract_{func_code}",
                        max_retries=3,
                    )

                    response_type = classify_response(content, func_code)

                    # Save the full HTML content
                    html_file = CGI_DIR / f"{func_code}_full.html"
                    html_file.write_text(content, encoding="utf-8")

                    # For BI reports, also try to extract REPORT.IFRAME data
                    report_data = None
                    if func_code in BI_FUNCTIONS or response_type == "bi_report":
                        report_data = await self.extract_report_iframe(func_code)
                        if report_data:
                            txt_file = CGI_DIR / f"{func_code}_report.txt"
                            txt_file.write_text(report_data, encoding="utf-8")
                            self.manifest.add_entry(
                                txt_file,
                                source="cgi_bi_report",
                                source_id=func_code,
                                data_type="text/plain",
                                extra={"module": module_name},
                            )

                    # Extract text content (no HTML tags)
                    text_content = extract_text_from_html(content)
                    if text_content.strip():
                        txt_file = CGI_DIR / f"{func_code}_text.txt"
                        txt_file.write_text(text_content, encoding="utf-8")

                    self.manifest.add_entry(
                        html_file,
                        source="cgi_function",
                        source_id=func_code,
                        data_type="text/html",
                        extra={
                            "module": module_name,
                            "response_type": response_type,
                            "has_report_data": report_data is not None,
                        },
                    )

                    results[func_code] = {
                        "response_type": response_type,
                        "content_length": len(content),
                        "report_data_length": len(report_data) if report_data else 0,
                        "file": str(html_file),
                    }

                    self.checkpoint.mark_completed(item_key, {
                        "size": len(content),
                        "type": response_type,
                    })
                    log.info(
                        "Extracted %s: %s (%d bytes)",
                        func_code, response_type, len(content),
                    )

                except Exception as e:
                    self.checkpoint.mark_failed(item_key, str(e))
                    results[func_code] = {"error": str(e)}
                    log.warning("Failed to extract %s: %s", func_code, e)

        return results

    async def extract_all_spooled_reports(self) -> dict[str, Any]:
        """Extract ALL spooled reports (full verbatim text)."""
        log.info("Extracting all spooled reports...")
        REPORT_DIR.mkdir(parents=True, exist_ok=True)

        # First get the report index
        report_index = await retry_async(
            self.get_spooled_report_index,
            operation_name="get_report_index",
        )

        # Also load previously discovered reports
        prev_index_file = BASE_DIR / "probe_results/deep_probe/exports/spooled_report_index_v2.json"
        if prev_index_file.exists():
            try:
                with open(prev_index_file, encoding="utf-8") as f:
                    prev_reports = json.load(f)
                    for pr in prev_reports:
                        rid = pr.get("report_id", "")
                        if rid and not any(r["report_id"] == rid for r in report_index):
                            report_index.append({"report_id": rid, "text": ""})
                log.info(
                    "Merged with previous index: %d total reports", len(report_index),
                )
            except (json.JSONDecodeError, OSError):
                pass

        results: dict[str, Any] = {}
        extracted_count = 0
        skipped_count = 0

        for report_entry in report_index:
            report_id = report_entry["report_id"]
            item_key = f"spooled_report_{report_id}"

            if self.checkpoint.is_completed(item_key):
                skipped_count += 1
                continue

            self.checkpoint.mark_in_progress(item_key)

            try:
                report_content = await retry_async(
                    self.extract_spooled_report,
                    report_id,
                    operation_name=f"report_{report_id}",
                    max_retries=3,
                )

                if report_content:
                    # Clean filename
                    safe_id = re.sub(r"[^a-zA-Z0-9._\-]", "_", report_id)
                    report_file = REPORT_DIR / f"{safe_id}.txt"
                    report_file.write_text(report_content, encoding="utf-8")

                    row_count = report_content.count("\n")
                    self.manifest.add_entry(
                        report_file,
                        source="spooled_report",
                        source_id=report_id,
                        data_type="text/plain",
                        row_count=row_count,
                    )

                    results[report_id] = {
                        "file": str(report_file),
                        "size_bytes": len(report_content.encode("utf-8")),
                        "line_count": row_count,
                    }
                    extracted_count += 1
                    self.checkpoint.mark_completed(item_key, {
                        "size": len(report_content),
                        "lines": row_count,
                    })
                    log.info(
                        "Report %s: %d bytes, %d lines",
                        report_id, len(report_content), row_count,
                    )
                else:
                    self.checkpoint.mark_failed(item_key, "No content returned")
                    results[report_id] = {"error": "No content"}

            except Exception as e:
                self.checkpoint.mark_failed(item_key, str(e))
                results[report_id] = {"error": str(e)}
                log.warning("Report %s failed: %s", report_id, e)

        log.info(
            "Spooled reports: %d extracted, %d skipped (checkpoint), %d failed",
            extracted_count, skipped_count,
            sum(1 for r in results.values() if "error" in r),
        )

        return results

    async def export_informer_reports(self) -> dict[str, Any]:
        """Export all Informer reports via browser CSV export."""
        log.info("Exporting Informer reports via CSV...")
        INFORMER_DIR.mkdir(parents=True, exist_ok=True)

        results: dict[str, Any] = {}

        # First check if Informer port is accessible
        informer_url = f"{INFORMER_BASE}/Informer.html?locale=en_US"

        for report_id in INFORMER_REPORT_IDS:
            item_key = f"informer_export_{report_id}"
            if self.checkpoint.is_completed(item_key):
                continue

            self.checkpoint.mark_in_progress(item_key)

            try:
                # Navigate to report
                await self.rate_limiter.wait()
                report_url = f"{informer_url}#action=ReportRun&reportId={report_id}"

                await self.page.goto(report_url, timeout=60000)
                await asyncio.sleep(5)

                # Wait for data to load
                try:
                    await self.page.wait_for_selector(
                        "table.informer-data-table, .data-table, table[class*='data']",
                        timeout=30000,
                    )
                except Exception:
                    log.warning("Report %d: no data table found", report_id)

                # Try to click "Export Results" button
                export_btn = self.page.locator(
                    'button:has-text("Export"), a:has-text("Export"), '
                    '[class*="export"], [title*="Export"]'
                )

                if await export_btn.count() > 0:
                    # Click export button first (may open dropdown)
                    await export_btn.first.click()
                    await asyncio.sleep(1)

                    # Look for CSV option in dropdown
                    csv_option = self.page.locator(
                        'a:has-text("CSV"), button:has-text("CSV"), '
                        '[data-format="csv"]'
                    )

                    if await csv_option.count() > 0:
                        # CSV option found — wrap only the download-triggering click
                        async with self.page.expect_download(timeout=30000) as download_info:
                            await csv_option.first.click()
                    else:
                        # No CSV option — export button may have triggered direct download
                        log.warning("Report %d: no CSV option found after Export click", report_id)
                        continue

                    download = await download_info.value
                    save_path = INFORMER_DIR / f"report_{report_id}.csv"
                    await download.save_as(str(save_path))

                    file_size = save_path.stat().st_size
                    with open(save_path, encoding="utf-8", errors="replace") as f:
                        row_count = max(0, sum(1 for _ in f) - 1)  # minus header

                    self.manifest.add_entry(
                        save_path,
                        source="informer_csv",
                        source_id=str(report_id),
                        data_type="text/csv",
                        row_count=row_count,
                    )

                    results[str(report_id)] = {
                        "file": str(save_path),
                        "size_bytes": file_size,
                        "row_count": row_count,
                    }
                    self.checkpoint.mark_completed(item_key, {
                        "size": file_size,
                        "rows": row_count,
                    })
                    log.info(
                        "Report %d: %d bytes, %d rows", report_id, file_size, row_count,
                    )
                else:
                    # No export button — extract table data directly
                    table_data = await self.page.evaluate("""
                        () => {
                            const rows = [];
                            const tables = document.querySelectorAll('table');
                            for (const table of tables) {
                                for (const row of table.rows) {
                                    const cells = [];
                                    for (const cell of row.cells) {
                                        cells.push(cell.textContent.trim());
                                    }
                                    rows.push(cells);
                                }
                            }
                            return rows;
                        }
                    """)

                    if table_data:
                        import csv
                        import io
                        output = io.StringIO()
                        writer = csv.writer(output)
                        for row in table_data:
                            writer.writerow(row)
                        csv_content = output.getvalue()

                        save_path = INFORMER_DIR / f"report_{report_id}_scraped.csv"
                        save_path.write_text(csv_content, encoding="utf-8")

                        self.manifest.add_entry(
                            save_path,
                            source="informer_table_scrape",
                            source_id=str(report_id),
                            data_type="text/csv",
                            row_count=len(table_data),
                        )

                        results[str(report_id)] = {
                            "file": str(save_path),
                            "size_bytes": len(csv_content),
                            "row_count": len(table_data),
                            "method": "table_scrape",
                        }
                        self.checkpoint.mark_completed(item_key)
                    else:
                        self.checkpoint.mark_failed(
                            item_key, "No export button or table data"
                        )
                        results[str(report_id)] = {"error": "No data found"}

            except Exception as e:
                self.checkpoint.mark_failed(item_key, str(e))
                results[str(report_id)] = {"error": str(e)}
                log.warning("Informer report %d failed: %s", report_id, e)

        return results

    async def check_admin_access(self) -> dict[str, Any]:
        """Check current user's access level by probing restricted functions."""
        log.info("Checking %s admin access level...", USERNAME)

        admin_functions = [
            "USER.ADMIN", "SYSTEM.ADMIN", "REPORT.ADMIN",
            "AP.INVOICE.ENTRY", "AR.CASH.RECEIPTS",
            "LABOR.ENTRY", "WO.ENTRY", "ORDER.ENTRY",
        ]

        results: dict[str, Any] = {"user": USERNAME, "access_level": "unknown"}
        accessible: list[str] = []
        denied: list[str] = []

        for func in admin_functions:
            try:
                content = await retry_async(
                    self.navigate_to_function,
                    func,
                    operation_name=f"admin_check_{func}",
                    max_retries=2,
                )
                if "NOT AUTHORIZED" in content.upper():
                    denied.append(func)
                elif "LOGIN.START" in self.page.url:
                    denied.append(func)
                else:
                    accessible.append(func)
                    log.info("  %s: ACCESSIBLE", func)
            except Exception as e:
                denied.append(func)
                log.warning("  %s: ERROR (%s)", func, e)

        results["accessible_admin_functions"] = accessible
        results["denied_admin_functions"] = denied
        results["is_admin"] = len(accessible) > len(denied)
        results["access_summary"] = (
            f"{len(accessible)}/{len(admin_functions)} admin functions accessible"
        )

        log.info(
            "Admin access check: %s (%s)",
            results["access_summary"],
            "ADMIN" if results["is_admin"] else "RESTRICTED",
        )

        return results


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def classify_response(content: str, function_code: str) -> str:
    """Classify the type of CGI response."""
    content_upper = content.upper()

    if "NOT AUTHORIZED" in content_upper:
        return "unauthorized"
    if "LOGIN.START" in content_upper and "USERNAME" in content_upper:
        return "login_redirect"
    if "EXCEEDED YOUR LICENSE QUOTA" in content_upper:
        return "license_quota"
    if "REPORT.IFRAME" in content or "REPORT.VIEW" in content:
        return "bi_report"
    if "<TABLE" in content_upper and ("<TR" in content_upper or "<TH" in content_upper):
        if content_upper.count("<TR") > 5:
            return "data_listing"
        return "form_with_table"
    if "<FORM" in content_upper:
        return "form"
    if "<PRE" in content_upper:
        return "preformatted"
    if len(content.strip()) < 200:
        return "minimal"
    return "other"


def extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML, stripping tags."""
    # Remove script and style content
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Replace common entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&nbsp;", " ").replace("&quot;", '"')
    # Strip tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse whitespace (but preserve newlines)
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        cleaned = re.sub(r"[ \t]+", " ", line).strip()
        if cleaned:
            cleaned_lines.append(cleaned)
    return "\n".join(cleaned_lines)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

async def verify_extraction() -> dict[str, Any]:
    """Verify all extracted data for integrity."""
    log.info("Verifying extraction integrity...")

    manifest = ExtractionManifest(MANIFEST_FILE)
    passed, failed, errors = manifest.verify_all()

    # Check directory sizes
    dir_stats: dict[str, Any] = {}
    for d_name, d_path in [
        ("spooled_reports", REPORT_DIR),
        ("informer_exports", INFORMER_DIR),
        ("cgi_data", CGI_DIR),
    ]:
        if d_path.exists():
            files = list(d_path.rglob("*"))
            file_count = sum(1 for f in files if f.is_file())
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            dir_stats[d_name] = {
                "file_count": file_count,
                "total_bytes": total_size,
                "total_mb": round(total_size / (1024 * 1024), 2),
            }

    checkpoint = CheckpointManager(CHECKPOINT_DIR)

    result = {
        "verification_time": datetime.now(timezone.utc).isoformat(),
        "manifest_checks": {
            "passed": passed,
            "failed": failed,
            "errors": errors,
        },
        "directory_stats": dir_stats,
        "checkpoint_summary": checkpoint.summary(),
    }

    if failed > 0:
        log.error("VERIFICATION FAILED: %d files have issues", failed)
        for err in errors:
            log.error("  %s", err)
    else:
        log.info("VERIFICATION PASSED: %d files OK", passed)

    return result


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

async def run_pipeline(mode: str) -> None:
    """Run the extraction pipeline in the specified mode."""
    log.info("=" * 70)
    log.info("KeyedIn Extraction Engine — Mode: %s", mode)
    log.info("Output directory: %s", OUTPUT_DIR)
    log.info("=" * 70)

    # Create directories
    for d in [OUTPUT_DIR, CHECKPOINT_DIR, REPORT_DIR, INFORMER_DIR, CGI_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    browser = KeyedInBrowser()

    try:
        await browser.connect()

        # Authenticate
        if not await browser.authenticate():
            log.error("Authentication failed — cannot proceed")
            return

        all_results: dict[str, Any] = {
            "engine_version": "2.0",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "user": USERNAME,
        }

        if mode in ("spider", "all"):
            log.info("PHASE: Spider ERP menu structure")
            menu_map = await browser.spider_erp_menu()
            SPIDER_MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SPIDER_MAP_FILE, "w", encoding="utf-8") as f:
                json.dump(menu_map, f, indent=2)
            all_results["spider"] = {
                "modules_mapped": len(menu_map),
                "file": str(SPIDER_MAP_FILE),
            }

        if mode in ("extract", "all"):
            log.info("PHASE: Extract CGI data")
            cgi_results = await browser.extract_all_cgi_data()
            all_results["cgi_extraction"] = {
                "total": len(cgi_results),
                "successful": sum(
                    1 for r in cgi_results.values() if "error" not in r
                ),
            }

        if mode in ("reports", "all"):
            log.info("PHASE: Extract spooled reports")
            report_results = await browser.extract_all_spooled_reports()
            all_results["spooled_reports"] = {
                "total": len(report_results),
                "successful": sum(
                    1 for r in report_results.values() if "error" not in r
                ),
            }

        if mode in ("informer", "all"):
            log.info("PHASE: Export Informer reports")
            informer_results = await browser.export_informer_reports()
            all_results["informer_exports"] = {
                "total": len(informer_results),
                "successful": sum(
                    1 for r in informer_results.values() if "error" not in r
                ),
            }

        if mode in ("admin", "all"):
            log.info("PHASE: Check admin access")
            admin_results = await browser.check_admin_access()
            all_results["admin_access"] = admin_results

        if mode in ("verify", "all"):
            log.info("PHASE: Verify extraction integrity")
            verify_results = await verify_extraction()
            all_results["verification"] = verify_results

        all_results["completed_at"] = datetime.now(timezone.utc).isoformat()
        all_results["checkpoint_summary"] = browser.checkpoint.summary()

        # Save final results
        results_file = OUTPUT_DIR / "extraction_results.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)

        log.info("=" * 70)
        log.info("Extraction complete. Results: %s", results_file)
        log.info("Checkpoint: %s", browser.checkpoint.summary())
        log.info("=" * 70)

    except Exception as e:
        log.error("Pipeline failed: %s", e)
        log.error(traceback.format_exc())
        raise
    finally:
        await browser.disconnect()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="KeyedIn Full-System Extraction Engine",
    )
    parser.add_argument(
        "--mode",
        choices=["spider", "extract", "reports", "informer", "admin", "verify", "all"],
        default="all",
        help="Extraction mode (default: all)",
    )
    args = parser.parse_args()
    asyncio.run(run_pipeline(args.mode))


if __name__ == "__main__":
    main()
