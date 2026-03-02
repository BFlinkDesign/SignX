from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Tuple
import ezdxf

try:
    from weasyprint import HTML as _WeasyHTML
    HAS_WEASYPRINT = True
except (ImportError, OSError):
    HAS_WEASYPRINT = False

def _store_blob(root: Path, data: bytes, ext: str) -> Tuple[str, str]:
    h = hashlib.sha256(data).hexdigest()
    path = f"blobs/{h[:2]}/{h}.{ext}"
    full_path = root / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(data)
    return h, path

def render_calc_json(root: Path, data: Any) -> Tuple[str, str]:
    payload = json.dumps(data, indent=2, default=str)
    h, path = _store_blob(root, payload.encode("utf-8"), "json")
    return h, path

def render_pdf(root: Path, title: str, data: Dict[str, Any]) -> Tuple[str, str]:
    loads = data.get("loads", {})
    sign = data.get("sign", {})
    selected = data.get("selected", {})
    
    html = f"""
    <html>
    <head>
      <style>
        body {{ font-family: sans-serif; padding: 1in; }}
        h1 {{ color: #004a99; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 0.5in; }}
        td {{ padding: 10px; border-bottom: 1px solid #eee; }}
        .header {{ border-bottom: 3px solid #004a99; padding-bottom: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }}
        .logo {{ font-size: 24pt; font-weight: bold; color: #004a99; letter-spacing: 2px; }}
      </style>
    </head>
    <body>
      <div class="header"><div class="logo">EAGLE SIGN CO.</div><div style="font-size: 10pt; color: #666;">ENGINEERING CALCULATION REPORT</div></div>
      <h1>{title}</h1>
      <p>Date: 2026-03-02</p>
      <table>
        <tr><td>Sign Area</td><td>{sign.get('area_sf', 'N/A')} sqft</td></tr>
        <tr><td>Centroid Height</td><td>{sign.get('centroid_height_ft', 'N/A')} ft</td></tr>
        <tr><td>Design Pressure (qz)</td><td>{loads.get('qz_psf', 'N/A')} psf</td></tr>
        <tr><td>Governing Force</td><td>{loads.get('governing_F_lbf', 'N/A')} lbf</td></tr>
        <tr><td>Selected Pole</td><td>{selected.get('support', {}).get('designation', 'N/A')}</td></tr>
      </table>
      <div style="margin-top: 1in; border: 1px dashed #ccc; padding: 20px; text-align: center; color: #ccc;">
        PRELIMINARY ESTIMATE - NOT FOR PERMIT
      </div>
    </body>
    </html>
    """
    
    if not HAS_WEASYPRINT:
        h = hashlib.sha256(html.encode("utf-8")).hexdigest()
        path = f"blobs/{h[:2]}/{h}.html"
        full_path = root / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(html, encoding="utf-8")
        return h, path

    pdf_data = _WeasyHTML(string=html).write_pdf()
    h, path = _store_blob(root, pdf_data, "pdf")
    return h, path

def render_dxf(root: Path, title: str) -> Tuple[str, str]:
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_text(title, dxfattribs={"height": 0.35, "insert": (0, 0)})

    import io
    stream = io.StringIO()
    doc.write(stream)
    data = stream.getvalue().encode("utf-8")

    h, path = _store_blob(root, data, "dxf")
    return h, f"blobs/{h[:2]}/{h}.dxf"
