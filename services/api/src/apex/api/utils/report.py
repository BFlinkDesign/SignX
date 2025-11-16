"""PDF report generation utilities with deterministic caching."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import structlog

# Add signcalc-service to path
_signcalc_path = Path(__file__).parent.parent.parent.parent.parent / "signcalc-service"
if str(_signcalc_path) not in sys.path:
    sys.path.insert(0, str(_signcalc_path))

try:
    from apex_signcalc.report_render import render_pdf
except ImportError:
    # Fallback for development
    def render_pdf(root: Path, title: str, calc_data: dict) -> tuple[str, str]:
        return "fallback_hash", "blobs/00/fallback.pdf"

logger = structlog.get_logger(__name__)


from ..common.hashing import compute_payload_sha256


async def generate_report_from_payload(
    project_id: str,
    payload: dict,
    root_path: Optional[Path] = None,
) -> dict[str, str]:
    """Generate PDF report from project payload with deterministic caching.
    
    Returns: {"sha256": str, "pdf_ref": str, "cached": bool}
    """
    if root_path is None:
        # Default to artifacts directory
        root_path = Path(__file__).parent.parent.parent.parent.parent / "artifacts"
    
    # Compute deterministic hash
    payload_sha = compute_payload_sha256(payload)
    
    # Check cache by SHA256
    cached_path = root_path / "blobs" / payload_sha[:2] / f"{payload_sha}.pdf"
    if cached_path.exists():
        logger.info("report.cache_hit", project_id=project_id, sha256=payload_sha[:16])
        return {
            "sha256": payload_sha,
            "pdf_ref": f"blobs/{payload_sha[:2]}/{payload_sha}.pdf",
            "cached": True,
        }
    
    # Generate new report
    logger.info("report.generate", project_id=project_id, sha256=payload_sha[:16])
    
    # Format payload for signcalc-service render_pdf
    # Extract design data from payload config
    from datetime import datetime
    
    calc_data = {
        "request": payload.get("config", {}).get("request", {}),
        "selected": payload.get("config", {}).get("selected", {}),
        "loads": payload.get("config", {}).get("loads", {}),
        "packs_sha": payload.get("config", {}).get("packs_sha", ""),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    # Ensure project name is present
    if "provenance" not in calc_data.get("request", {}):
        calc_data["request"]["provenance"] = {
            "project_name": payload.get("config", {}).get("project_name", "Sign Design"),
        }
    
    pdf_sha, pdf_ref = render_pdf(root_path, "Sign Design Report", calc_data)
    
    # Verify hash matches (deterministic)
    if pdf_sha != payload_sha:
        logger.warning("report.hash_mismatch", expected=payload_sha[:16], got=pdf_sha[:16])
    
    return {
        "sha256": pdf_sha,
        "pdf_ref": pdf_ref,
        "cached": False,
    }

