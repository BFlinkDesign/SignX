"""
mail_processor.py — Win32com Outlook polling loop for Eagle Sign email intake.

Single-threaded poller designed to be wrapped as a Windows Service via NSSM.
Polls Inbox/BID REQUEST/{salesperson}/ every 60 seconds, classifies emails
via mail_classifier, deduplicates via mail_state, and triggers auto-takeoff.

CLI modes:
    python mail_processor.py            # Start polling loop
    python mail_processor.py --once     # Process once and exit
    python mail_processor.py --dry-run  # Classify only, no Notion writes
    python mail_processor.py --status   # Print stats from mail_state.db
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

import requests as http_requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SALESPERSON_FOLDERS = ["Jeff Fye", "Joe Phillips", "Rich Thompson", "House"]
POLL_INTERVAL = 60  # seconds
LOOKBACK_DAYS = 7
MAX_COM_RETRIES = 3
TAKEOFF_BASE_URL = "http://localhost:8765"
HTTP_TIMEOUT = 30

DATA_DIR = Path(__file__).parent / "data"
LOG_PATH = DATA_DIR / "mail_processor.log"

# MAPI property tag for Internet Message ID
PR_INTERNET_MESSAGE_ID = "http://schemas.microsoft.com/mapi/proptag/0x1035001E"

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def _setup_logging() -> logging.Logger:
    """Configure console + rotating file logger."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("mail_processor")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (NSSM captures stdout)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Rotating file handler: 5 MB x 3 backups
    fh = RotatingFileHandler(
        str(LOG_PATH), maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


log = _setup_logging()

# ---------------------------------------------------------------------------
# COM helpers
# ---------------------------------------------------------------------------


def _init_com():
    """Initialize COM apartment for this thread. Returns pythoncom module."""
    import pythoncom

    pythoncom.CoInitialize()
    return pythoncom


def _uninit_com(pythoncom_mod):
    """Uninitialize COM apartment. Safe to call even if not initialized."""
    try:
        pythoncom_mod.CoUninitialize()
    except Exception:
        pass


def _connect_outlook(max_retries: int = MAX_COM_RETRIES):
    """
    Connect to Outlook MAPI with retry logic.
    Returns (outlook, namespace, bid_request_folder, pythoncom_mod).
    Raises RuntimeError after max_retries exhausted.
    """
    import win32com.client

    last_err = None
    for attempt in range(1, max_retries + 1):
        pythoncom_mod = None
        try:
            pythoncom_mod = _init_com()
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")
            inbox = namespace.GetDefaultFolder(6)  # olFolderInbox
            bid_request_folder = inbox.Folders["BID REQUEST"]
            log.info(
                "COM connected (attempt %d/%d)", attempt, max_retries
            )
            return outlook, namespace, bid_request_folder, pythoncom_mod
        except Exception as exc:
            last_err = exc
            log.warning(
                "COM connect attempt %d/%d failed: %s", attempt, max_retries, exc
            )
            if pythoncom_mod:
                _uninit_com(pythoncom_mod)
            if attempt < max_retries:
                time.sleep(2)

    raise RuntimeError(
        f"Failed to connect to Outlook after {max_retries} attempts: {last_err}"
    )


# ---------------------------------------------------------------------------
# Email extraction
# ---------------------------------------------------------------------------


def _get_message_id(item) -> str | None:
    """Extract Internet Message-ID via PropertyAccessor."""
    try:
        return item.PropertyAccessor.GetProperty(PR_INTERNET_MESSAGE_ID)
    except Exception:
        return None


def _get_attachments(item) -> list[str]:
    """Get list of attachment filenames."""
    names = []
    try:
        for att in item.Attachments:
            names.append(att.FileName)
    except Exception:
        pass
    return names


def _get_received_iso(item) -> str:
    """Get ReceivedTime as ISO string."""
    try:
        if hasattr(item, "ReceivedTime") and item.ReceivedTime:
            return item.ReceivedTime.isoformat()
    except Exception:
        pass
    return datetime.now().isoformat()


# ---------------------------------------------------------------------------
# Auto-takeoff + SMS trigger
# ---------------------------------------------------------------------------


def _trigger_takeoff(page_id: str, customer: str, quote_name: str, quote_number: str = "") -> None:
    """POST to SignX-Takeoff to trigger auto-estimation and SMS notification."""
    # Auto-takeoff
    try:
        resp = http_requests.post(
            f"{TAKEOFF_BASE_URL}/api/notion/takeoff",
            json={"page_id": page_id},
            timeout=HTTP_TIMEOUT,
        )
        if resp.ok:
            log.info("Auto-takeoff triggered for page %s", page_id)
        else:
            log.warning(
                "Auto-takeoff returned %d: %s", resp.status_code, resp.text[:200]
            )
    except Exception as exc:
        log.warning("Auto-takeoff request failed: %s", exc)

    # SMS notification
    try:
        msg = f"New bid: {customer or 'Unknown'} - {quote_name or 'New Bid'}"
        resp = http_requests.post(
            f"{TAKEOFF_BASE_URL}/api/notify/bid-ready",
            json={
                "quote_number": quote_number,
                "customer": customer or "Unknown",
                "total_hours": 0.0,
                "estimator_type": "pending",
                "message": msg,
            },
            timeout=HTTP_TIMEOUT,
        )
        if resp.ok:
            log.info("SMS notification sent for %s", quote_name)
        else:
            log.warning(
                "SMS notify returned %d: %s", resp.status_code, resp.text[:200]
            )
    except Exception as exc:
        log.warning("SMS notify request failed: %s", exc)


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------


def process_folder(folder, folder_name: str, dry_run: bool = False) -> dict:
    """
    Process all unprocessed emails in a single salesperson folder.
    Returns {"processed": N, "skipped": N, "errors": N}.
    """
    from mail_state import is_processed, mark_processed
    from mail_classifier import classify_and_route

    stats = {"processed": 0, "skipped": 0, "errors": 0}

    try:
        items = folder.Items

        # Restrict to last LOOKBACK_DAYS days
        cutoff = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime(
            "%m/%d/%Y %H:%M %p"
        )
        restricted = items.Restrict(f"[ReceivedTime] > '{cutoff}'")
        restricted.Sort("[ReceivedTime]", True)  # Descending

        for item in restricted:
            try:
                # Only MailItems (Class 43)
                if item.Class != 43:
                    continue

                # Deduplicate by Internet Message-ID
                msg_id = _get_message_id(item)
                if not msg_id:
                    # Fallback: use subject + received as ID
                    msg_id = f"{item.Subject or ''}|{_get_received_iso(item)}"

                if is_processed(msg_id):
                    stats["skipped"] += 1
                    continue

                # Extract fields
                subject = item.Subject or ""
                sender = item.SenderName or ""
                body = ""
                try:
                    body = item.Body or ""
                except Exception:
                    pass
                received = _get_received_iso(item)
                attachments = _get_attachments(item)

                log.info(
                    "Processing: [%s] %s from %s (%s)",
                    folder_name,
                    subject[:80],
                    sender,
                    received[:10],
                )

                if dry_run:
                    # Classify but don't persist
                    from mail_classifier import BID_INTAKE_PATTERN

                    is_bid = bool(BID_INTAKE_PATTERN.search(subject))
                    log.info(
                        "  DRY-RUN: would classify as %s",
                        "bid_intake" if is_bid else "correspondence",
                    )
                    stats["processed"] += 1
                    continue

                # Classify and route (writes to Notion)
                result = classify_and_route(
                    subject=subject,
                    body=body,
                    sender=sender,
                    received=received,
                    folder=folder_name,
                    attachments=attachments,
                )

                flow = result.get("flow", "unknown")

                # If Notion creation failed, do NOT mark as processed (retry next loop)
                if "notion_error" in result and result.get("notion_page_id") is None:
                    log.error(
                        "  Notion failed for %s: %s — will retry",
                        subject[:60],
                        result["notion_error"],
                    )
                    stats["errors"] += 1
                    continue

                # Mark as processed
                mark_processed(
                    internet_message_id=msg_id,
                    flow=flow,
                    folder=folder_name,
                    subject=subject,
                    sender=sender,
                    result_json=json.dumps(result, default=str),
                )

                # Mark email as read
                try:
                    item.UnRead = False
                    item.Save()
                except Exception as exc:
                    log.warning("  Failed to mark as read: %s", exc)

                # Trigger auto-takeoff for bid intake
                page_id = result.get("notion_page_id")
                if flow == "bid_intake" and page_id:
                    _trigger_takeoff(
                        page_id=page_id,
                        customer=result.get("customer", ""),
                        quote_name=result.get("quote_name", ""),
                        quote_number=result.get("quote_number", ""),
                    )

                log.info(
                    "  OK: flow=%s, notion_page=%s",
                    flow,
                    page_id or "none",
                )
                stats["processed"] += 1

            except Exception as exc:
                log.error("  Error processing email: %s", exc, exc_info=True)
                stats["errors"] += 1
                continue

    except Exception as exc:
        log.error("Error accessing folder %s: %s", folder_name, exc, exc_info=True)
        stats["errors"] += 1

    return stats


def process_all_folders(bid_request_folder, dry_run: bool = False) -> dict:
    """Process all salesperson subfolders. Returns aggregate stats."""
    totals = {"processed": 0, "skipped": 0, "errors": 0}

    for folder_name in SALESPERSON_FOLDERS:
        try:
            folder = bid_request_folder.Folders[folder_name]
        except Exception:
            log.warning("Folder not found: BID REQUEST/%s — skipping", folder_name)
            continue

        stats = process_folder(folder, folder_name, dry_run=dry_run)
        for k in totals:
            totals[k] += stats[k]

        log.debug(
            "Folder %s: processed=%d, skipped=%d, errors=%d",
            folder_name,
            stats["processed"],
            stats["skipped"],
            stats["errors"],
        )

    return totals


# ---------------------------------------------------------------------------
# Polling loop
# ---------------------------------------------------------------------------


def run_loop(dry_run: bool = False) -> None:
    """Main polling loop. Runs until interrupted."""
    from mail_state import init_db

    init_db()
    log.info(
        "Mail processor starting — poll=%ds, lookback=%dd, dry_run=%s",
        POLL_INTERVAL,
        LOOKBACK_DAYS,
        dry_run,
    )

    while True:
        pythoncom_mod = None
        try:
            outlook, namespace, bid_request_folder, pythoncom_mod = _connect_outlook()
            totals = process_all_folders(bid_request_folder, dry_run=dry_run)
            log.info(
                "Poll complete: processed=%d, skipped=%d, errors=%d",
                totals["processed"],
                totals["skipped"],
                totals["errors"],
            )
        except Exception as exc:
            log.error("Poll cycle failed: %s", exc, exc_info=True)
        finally:
            if pythoncom_mod:
                _uninit_com(pythoncom_mod)

        log.debug("Sleeping %d seconds...", POLL_INTERVAL)
        time.sleep(POLL_INTERVAL)


def run_once(dry_run: bool = False) -> None:
    """Process once and exit."""
    from mail_state import init_db

    init_db()
    log.info("Mail processor — single pass (dry_run=%s)", dry_run)

    pythoncom_mod = None
    try:
        outlook, namespace, bid_request_folder, pythoncom_mod = _connect_outlook()
        totals = process_all_folders(bid_request_folder, dry_run=dry_run)
        log.info(
            "Done: processed=%d, skipped=%d, errors=%d",
            totals["processed"],
            totals["skipped"],
            totals["errors"],
        )
    except Exception as exc:
        log.error("Processing failed: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        if pythoncom_mod:
            _uninit_com(pythoncom_mod)


def print_status() -> None:
    """Print stats from mail_state.db and exit."""
    from mail_state import init_db, get_stats, get_recent_emails

    init_db()
    stats = get_stats()

    print(f"\n{'='*50}")
    print(f"  Mail Processor Status")
    print(f"{'='*50}")
    print(f"  Total processed:  {stats['total']}")
    print(f"\n  By flow:")
    for flow, cnt in sorted(stats["by_flow"].items()):
        print(f"    {flow:20s}  {cnt}")
    print(f"\n  By folder:")
    for folder, cnt in sorted(stats["by_folder"].items()):
        print(f"    {folder:20s}  {cnt}")

    recent = get_recent_emails(days=1)
    if recent:
        print(f"\n  Last 24h: {len(recent)} emails")
        for r in recent[:5]:
            print(f"    [{r['flow']}] {r['subject'][:60]}")
    else:
        print(f"\n  Last 24h: 0 emails")
    print(f"{'='*50}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Eagle Sign email intake processor"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process once and exit (no polling loop)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Classify emails but don't write to Notion or mark processed",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print processing stats and exit",
    )
    args = parser.parse_args()

    if args.status:
        print_status()
        return

    if args.once:
        run_once(dry_run=args.dry_run)
    else:
        try:
            run_loop(dry_run=args.dry_run)
        except KeyboardInterrupt:
            log.info("Shutting down (KeyboardInterrupt)")
            sys.exit(0)


if __name__ == "__main__":
    main()
