from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any
from packages.schemas import ResponseEnvelope, TraceDataModel, TraceModel, CodeVersionModel, ModelConfigModel

logger = logging.getLogger(__name__)


def sha256_digest(data: bytes | str) -> str:
    """Compute SHA256 digest of bytes or string.
    
    Unified hash function for consistent digest computation across services.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path | str) -> str:
    """Compute SHA256 digest of a file.
    
    Args:
        path: Path to file
        
    Returns:
        SHA256 hex digest, empty string on error
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    try:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logger.warning("Failed to compute SHA256 for file %s: %s", path, str(e))
        return ""


def round_safe(value: float | None, places: int = 2) -> float | None:
    """Safely round a float value, returning None if input is None."""
    if value is None:
        return None
    return round(float(value), places)


def load_json(path: Path | str) -> dict[str, Any]:
    """Load JSON file with consistent error handling.
    
    Args:
        path: Path to JSON file
        
    Returns:
        Parsed JSON as dict, empty dict on error
    """
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8")) or {}
    except Exception as e:
        logger.warning("Failed to load JSON from %s: %s", path, str(e))
        return {}


def load_yaml(path: Path | str) -> dict[str, Any]:
    """Load YAML file with consistent error handling.
    
    Args:
        path: Path to YAML file
        
    Returns:
        Parsed YAML as dict, empty dict on error
    """
    try:
        import yaml
    except ImportError:
        return {}
    
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as e:
        logger.warning("Failed to load YAML from %s: %s", path, str(e))
        return {}


def build_envelope(
    *,
    result: Any,
    assumptions: list[str] | None = None,
    confidence: float = 1.0,
    inputs: dict[str, Any] | None = None,
    intermediates: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    code_version: CodeVersionModel | None = None,
    model_config: ModelConfigModel | None = None,
) -> ResponseEnvelope:
    """Build ResponseEnvelope for services that don't have API dependencies.
    
    This is a standalone envelope builder for microservices that don't
    import from apex.api internals.
    """
    return ResponseEnvelope(
        result=result,
        assumptions=assumptions or [],
        confidence=confidence,
        trace=TraceModel(
            data=TraceDataModel(
                inputs=inputs or {},
                intermediates=intermediates or {},
                outputs=outputs or {},
            ),
            code_version=code_version or CodeVersionModel(),
            model_config=model_config or ModelConfigModel(),
        ),
    )

