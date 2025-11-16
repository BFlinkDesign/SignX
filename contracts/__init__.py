"""
Contracts package defining request/response models for all agents.

Uses Pydantic v2 for strict validation. Each module exposes Request/Response
pairs and a `schemas()` helper that returns a mapping of name->JSON Schema.
"""

from . import materials as materials  # re-export for discoverability
from . import stackup as stackup
from . import dfma as dfma
from . import cad as cad
from . import parts as parts
from . import compliance as compliance
from . import eval as eval  # noqa: A001 - deliberate name
from . import signs as signs

__all__ = [
    "materials",
    "stackup",
    "dfma",
    "cad",
    "parts",
    "compliance",
    "eval",
    "signs",
]


