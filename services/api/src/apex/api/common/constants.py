"""Constants pack loading and versioning for APEX.

Loads versioned YAML packs from services/api/packs/constants/
and computes SHA256 digests for auditability.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger(__name__)


class ConstantsPack:
    """A versioned pack of engineering constants."""
    
    def __init__(self, name: str, version: str, sha256: str, data: dict[str, Any]):
        self.name = name
        self.version = version
        self.sha256 = sha256
        self.data = data
    
    def __repr__(self) -> str:
        return f"ConstantsPack({self.name}:{self.version}:{self.sha256[:8]})"


_PACKS: dict[str, ConstantsPack] = {}


def load_constants_packs(base_dir: Path | None = None) -> dict[str, ConstantsPack]:
    """Load all constants packs from packs/constants/ directory.
    
    Args:
        base_dir: Optional base directory (defaults to services/api/)
    
    Returns:
        Dict mapping pack_name to ConstantsPack
    """
    if _PACKS:
        return _PACKS  # Already loaded
    
    if base_dir is None:
        # Resolve from this file: /app/src/apex/api/common/constants.py
        # Go up 4 levels to /app/
        base_dir = Path(__file__).resolve().parents[4]
    
    constants_dir = base_dir / "config"
    
    if not constants_dir.exists():
        logger.warning("constants_directory_missing", path=str(constants_dir))
        return {}
    
    # Find all YAML files matching pattern *_v*.yaml
    for yaml_file in constants_dir.glob("*_v*.yaml"):
        try:
            _load_pack(yaml_file)
        except Exception as e:
            logger.error("constants_pack_load_failed", file=str(yaml_file), error=str(e))
    
    logger.info("constants_packs_loaded", count=len(_PACKS))
    return _PACKS


def _load_pack(path: Path) -> ConstantsPack:
    """Load a single constants pack and compute SHA256.
    
    Args:
        path: Path to YAML file
    
    Returns:
        ConstantsPack instance
    """
    with path.open("rb") as f:
        raw_content = f.read()
    
    # Parse YAML
    data = yaml.safe_load(raw_content.decode("utf-8")) or {}
    
    # Compute SHA256 of raw file content
    sha256 = hashlib.sha256(raw_content).hexdigest()
    
    # Extract name and version from filename (e.g., pricing_v1.yaml)
    stem = path.stem
    if "_v" in stem:
        name, version_part = stem.rsplit("_v", 1)
        version = f"v{version_part}"
    else:
        name = stem
        version = "v1"
    
    pack = ConstantsPack(name=name, version=version, sha256=sha256, data=data)
    _PACKS[name] = pack
    
    logger.info("constants_pack_loaded", name=name, version=version, sha256=sha256[:8])
    return pack


def get_constants_version_string() -> str:
    """Generate version string for all loaded packs.
    
    Returns:
        Comma-separated string: "name:version:sha256,name:version:sha256..."
    """
    packs = load_constants_packs()
    if not packs:
        return ""
    
    versions = [f"{pack.name}:{pack.version}:{pack.sha256}" for pack in packs.values()]
    return ",".join(sorted(versions))


def get_pack_metadata() -> dict[str, Any]:
    """Get metadata dict for all loaded packs (for trace.pack_metadata).
    
    Returns:
        Dict with pack names as keys and metadata as values
    """
    packs = load_constants_packs()
    
    metadata = {}
    for pack in packs.values():
        metadata[pack.name] = {
            "version": pack.version,
            "sha256": pack.sha256,
            "refs": _extract_refs(pack.data),
        }
    
    return metadata


def _extract_refs(data: dict[str, Any]) -> list[str]:
    """Extract references/citations from constants pack data.
    
    Args:
        data: Parsed YAML data
    
    Returns:
        List of reference strings
    """
    refs = []
    
    # Look for common reference fields
    if isinstance(data, dict):
        for key in ["source", "citation", "reference", "references"]:
            if key in data:
                val = data[key]
                if isinstance(val, str):
                    refs.append(val)
                elif isinstance(val, list):
                    refs.extend(val)
    
    return refs


def get_constants(name: str) -> dict[str, Any] | None:
    """Get a specific constants pack by name.
    
    Args:
        name: Pack name (e.g., "pricing")
    
    Returns:
        Parsed data dict or None if not found
    """
    packs = load_constants_packs()
    if name in packs:
        return packs[name].data
    return None

