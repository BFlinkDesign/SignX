#!/usr/bin/env python3
"""
KeyedIn Resilient Agent - Production Ready
- Attach to running Chrome via CDP when available (reuse live session)
- Fall back to launching Chromium (with session persistence)
- Frame-aware login detection and lockout prevention
- Permanent ASCII-safe logging (no console Unicode errors)
- Service mode with health checks
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Optional .env support
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Playwright
try:
    from playwright.async_api import (
        async_playwright,
        Page,
        Browser,
        BrowserContext,
    )
except ImportError:
    print("ERROR: Playwright not installed. Run:\n  pip install playwright\n  python -m playwright install chromium")
    sys.exit(1)


# ====================
# Logging (permanent ASCII-safe)
# ====================

class SafeFileHandler(logging.FileHandler):
    """File handler that always uses UTF-8 encoding."""
    def __init__(self, filename: str, mode: str = "a"):
        super().__init__(filename, mode, encoding="utf-8")


class SafeConsoleHandler(logging.StreamHandler):
    """Console handler that converts Unicode symbols to ASCII if needed."""
    def __init__(self, stream=None):
        super().__init__(stream or sys.stdout)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Try original message
            super().emit(record)
        except UnicodeEncodeError:
            # Fallback to ASCII-safe message
            original_msg = record.getMessage()
            safe_msg = (original_msg
                        .replace("✓", "OK")
                        .replace("✗", "FAIL")
                        .replace("⚠", "WARN"))
            record.msg = safe_msg
            record.args = ()
            super().emit(record)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with safe handlers."""
    logger = logging.getLogger()
    logger.setLevel(level)
    # Remove existing handlers
    for h in logger.handlers[:]:
        logger.removeHandler(h)
    # Add safe handlers
    file_handler = SafeFileHandler("keyedin_agent.log")
    console_handler = SafeConsoleHandler(sys.stdout)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler.setFormatter(fmt)
    console_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


# ====================
# Config and helpers
# ====================

@dataclass
class AgentConfig:
    base_url: str = os.getenv("KEYEDIN_BASE_URL", "http://eaglesign.keyedinsign.com").rstrip("/")
    username: str = os.getenv("KEYEDIN_USERNAME", "")
    password: str = os.getenv("KEYEDIN_PASSWORD", "")
    storage_state: str = os.getenv("STORAGE_STATE", "keyedin_session.json")
    lockfile: str = os.getenv("LOCKFILE", ".keyedin_lock")
    headless: bool = os.getenv("HEADLESS", "true").lower() == "true"
    default_timeout: int = int(os.getenv("DEFAULT_TIMEOUT_MS", "15000"))
    login_backoff: int = int(os.getenv("LOGIN_BACKOFF_SECONDS", "45"))
    max_retries: int = int(os.getenv("MAX_LOGIN_RETRIES", "2"))
    service_interval: int = int(os.getenv("SERVICE_INTERVAL", "300"))
    cdp_port: int = int(os.getenv("CDP_PORT", "9222"))
    disable_images: bool = os.getenv("DISABLE_IMAGES", "true").lower() == "true"

    # Windows Chrome profile reuse (optional)
    chrome_user_data: Path = Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"
    chrome_profile: str = os.getenv("CHROME_PROFILE", "Default")


class Lockfile:
    def __init__(self, path: str):
        self.path = Path(path)
        self._owned = False

    def acquire(self, max_age_min: int = 30) -> bool:
        try:
            if self.path.exists():
                with self.path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                ts = datetime.fromisoformat(data.get("created", datetime.min.isoformat()))
                if datetime.now() - ts < timedelta(minutes=max_age_min):
                    return False
                self.path.unlink(missing_ok=True)
        except Exception:
            # Corrupt or unreadable lock -> remove
            self.path.unlink(missing_ok=True)

        self.path.write_text(json.dumps({
            "created": datetime.now().isoformat(),
            "pid": os.getpid(),
            "purpose": "keyedin_agent"
        }), encoding="utf-8")
        self._owned = True
        return True

    def release(self) -> None:
        if self._owned:
            self.path.unlink(missing_ok=True)
            self._owned = False


class SessionStore:
    def __init__(self, storage_path: str):
        self.file = Path(storage_path)

    def is_valid(self, max_age_hours: int = 24) -> bool:
        if not self.file.exists():
            return False
        try:
            data = json.loads(self.file.read_text(encoding="utf-8"))
            saved_at = datetime.fromisoformat(data.get("saved_at", datetime.min.isoformat()))
            return (datetime.now() - saved_at) < timedelta(hours=max_age_hours)
        except Exception:
            return False

    def load(self) -> Optional[Dict[str, Any]]:
        if not self.file.exists():
            return None
        try:
            data = json.loads(self.file.read_text(encoding="utf-8"))
            return data.get("storage_state")
        except Exception:
            return None

    def save(self, storage_state: Dict[str, Any]) -> None:
        payload = {
            "storage_state": storage_state,
            "saved_at": datetime.now().isoformat(),
        }
        self.file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def clear(self) -> None:
        self.file.unlink(missing_ok=True)


LOCKOUT_RE = re.compile(r"(too many attempts|locked|invalid credentials|access denied)", re.I)


# ====================
# Agent
# ====================

class KeyedInAgent:
    def __init__(self, cfg: AgentConfig):
        self.cfg = cfg
        self.lock = Lockfile(cfg.lockfile)
        self.session = SessionStore(cfg.storage_state)
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None

    # ---------- frame-aware helpers ----------

    async def _any_frame_has(self, selector: str, timeout_ms: int = 0) -> bool:
        """Return True if any frame has an element matching selector."""
        if not self.page:
            return False
        end = time.time() + (timeout_ms / 1000.0)
        while True:
            for fr in self.page.frames:
                try:
                    el = await fr.query_selector(selector)
                    if el:
                        return True
                except Exception:
                    pass
            if time.time() >= end or timeout_ms <= 0:
                break
            await asyncio.sleep(0.05)
        return False

    async def _text_in_any_frame(self, needle: str, timeout_ms: int = 0) -> bool:
        """Case-insensitive search for needle in any frame's visible text."""
        if not self.page:
            return False
        needle_l = (needle or "").lower()
        end = time.time() + (timeout_ms / 1000.0)
        while True:
            for fr in self.page.frames:
                try:
                    txt = await fr.evaluate("() => (document.body && document.body.innerText) || ''")
                    if needle_l in (txt or "").lower():
                        return True
                except Exception:
                    pass
            if time.time() >= end or timeout_ms <= 0:
                break
            await asyncio.sleep(0.05)
        return False

    # ---------- lifecycle ----------

    async def start(self) -> bool:
        """Start the agent and return success status."""
        try:
            if not self.lock.acquire():
                logging.error("Another agent instance is running (lock active)")
                return False

            # Windows subprocess handling policy
            if sys.platform.startswith("win"):
                try:
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                except Exception:
                    pass

            self.playwright = await async_playwright().start()

            # 1) Try CDP attach to existing Chrome
            self.browser = None
            try:
                endpoint = f"http://127.0.0.1:{self.cfg.cdp_port}"
                self.browser = await self.playwright.chromium.connect_over_cdp(endpoint)
                logging.info(f"Connected to existing Chrome over CDP at {endpoint}")
                contexts = self.browser.contexts
                if contexts:
                    ctx = contexts[0]
                else:
                    ctx = await self.browser.new_context()
                pages = ctx.pages
                self.page = pages[0] if pages else await ctx.new_page()
                self.page.set_default_timeout(self.cfg.default_timeout)
            except Exception as cdp_err:
                logging.info(f"CDP connect not available ({cdp_err}); launching fresh Chromium...")

            # 2) Fall back to launching a fresh Chromium
            if not self.browser:
                launch_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ]
                self.browser = await self.playwright.chromium.launch(
                    headless=self.cfg.headless,
                    args=launch_args
                )
                context_kwargs: Dict[str, Any] = {}
                if self.session.is_valid():
                    state = self.session.load()
                    if state:
                        context_kwargs["storage_state"] = state
                        logging.info("Loaded saved session")
                ctx = await self.browser.new_context(**context_kwargs)
                self.page = await ctx.new_page()
                self.page.set_default_timeout(self.cfg.default_timeout)

            if self.cfg.disable_images and self.page:
                await self.page.route(
                    "**/*.{png,jpg,jpeg,gif,svg,ico,webp,woff,woff2}",
                    lambda r: r.abort()
                )

            # Ensure logged in
            await self.ensure_logged_in()
            logging.info("Agent started successfully")
            return True

        except Exception as e:
            logging.error(f"Failed to start agent: {e}")
            await self.stop()
            return False

    async def stop(self) -> None:
        """Clean shutdown of agent."""
        try:
            if self.page:
                # Save session state when possible
                try:
                    state = await self.page.context.storage_state()
                    self.session.save(state)
                except Exception:
                    pass
                await self.page.close()
        except Exception:
            pass

        try:
            if self.browser:
                # Let transports flush on Windows
                await asyncio.sleep(0.1)
                await self.browser.close()
        except Exception:
            pass

        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        finally:
            self.lock.release()

    # ---------- auth ----------

    async def is_logged_in(self) -> bool:
        """Check if currently logged into KeyedIn (frame-aware)."""
        if not self.page:
            return False
        try:
            if await self._any_frame_has("text=Logout", timeout_ms=1200):
                return True
            found_welcome = await self._text_in_any_frame("Welcome,", timeout_ms=600)
            found_profile = await self._text_in_any_frame("Profile", timeout_ms=0)
            found_password = await self._text_in_any_frame("Password", timeout_ms=0)
            found_logout = await self._text_in_any_frame("Logout", timeout_ms=0)
            return found_welcome and found_profile and found_password and found_logout
        except Exception:
            return False

    async def has_lockout(self) -> bool:
        """Check for lockout messages (frame-aware)."""
        if not self.page:
            return False
        try:
            for fr in self.page.frames:
                try:
                    txt = await fr.evaluate("() => (document.body && document.body.innerText) || ''")
                    if txt and LOCKOUT_RE.search(txt.lower()):
                        return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    async def ensure_logged_in(self) -> bool:
        """Ensure we are logged into KeyedIn."""
        if not self.page:
            return False

        await self.page.goto(f"{self.cfg.base_url}/cgi-bin/mvi.exe/LOGIN.START", wait_until="domcontentloaded")

        if await self.is_logged_in():
            logging.info("Already logged in")
            return True

        if await self.has_lockout():
            logging.error("Account locked - too many attempts")
            return False

        return await self.perform_login()

    async def perform_login(self) -> bool:
        """Perform login with improved form detection and fallbacks."""
        if not self.page:
            return False

        # Allow dynamic content settle, then re-check
        await self.page.wait_for_timeout(1000)
        if await self.is_logged_in():
            logging.info("Already authenticated after page settle")
            try:
                state = await self.page.context.storage_state()
                self.session.save(state)
            except Exception:
                pass
            return True

        frame = None
        user = None
        pw = None

        password_selectors = [
            "input[type='password']",
            "input[name='PASSWORD']",
            "input#PASSWORD",
        ]
        user_selectors = [
            "input[name='USERNAME']",
            "input#USERNAME",
            "input[type='text']",
        ]

        # Retry find form fields across all frames
        deadline = time.time() + 3.0
        while time.time() < deadline and not (frame and user and pw):
            for fr in self.page.frames:
                try:
                    cand_pw = None
                    for sel in password_selectors:
                        cand_pw = await fr.query_selector(sel)
                        if cand_pw:
                            break
                    if not cand_pw:
                        continue

                    cand_user = None
                    for sel in user_selectors:
                        cand_user = await fr.query_selector(sel)
                        if cand_user:
                            break

                    if cand_user:
                        frame, user, pw = fr, cand_user, cand_pw
                        logging.info("Found login form")
                        break
                except Exception:
                    continue

            if not (frame and user and pw):
                await self.page.wait_for_timeout(200)

        if not (frame and user and pw):
            if await self.is_logged_in():
                logging.info("Authenticated (no login form present)")
                try:
                    state = await self.page.context.storage_state()
                    self.session.save(state)
                except Exception:
                    pass
                return True
            logging.error("Login form not found")
            return False

        # Fill credentials or use autofill
        try:
            if not self.cfg.headless:
                await user.click()
                await self.page.wait_for_timeout(800)
                if await pw.input_value():
                    logging.info("Using Chrome autofill")
                else:
                    if not (self.cfg.username and self.cfg.password):
                        logging.error("No credentials available")
                        return False
                    await user.fill(self.cfg.username)
                    await pw.fill(self.cfg.password)
                    logging.info("Using manual credentials")
            else:
                if not (self.cfg.username and self.cfg.password):
                    logging.error("Headless mode requires credentials in environment or .env")
                    return False
                await user.fill(self.cfg.username)
                await pw.fill(self.cfg.password)

            # Submit
            submit = await frame.query_selector("#btnLogin, input[type='submit'], button[type='submit']")
            if submit:
                await submit.click()
            else:
                await pw.press("Enter")

            await self.page.wait_for_timeout(3000)

            if await self.has_lockout():
                logging.error("Login failed - account locked")
                return False

            if await self.is_logged_in():
                logging.info("Login successful")
                try:
                    state = await self.page.context.storage_state()
                    self.session.save(state)
                except Exception:
                    pass
                return True

            logging.error("Login failed - invalid credentials or unexpected response")
            return False

        except Exception as e:
            logging.error(f"Login error: {e}")
            return False

    # ---------- navigation and data ----------

    async def navigate_to_module(self, module_path: str) -> bool:
        """Navigate to a specific KeyedIn module path."""
        if not self.page:
            return False
        try:
            url = f"{self.cfg.base_url}{module_path}"
            await self.page.goto(url, wait_until="domcontentloaded")
            await self.page.wait_for_load_state("networkidle", timeout=10000)

            # Settle and verify still authenticated
            if not await self.is_logged_in():
                await self.page.wait_for_timeout(400)
                if not await self.is_logged_in():
                    logging.warning("Lost login after navigation, re-authenticating...")
                    return await self.ensure_logged_in()

            return True
        except Exception as e:
            logging.error(f"Navigation failed: {e}")
            return False

    async def extract_table_data(self, table_selector: str = "table") -> List[List[str]]:
        """Extract data from the first table matching selector."""
        if not self.page:
            return []
        try:
            tables = await self.page.query_selector_all(table_selector)
            if not tables:
                return []
            table = tables[0]
            data = await table.evaluate('''
                table => {
                    const rows = Array.from(table.querySelectorAll('tr'));
                    return rows.map(row => {
                        const cells = Array.from(row.querySelectorAll('td, th'));
                        return cells.map(cell => (cell.innerText || '').trim());
                    }).filter(r => r.length > 0);
                }
            ''')
            return data or []
        except Exception as e:
            logging.error(f"Table extraction failed: {e}")
            return []


# ====================
# CLI
# ====================

async def run_once(args: argparse.Namespace) -> int:
    """Run the agent once for testing."""
    setup_logging(logging.DEBUG if not AgentConfig().headless else logging.INFO)
    cfg = AgentConfig()
    agent = KeyedInAgent(cfg)
    try:
        if not await agent.start():
            return 2

        success = await agent.navigate_to_module("/cgi-bin/mvi.exe/PROJECTS.LIST")
        if success:
            data = await agent.extract_table_data()
            print(f"Found {len(data)} rows of project data")
            print("Agent test successful")
            return 0
        else:
            print("Navigation failed")
            return 1
    finally:
        await agent.stop()


async def service_loop(args: argparse.Namespace) -> int:
    """Run the agent as a background service with periodic health checks."""
    setup_logging(logging.INFO)
    cfg = AgentConfig()
    agent = KeyedInAgent(cfg)
    try:
        if not await agent.start():
            return 2

        logging.info("Service started - monitoring KeyedIn connection")
        while True:
            try:
                if not await agent.is_logged_in():
                    logging.warning("Session expired, re-authenticating...")
                    if not await agent.ensure_logged_in():
                        logging.error("Re-authentication failed, backing off...")
                        await asyncio.sleep(cfg.login_backoff)
                        continue
                logging.info("Health check passed")
                await asyncio.sleep(cfg.service_interval)
            except KeyboardInterrupt:
                logging.info("Service stopped by user")
                break
            except Exception as e:
                logging.error(f"Service error: {e}")
                await asyncio.sleep(60)
    finally:
        await agent.stop()
    return 0


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser("keyedin_resilient_agent")
    ap.add_argument("--run-once", action="store_true", help="Run once for testing")
    ap.add_argument("--service", action="store_true", help="Run as background service")
    ap.add_argument("--clear-session", action="store_true", help="Clear saved session")
    ap.add_argument("--selftest", action="store_true", help="Run self-test")
    return ap.parse_args()


def selftest() -> int:
    print("KeyedIn Agent Self-Test")
    print("=" * 30)
    # Dependencies
    try:
        from playwright.async_api import async_playwright  # noqa
        print("OK: Playwright installed")
    except ImportError:
        print("FAIL: Playwright not installed")
        return 1
    # Config
    cfg = AgentConfig()
    if cfg.base_url:
        print(f"OK: Base URL configured: {cfg.base_url}")
    else:
        print("WARN: No base URL configured")
    if cfg.username and cfg.password:
        print("OK: Credentials configured")
    else:
        print("INFO: No credentials in environment; will try autofill/CDP")
    print("Self-test completed")
    return 0


def main() -> int:
    args = parse_args()

    if args.selftest:
        return selftest()

    if args.clear_session:
        SessionStore(AgentConfig().storage_state).clear()
        print("Session cleared")
        return 0

    if args.service:
        return asyncio.run(service_loop(args))
    else:
        return asyncio.run(run_once(args))


if __name__ == "__main__":
    # Best-effort: prefer UTF-8 console if possible (safe fallback exists)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    # Windows event loop policy for subprocess transports
    if sys.platform.startswith("win"):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass
    sys.exit(main())
