from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Tuple

import ezdxf
from weasyprint import HTML


def _store_blob(root: Path, data: bytes, ext: str) -> Tuple[str, Path]:
    h = hashlib.sha256(data).hexdigest()
    sub = h[:2]
    p = root / "artifacts" / "blobs" / sub
    p.mkdir(parents=True, exist_ok=True)
    dst = p / f"{h}.{ext}"
    if not dst.exists():
        dst.write_bytes(data)
    return h, dst


def render_calc_json(root: Path, payload: Dict) -> Tuple[str, str]:
    data = (str(payload)).encode("utf-8")
    h, path = _store_blob(root, data, "json")
    return h, f"blobs/{h[:2]}/{h}.json"


def render_pdf(root: Path, title: str, calc_data: Dict) -> Tuple[str, str]:
    # Format 4-page sign calc report
    from datetime import datetime
    
    project_name = calc_data.get("request", {}).get("provenance", {}).get("project_name", "Sign Design")
    site_addr = calc_data.get("request", {}).get("site", {})
    selected = calc_data.get("selected", {})
    loads = calc_data.get("loads", {})
    
    # Timestamp for report
    generated_at = calc_data.get("generated_at", datetime.now().strftime("%Y-%m-%d"))
    
    # Concrete yards calculation
    fdn = selected.get("foundation", {})
    dia_ft = (fdn.get("dia_in", 0) or 0) / 12.0
    depth_ft = (fdn.get("depth_in", 0) or 0) / 12.0
    concrete_yds = 0.0
    if dia_ft > 0 and depth_ft > 0:
        import math
        concrete_yds = round((math.pi * (dia_ft/2)**2 * depth_ft) / 27.0, 2)
    
    # Extract additional data for enhanced 4-page layout
    support_type = selected.get('support', {}).get('type', 'N/A')
    support_designation = selected.get('support', {}).get('designation', 'N/A')
    checks = selected.get('checks', {})
    max_torque = loads.get('F_w_sign_lbf', 0.0) * (selected.get('support', {}).get('height_ft', 0.0) * 12.0) / 12.0  # kip-ft approximation
    site_address = site_addr.get('street') or site_addr.get('address') or f"{site_addr.get('lat', 'N/A')}, {site_addr.get('lon', 'N/A')}"
    
    html = f"""
    <!DOCTYPE html>
    <html><head><meta charset='utf-8'><title>{project_name}</title><style>
      @page {{ size: letter; margin: 0.5in; }}
      body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
      .cover {{ text-align: center; padding: 2in 0; }}
      h1 {{ font-size: 28pt; color: #0066cc; margin-bottom: 0.5in; }}
      h2 {{ font-size: 20pt; page-break-before: always; color: #333; margin-top: 0.5in; }}
      .page-break {{ page-break-after: always; }}
      .info-box {{ background-color: #f5f5f5; border: 1px solid #ddd; padding: 15px; margin: 15px 0; border-radius: 5px; }}
      .info-box strong {{ color: #0066cc; }}
      table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
      td, th {{ border: 1px solid #ccc; padding: 10px; text-align: left; }}
      th {{ background-color: #0066cc; color: white; font-weight: bold; }}
      tr:nth-child(even) {{ background-color: #f9f9f9; }}
      .notes {{ margin-top: 20px; font-size: 10pt; line-height: 1.8; }}
      .notes ul {{ margin-left: 20px; }}
      .footer {{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #ccc; font-size: 9pt; color: #666; }}
    </style></head>
    <body>
      <!-- Page 1: Cover -->
      <div class="cover page-break">
        <h1>{project_name}</h1>
        <div class="info-box" style="margin: 30px auto; max-width: 500px;">
          <p><strong>Site Address:</strong><br>{site_address}</p>
          <p><strong>Coordinates:</strong> {site_addr.get('lat', 'N/A')}, {site_addr.get('lon', 'N/A')}</p>
          <p><strong>Date:</strong> {generated_at}</p>
        </div>
        <div class="footer">
          <p>Sign Design Calculation Report</p>
          <p>Prepared in accordance with ASCE 7-16 and applicable building codes</p>
        </div>
      </div>
      
      <!-- Page 2: Elevation -->
      <h2>Elevation Drawing</h2>
      <div class="info-box">
        <p><strong>Support Structure:</strong> {support_type} {support_designation}</p>
        <p><strong>Foundation:</strong> {fdn.get('dia_in', 'N/A')}" diameter × {fdn.get('depth_in', 'N/A')}" deep</p>
        <p><strong>Foundation Shape:</strong> {fdn.get('shape', 'cylindrical').upper()}</p>
        {f"<p><strong>Rebar Schedule:</strong> {fdn.get('rebar_schedule_ref', 'N/A')}</p>" if fdn.get('rebar_schedule_ref') else ""}
        {f"<p><strong>Anchor Pattern:</strong> {fdn.get('anchor_bolt_ref', 'N/A')}</p>" if fdn.get('anchor_bolt_ref') else ""}
      </div>
      <div class="footer">
        <p>Note: Elevation drawing shown schematically. Verify dimensions in field.</p>
      </div>
      
      <!-- Page 3: Design Output -->
      <h2>Design Output</h2>
      <table>
        <tr><th colspan="2">Wind Loads</th></tr>
        <tr><td>Basic Wind Speed (V)</td><td>{loads.get('V_basic', 'N/A')} mph</td></tr>
        <tr><td>Wind Force on Sign</td><td>{loads.get('F_w_sign_lbf', 'N/A'):.1f} lbf</td></tr>
        <tr><td>Design Pressure (qz)</td><td>{loads.get('qz_psf', 'N/A'):.1f} psf</td></tr>
      </table>
      <table>
        <tr><th colspan="2">Foundation Design</th></tr>
        <tr><td>Concrete Required</td><td>{concrete_yds} cu. yd</td></tr>
        <tr><td>Foundation Diameter</td><td>{fdn.get('dia_in', 'N/A')} in</td></tr>
        <tr><td>Foundation Depth</td><td>{fdn.get('depth_in', 'N/A')} in</td></tr>
      </table>
      <table>
        <tr><th colspan="2">Safety Factors</th></tr>
        <tr><td>Overturning (OT)</td><td>{checks.get('OT_sf', 'N/A'):.2f}</td></tr>
        <tr><td>Bearing (BRG)</td><td>{checks.get('BRG_sf', 'N/A'):.2f}</td></tr>
        <tr><td>Sliding (SLIDE)</td><td>{checks.get('SLIDE_sf', 'N/A'):.2f}</td></tr>
        <tr><td>Uplift (UPLIFT)</td><td>{checks.get('UPLIFT_sf', 'N/A'):.2f}</td></tr>
        <tr><td>Deflection OK</td><td>{'Yes' if checks.get('DEF_ok', False) else 'No'}</td></tr>
      </table>
      {f"<p><strong>Maximum Applied Moment:</strong> {max_torque:.1f} kip-ft</p>" if max_torque > 0 else ""}
      
      <!-- Page 4: General Notes -->
      <h2>General Notes</h2>
      <div class="notes">
        <p><strong>Design Basis:</strong></p>
        <ul>
          <li>Wind loads per ASCE 7-16, Method 2 (Analytical Procedure)</li>
          <li>Foundation design per ACI 318 and industry standard practice</li>
          <li>Steel design per AISC 360 (if applicable)</li>
        </ul>
        <p><strong>Field Verification Required:</strong></p>
        <ul>
          <li>Verify site conditions match design assumptions (soil bearing, exposure)</li>
          <li>Confirm foundation depth and diameter per approved drawings</li>
          <li>Verify anchor bolt placement and embedment (if baseplate foundation)</li>
          <li>Check support member installation and alignment</li>
        </ul>
        <p><strong>Disclaimers:</strong></p>
        <ul>
          <li>This calculation is for design estimation purposes</li>
          <li>Final design review by licensed professional engineer may be required</li>
          <li>Verify all applicable local building codes and regulations</li>
          <li>No warranty expressed or implied</li>
        </ul>
      </div>
      <div class="footer">
        <p>Report Generated: {generated_at}</p>
        <p>Standards Pack SHA256: {calc_data.get('packs_sha', 'N/A')[:16]}...</p>
      </div>
    </body></html>
    """.strip()
    pdf_bytes = HTML(string=html).write_pdf()
    h, path = _store_blob(root, pdf_bytes, "pdf")
    return h, f"blobs/{h[:2]}/{h}.pdf"


def render_dxf(root: Path, title: str) -> Tuple[str, str]:
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_text(title, dxfattribs={"height": 0.35}).set_pos((0, 0))
    data = doc.write_bytes()
    h, path = _store_blob(root, data, "dxf")
    return h, f"blobs/{h[:2]}/{h}.dxf"


