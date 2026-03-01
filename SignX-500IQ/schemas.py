"""
schemas.py — Pydantic v2 request/response models for the 500IQ API.

Follows the SignX envelope pattern:
  { schema_version, result, assumptions, confidence, trace }

Every mutating or query response is wrapped in IQEnvelope so downstream
consumers (Intelligence module, SignX-Takeoff) get a consistent shape.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "iq-1.0"


# ── Enums ─────────────────────────────────────────────────────────────────── #

class NodeType(str, Enum):
    JOB = "JOB"
    EMPLOYEE = "EMPLOYEE"
    HEURISTIC = "HEURISTIC"
    MATERIAL = "MATERIAL"
    FAILURE_MODE = "FAILURE_MODE"
    WORK_CODE = "WORK_CODE"
    CUSTOMER = "CUSTOMER"
    SIGN_TYPE = "SIGN_TYPE"
    CONSTRAINT = "CONSTRAINT"
    EQUIPMENT = "EQUIPMENT"
    SUPPLIER = "SUPPLIER"


class EdgeStatus(str, Enum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    REJECTED = "rejected"


class RelationshipType(str, Enum):
    CAUSED_BY = "CAUSED_BY"
    PREFERS = "PREFERS"
    VIOLATES = "VIOLATES"
    LEARNED_FROM = "LEARNED_FROM"
    USES = "USES"
    IMPACTS = "IMPACTS"
    WORKED_ON = "WORKED_ON"
    SIMILAR_TO = "SIMILAR_TO"
    ADJUSTS = "ADJUSTS"
    APPLIES_TO = "APPLIES_TO"
    INFLUENCED_BY = "INFLUENCED_BY"
    REQUIRES = "REQUIRES"


class TraversalDirection(str, Enum):
    OUTGOING = "outgoing"
    INCOMING = "incoming"
    BOTH = "both"


# ── Trace (audit trail) ──────────────────────────────────────────────────── #

def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except Exception:
        return "unknown"


def make_trace(result_data: Any, inputs_data: Any) -> "Trace":
    """Build a Trace from result + inputs for the envelope."""
    result_bytes = json.dumps(
        result_data, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    inputs_bytes = json.dumps(
        inputs_data, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return Trace(
        data_sha256=hashlib.sha256(result_bytes).hexdigest(),
        inputs_hash=hashlib.sha256(inputs_bytes).hexdigest(),
        code_version=_git_sha(),
    )


class Trace(BaseModel):
    data_sha256: str
    inputs_hash: str
    code_version: str = "unknown"
    timestamp_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ── Envelope ──────────────────────────────────────────────────────────────── #

class IQEnvelope(BaseModel):
    """Standardised response wrapper matching SignX service conventions."""
    schema_version: str = SCHEMA_VERSION
    result: Any
    assumptions: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    trace: Trace


# ── Node CRUD ─────────────────────────────────────────────────────────────── #

class NodeCreate(BaseModel):
    id: str = Field(..., min_length=1, description="Namespaced ID, e.g. EMPLOYEE-JEFF")
    type: NodeType
    label: str = Field(default="", description="Human-readable name")
    properties: Dict[str, Any] = Field(default_factory=dict)
    source: str = Field(default="manual")


class NodeUpdate(BaseModel):
    label: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    source: Optional[str] = None


class NodeResponse(BaseModel):
    id: str
    type: str
    label: str
    properties: Dict[str, Any]
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NodeWithEdges(NodeResponse):
    outgoing: List["EdgeResponse"] = Field(default_factory=list)
    incoming: List["EdgeResponse"] = Field(default_factory=list)


# ── Edge CRUD ─────────────────────────────────────────────────────────────── #

class EdgeCreate(BaseModel):
    source_id: str = Field(..., min_length=1)
    target_id: str = Field(..., min_length=1)
    relationship_type: RelationshipType
    weight: float = Field(default=1.0, ge=0.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    status: EdgeStatus = Field(default=EdgeStatus.VALIDATED)
    evidence: Dict[str, Any] = Field(default_factory=dict)


class EdgeResponse(BaseModel):
    id: int
    source_id: str
    target_id: str
    relationship_type: str
    weight: float
    confidence: float
    status: str
    evidence: Dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Traversal ─────────────────────────────────────────────────────────────── #

class TraversalRequest(BaseModel):
    start_node_id: str
    relationship_types: Optional[List[RelationshipType]] = None
    max_depth: int = Field(default=3, ge=1, le=10)
    direction: TraversalDirection = TraversalDirection.OUTGOING


class TraversalResult(BaseModel):
    nodes: List[NodeResponse]
    edges: List[EdgeResponse]
    depth_reached: int


# ── Path finding ──────────────────────────────────────────────────────────── #

class PathRequest(BaseModel):
    source_id: str
    target_id: str
    max_depth: int = Field(default=5, ge=1, le=10)


class PathStep(BaseModel):
    node: NodeResponse
    edge: Optional[EdgeResponse] = None


class PathResult(BaseModel):
    paths: List[List[PathStep]]
    shortest_length: int


# ── Heuristic query (the killer feature) ──────────────────────────────────── #

class HeuristicQuery(BaseModel):
    """Ask the graph: what adjustments apply to this work scenario?"""
    employee_id: Optional[str] = None
    work_code: Optional[str] = None
    sign_type: Optional[str] = None


class HeuristicAdjustment(BaseModel):
    heuristic_id: str
    label: str
    adjustment_factor: float = Field(
        description="Multiplier (1.15 = +15%, 0.90 = -10%)"
    )
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_chain: List[str] = Field(
        description="Node IDs showing the reasoning path"
    )
    notes: str = ""


class HeuristicResult(BaseModel):
    adjustments: List[HeuristicAdjustment]
    combined_factor: float = Field(
        description="Product of all adjustment factors"
    )
    query: HeuristicQuery


# ── Graph stats ───────────────────────────────────────────────────────────── #

class TypeCount(BaseModel):
    type: str
    count: int


class GraphStats(BaseModel):
    total_nodes: int
    total_edges: int
    nodes_by_type: List[TypeCount]
    edges_by_type: List[TypeCount]


# ── Node list / search ────────────────────────────────────────────────────── #

class NodeListResponse(BaseModel):
    items: List[NodeResponse]
    total: int


# ── Batch ingest ──────────────────────────────────────────────────────────── #

def _normalize_id(raw: str) -> str:
    """Trim, uppercase, spaces→hyphens, collapse repeated hyphens."""
    import re
    s = raw.strip().upper().replace(" ", "-")
    return re.sub(r"-{2,}", "-", s)


class BatchNodeInput(BaseModel):
    id: str = Field(..., min_length=1)
    type: NodeType
    label: str = Field(default="")
    properties: Dict[str, Any] = Field(default_factory=dict)
    source: str = Field(default="knowex")


class BatchEdgeInput(BaseModel):
    source_id: str = Field(..., min_length=1)
    target_id: str = Field(..., min_length=1)
    relationship_type: RelationshipType
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    status: EdgeStatus = Field(default=EdgeStatus.PROPOSED)
    evidence: Dict[str, Any] = Field(default_factory=dict)


class BatchIngestRequest(BaseModel):
    nodes: List[BatchNodeInput] = Field(default_factory=list)
    edges: List[BatchEdgeInput] = Field(default_factory=list)
    source: str = Field(default="knowex", description="Origin pipeline")


class BatchIngestResult(BaseModel):
    nodes_created: int = 0
    nodes_updated: int = 0
    edges_created: int = 0
    edges_updated: int = 0
    edges_skipped: int = 0
    errors: List[str] = Field(default_factory=list)
