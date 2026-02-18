"""
mail_state.py — SQLite state management for email intake engine.

Tables:
  processed_emails   — dedup tracking (keyed on internet_message_id)
  follow_up_timers   — 48-hour follow-up reminders for quoted bids
  closeout_variance  — future: auto-pull variance when job closes

All functions are synchronous; callers wrap with asyncio.to_thread().
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "mail_state.db"

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    """Return a module-level connection, creating it on first call."""
    global _conn
    if _conn is None:
        os.makedirs(DB_PATH.parent, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
    return _conn


# ── schema ──────────────────────────────────────────────────────────

def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS processed_emails (
            internet_message_id TEXT PRIMARY KEY,
            processed_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
            flow                TEXT NOT NULL,
            folder              TEXT NOT NULL,
            subject             TEXT,
            sender              TEXT,
            result_json         TEXT
        );

        CREATE TABLE IF NOT EXISTS follow_up_timers (
            bid_page_id    TEXT PRIMARY KEY,
            quote_name     TEXT,
            customer       TEXT,
            salesman       TEXT,
            quoted_at      DATETIME,
            reminder_sent_at DATETIME,
            status         TEXT DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS closeout_variance (
            work_order      TEXT PRIMARY KEY,
            quote_number    TEXT,
            estimated_total REAL,
            actual_total    REAL,
            variance_pct    REAL,
            computed_at     DATETIME
        );
    """)
    conn.commit()


# ── processed_emails ────────────────────────────────────────────────

def is_processed(internet_message_id: str) -> bool:
    """Check whether an email has already been processed."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT 1 FROM processed_emails WHERE internet_message_id = ?",
        (internet_message_id,),
    ).fetchone()
    return row is not None


def mark_processed(
    internet_message_id: str,
    flow: str,
    folder: str,
    subject: str | None = None,
    sender: str | None = None,
    result_json: str | None = None,
) -> None:
    """Record an email as processed (upsert)."""
    conn = _get_conn()
    conn.execute(
        """INSERT INTO processed_emails
               (internet_message_id, flow, folder, subject, sender, result_json)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(internet_message_id) DO UPDATE SET
               processed_at = CURRENT_TIMESTAMP,
               flow         = excluded.flow,
               folder       = excluded.folder,
               subject      = excluded.subject,
               sender       = excluded.sender,
               result_json  = excluded.result_json
        """,
        (internet_message_id, flow, folder, subject, sender, result_json),
    )
    conn.commit()


def get_recent_emails(days: int = 7) -> list[dict]:
    """Return emails processed within the last *days* days, newest first."""
    conn = _get_conn()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """SELECT internet_message_id, processed_at, flow, folder,
                  subject, sender, result_json
           FROM processed_emails
           WHERE processed_at >= ?
           ORDER BY processed_at DESC""",
        (cutoff,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    """Return aggregate stats: total count, per-flow breakdown, per-folder."""
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM processed_emails").fetchone()[0]

    by_flow = {}
    for row in conn.execute(
        "SELECT flow, COUNT(*) AS cnt FROM processed_emails GROUP BY flow"
    ):
        by_flow[row["flow"]] = row["cnt"]

    by_folder = {}
    for row in conn.execute(
        "SELECT folder, COUNT(*) AS cnt FROM processed_emails GROUP BY folder"
    ):
        by_folder[row["folder"]] = row["cnt"]

    return {"total": total, "by_flow": by_flow, "by_folder": by_folder}


# ── follow_up_timers ───────────────────────────────────────────────

def add_follow_up(
    bid_page_id: str,
    quote_name: str,
    customer: str,
    salesman: str,
    quoted_at: str | None = None,
) -> None:
    """Insert or replace a follow-up timer for a quoted bid."""
    conn = _get_conn()
    if quoted_at is None:
        quoted_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO follow_up_timers
               (bid_page_id, quote_name, customer, salesman, quoted_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(bid_page_id) DO UPDATE SET
               quote_name = excluded.quote_name,
               customer   = excluded.customer,
               salesman   = excluded.salesman,
               quoted_at  = excluded.quoted_at,
               status     = 'active',
               reminder_sent_at = NULL
        """,
        (bid_page_id, quote_name, customer, salesman, quoted_at),
    )
    conn.commit()


def get_pending_follow_ups(hours_threshold: int = 48) -> list[dict]:
    """Return active follow-ups where quoted_at is older than *hours_threshold*."""
    conn = _get_conn()
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=hours_threshold)
    ).isoformat()
    rows = conn.execute(
        """SELECT bid_page_id, quote_name, customer, salesman, quoted_at
           FROM follow_up_timers
           WHERE status = 'active' AND quoted_at <= ?
           ORDER BY quoted_at ASC""",
        (cutoff,),
    ).fetchall()
    return [dict(r) for r in rows]


def mark_follow_up_sent(bid_page_id: str) -> None:
    """Mark a follow-up reminder as sent."""
    conn = _get_conn()
    conn.execute(
        """UPDATE follow_up_timers
           SET reminder_sent_at = ?, status = 'reminded'
           WHERE bid_page_id = ?""",
        (datetime.now(timezone.utc).isoformat(), bid_page_id),
    )
    conn.commit()
