import os, sys, time, signal, threading, logging, argparse, json
from http.server import BaseHTTPRequestHandler, HTTPServer
from logging.handlers import RotatingFileHandler

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*args, **kwargs): pass

# --- Paths
FROZEN = getattr(sys, "frozen", False)
BASE_DIR = os.path.dirname(sys.executable) if FROZEN else os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "keyedin_agent.log")

# --- Logging
logger = logging.getLogger("keyedin_agent")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=5)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)

# --- State for health
state = {"start_ts": time.time(), "ticks": 0}
stop_event = threading.Event()

class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/health"):
            payload = {
                "status": "ok",
                "uptime_s": int(time.time() - self.server.start_ts),
                "ticks": self.server.state["ticks"],
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args, **kwargs):
        # Silence default HTTPServer console logging
        logger.debug("HTTP: " + " ".join(str(a) for a in args))

def start_health_server(port: int):
    if port <= 0:
        return None, None
    srv = HTTPServer(("127.0.0.1", port), _HealthHandler)
    srv.start_ts = state["start_ts"]
    srv.state = state
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    logger.info(f"Health server listening on http://127.0.0.1:{port}/health")
    return srv, th

def handle_signal(sig, frame):
    logger.info(f"Signal {sig} received; shutting down...")
    stop_event.set()

for s in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None), getattr(signal, "SIGBREAK", None)):
    if s is not None:
        try:
            signal.signal(s, handle_signal)
        except Exception:
            pass

def do_work_once() -> bool:
    """Put your Playwright/UI automation here."""
    state["ticks"] += 1
    browsers = os.getenv("PLAYWRIGHT_BROWSERS_PATH", "(not set)")
    logger.info(f"Tick #{state['ticks']}  PLAYWRIGHT_BROWSERS_PATH={browsers}")
    # TODO: real automation goes here
    return True

def service_loop(interval_s: int):
    logger.info(f"Service loop started; interval={interval_s}s")
    while not stop_event.is_set():
        try:
            ok = do_work_once()
            if not ok:
                logger.error("Work returned failure; sleeping before retry")
        except Exception as e:
            logger.exception("Unhandled exception in work loop: %s", e)
        finally:
            stop_event.wait(interval_s)
    logger.info("Service loop exiting")

def main():
    # Load .env from install dir if present
    try:
        load_dotenv(os.path.join(BASE_DIR, ".env"))
    except Exception:
        pass

    parser = argparse.ArgumentParser(prog="KeyedInAgent")
    parser.add_argument("--service", action="store_true", help="Run continuous service loop")
    parser.add_argument("--interval", type=int, default=int(os.getenv("SERVICE_INTERVAL", "300")), help="Loop interval seconds")
    parser.add_argument("--health-port", type=int, default=int(os.getenv("HEALTH_PORT", "0")), help="Expose /health on this port (0=disabled)")
    parser.add_argument("--once", action="store_true", help="Run one iteration and exit (smoke test)")
    args = parser.parse_args()

    srv = None
    try:
        srv, _ = start_health_server(args.health_port)

        if args.service:
            service_loop(args.interval)
        else:
            # Default to a quick smoke test so post-install doesn't hang.
            if not args.once:
                logger.info("No --service flag; performing one-shot smoke test and exiting.")
            do_work_once()
            logger.info("One-shot run complete.")
    finally:
        if srv:
            try:
                srv.shutdown()
            except Exception:
                pass

if __name__ == "__main__":
    main()
