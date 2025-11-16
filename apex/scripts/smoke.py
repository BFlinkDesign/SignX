from __future__ import annotations
import json, sys, time
import urllib.request

URL = "http://localhost:8000/health"
for _ in range(30):
    try:
        with urllib.request.urlopen(URL, timeout=2) as r:
            data = json.loads(r.read().decode())
            assert data.get("result", {}).get("status") == "ok"
            assert 0.0 <= data.get("confidence", 0.0) <= 1.0
            print(json.dumps({"ok": True, "endpoint": URL, "confidence": data["confidence"]}, indent=2))
            sys.exit(0)
    except Exception:
        time.sleep(1)
print(json.dumps({"ok": False, "endpoint": URL}, indent=2))
sys.exit(1)


