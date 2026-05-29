"""St. Anthony 40398 — CorelDRAW .CDR geometry extractor (Phase D step 1).

Attaches to the RUNNING CorelDRAW instance (does not relaunch), opens the
40398 autobackup read-only-ish, walks every page/layer/shape recursively,
and dumps bbox (inches) + text to JSON. Closes the opened doc WITHOUT saving
and restores the previously-active document. Never calls app.Quit().

Output: cdr_geometry_raw.json + a console summary of candidate dimensions.
NOTHING is fed to any engine here — this is the Brady checkpoint artifact.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CDR = r"C:\Temp\AUTOBACKUP_OF_ST ANTHONY MON 7X12 6MM EMC 1125-40398 X.CDR"
OUT = Path(__file__).parent / "cdr_geometry_raw.json"
SHAPE_LIMIT = 12000
TIME_BUDGET_S = 200

import win32com.client  # noqa: E402

t0 = time.time()
shapes_out: list[dict] = []
errors: list[str] = []
count = 0


def walk(coll, page_name: str, depth: int = 0) -> None:
    global count
    for s in coll:
        if count >= SHAPE_LIMIT or (time.time() - t0) > TIME_BUDGET_S:
            return
        count += 1
        rec: dict = {"page": page_name, "depth": depth}
        try:
            rec["type"] = int(s.Type)
        except Exception:
            rec["type"] = None
        try:
            rec["name"] = str(s.Name)
        except Exception:
            rec["name"] = None
        for attr, key in (("LeftX", "x_in"), ("BottomY", "y_in"),
                          ("SizeWidth", "w_in"), ("SizeHeight", "h_in")):
            try:
                rec[key] = round(float(getattr(s, attr)), 4)
            except Exception:
                rec[key] = None
        # Text (only text shapes have .Text)
        try:
            txt = s.Text.Story.Text
            if txt:
                rec["text"] = str(txt).strip()[:400]
        except Exception:
            pass
        shapes_out.append(rec)
        # Recurse into groups / powerclips
        try:
            child = s.Shapes
            if child is not None and int(child.Count) > 0:
                walk(child, page_name, depth + 1)
        except Exception:
            pass


def main() -> int:
    try:
        app = win32com.client.GetActiveObject("CorelDRAW.Application")
        attached = True
    except Exception:
        app = win32com.client.Dispatch("CorelDRAW.Application")
        attached = False

    prev_doc = None
    try:
        prev_doc = app.ActiveDocument
    except Exception:
        prev_doc = None

    doc = None
    try:
        doc = app.OpenDocument(CDR)
        try:
            doc.Unit = 1  # cdrInch
        except Exception as e:
            errors.append(f"set Unit: {e}")
        try:
            n_pages = int(doc.Pages.Count)
        except Exception as e:
            errors.append(f"Pages.Count: {e}")
            n_pages = 0
        for pi in range(1, n_pages + 1):
            if (time.time() - t0) > TIME_BUDGET_S:
                errors.append("time budget hit; partial")
                break
            page = doc.Pages.Item(pi)
            pname = f"p{pi}"
            try:
                for li in range(1, int(page.Layers.Count) + 1):
                    layer = page.Layers.Item(li)
                    try:
                        walk(layer.Shapes, f"{pname}:{layer.Name}")
                    except Exception as e:
                        errors.append(f"layer {li}: {e}")
            except Exception as e:
                errors.append(f"page {pi}: {e}")
    finally:
        if doc is not None:
            try:
                doc.Dirty = False
            except Exception:
                pass
            try:
                doc.Close()
            except Exception as e:
                errors.append(f"close: {e}")
        if prev_doc is not None:
            try:
                prev_doc.Activate()
            except Exception:
                pass

    payload = {
        "source_cdr": CDR,
        "attached_to_running": attached,
        "shape_count": len(shapes_out),
        "elapsed_s": round(time.time() - t0, 1),
        "errors": errors,
        "shapes": shapes_out,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Console summary: text shapes that look like dimensions + biggest boxes
    print(f"shapes={len(shapes_out)} elapsed={payload['elapsed_s']}s "
          f"attached={attached} errors={len(errors)}")
    dims = [r for r in shapes_out
            if r.get("text") and any(c.isdigit() for c in r["text"])
            and any(m in r["text"] for m in ('"', "'", "-", "X", "x"))]
    print(f"--- candidate dimension/text shapes ({len(dims)}) ---")
    for r in dims[:60]:
        print(f"[{r['page']}] {r['text']!r}")
    boxed = sorted((r for r in shapes_out if r.get("w_in") and r.get("h_in")),
                   key=lambda r: (r["w_in"] or 0) * (r["h_in"] or 0), reverse=True)
    print("--- 15 largest bounding boxes (inches) ---")
    for r in boxed[:15]:
        print(f"[{r['page']}] type={r['type']} name={r['name']!r} "
              f"x={r['x_in']} y={r['y_in']} w={r['w_in']} h={r['h_in']}")
    print(f"JSON -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
