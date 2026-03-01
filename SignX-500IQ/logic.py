"""
logic.py — Graph traversal and tribal-knowledge query functions.

This is the "brain" of 500IQ.  Given the adjacency-list stored in SQLite,
these functions walk the graph to answer business questions:

  * traverse()                — BFS from a start node
  * find_paths()              — all paths between two nodes
  * get_heuristic_adjustments — THE key function: "what tribal adjustments
                                 apply when Employee X works on WorkCode Y
                                 for SignType Z?"
  * get_related_failures()    — failure modes connected to a node
  * get_node_neighborhood()   — local subgraph for UI visualisation
  * compute_graph_stats()     — counts by type for health dashboard
"""
from __future__ import annotations

import re
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Edge, Node


# ── BFS Traversal ─────────────────────────────────────────────────────────── #

async def traverse(
    session: AsyncSession,
    start_id: str,
    relationship_types: Optional[List[str]] = None,
    max_depth: int = 3,
    direction: str = "outgoing",
) -> Tuple[List[Node], List[Edge], int]:
    """
    Breadth-first traversal from *start_id*.

    Returns (visited_nodes, traversed_edges, max_depth_reached).
    """
    visited_nodes: Dict[str, Node] = {}
    traversed_edges: List[Edge] = []
    queue: deque[Tuple[str, int]] = deque()

    # Load start node
    start = await session.get(Node, start_id)
    if start is None:
        return [], [], 0

    visited_nodes[start.id] = start
    queue.append((start.id, 0))
    depth_reached = 0

    while queue:
        current_id, depth = queue.popleft()
        if depth >= max_depth:
            continue

        edges = await _get_edges(session, current_id, relationship_types, direction)

        for edge in edges:
            traversed_edges.append(edge)
            neighbour_id = (
                edge.target_id if edge.source_id == current_id else edge.source_id
            )

            if neighbour_id not in visited_nodes:
                neighbour = await session.get(Node, neighbour_id)
                if neighbour is not None:
                    visited_nodes[neighbour_id] = neighbour
                    next_depth = depth + 1
                    depth_reached = max(depth_reached, next_depth)
                    queue.append((neighbour_id, next_depth))

    return list(visited_nodes.values()), traversed_edges, depth_reached


async def _get_edges(
    session: AsyncSession,
    node_id: str,
    relationship_types: Optional[List[str]],
    direction: str,
) -> List[Edge]:
    """Fetch edges for a node in the given direction."""
    clauses = []

    if direction in ("outgoing", "both"):
        stmt = select(Edge).where(Edge.source_id == node_id)
        if relationship_types:
            stmt = stmt.where(Edge.relationship_type.in_(relationship_types))
        result = await session.execute(stmt)
        clauses.extend(result.scalars().all())

    if direction in ("incoming", "both"):
        stmt = select(Edge).where(Edge.target_id == node_id)
        if relationship_types:
            stmt = stmt.where(Edge.relationship_type.in_(relationship_types))
        result = await session.execute(stmt)
        clauses.extend(result.scalars().all())

    return clauses


# ── Path Finding ──────────────────────────────────────────────────────────── #

async def find_paths(
    session: AsyncSession,
    source_id: str,
    target_id: str,
    max_depth: int = 5,
) -> List[List[Tuple[Node, Optional[Edge]]]]:
    """
    Find all paths from *source_id* to *target_id* up to *max_depth*.

    Returns a list of paths, where each path is a list of (node, edge_used)
    tuples.  The first step's edge is None (it's the start node).
    """
    source = await session.get(Node, source_id)
    target = await session.get(Node, target_id)
    if source is None or target is None:
        return []

    all_paths: List[List[Tuple[Node, Optional[Edge]]]] = []
    # DFS with path tracking
    stack: List[Tuple[str, List[Tuple[Node, Optional[Edge]]], Set[str]]] = [
        (source_id, [(source, None)], {source_id})
    ]

    while stack:
        current_id, path, visited = stack.pop()

        if current_id == target_id and len(path) > 1:
            all_paths.append(list(path))
            continue

        if len(path) - 1 >= max_depth:
            continue

        edges = await _get_edges(session, current_id, None, "outgoing")
        for edge in edges:
            next_id = edge.target_id
            if next_id not in visited:
                next_node = await session.get(Node, next_id)
                if next_node is not None:
                    new_visited = visited | {next_id}
                    stack.append((
                        next_id,
                        path + [(next_node, edge)],
                        new_visited,
                    ))

    # Sort by length (shortest first)
    all_paths.sort(key=len)
    return all_paths


# ── Heuristic Adjustments (THE killer query) ──────────────────────────────── #

async def get_heuristic_adjustments(
    session: AsyncSession,
    employee_id: Optional[str] = None,
    work_code: Optional[str] = None,
    sign_type: Optional[str] = None,
    include_proposed: bool = False,
) -> Tuple[List[dict], float]:
    """
    Walk the graph to find tribal-knowledge adjustments.

    The canonical path:
      EMPLOYEE --USES--> HEURISTIC --IMPACTS--> WORK_CODE
      SIGN_TYPE --REQUIRES--> HEURISTIC

    SAFETY: Only uses edges with status="validated" by default.
    Set include_proposed=True for debugging to also include proposed edges.

    Returns (adjustments_list, combined_factor) where combined_factor is
    the product of all individual adjustment_factor values.
    """
    allowed_statuses = ["validated"]
    if include_proposed:
        allowed_statuses.append("proposed")

    heuristic_ids: Set[str] = set()
    adjustments: List[dict] = []

    # 1) Employee heuristics: EMPLOYEE --USES--> HEURISTIC
    if employee_id:
        stmt = (
            select(Edge)
            .where(Edge.source_id == employee_id)
            .where(Edge.relationship_type.in_(["USES", "PREFERS"]))
            .where(Edge.status.in_(allowed_statuses))
        )
        result = await session.execute(stmt)
        for edge in result.scalars().all():
            heuristic_ids.add(edge.target_id)

    # 2) Sign-type heuristics: SIGN_TYPE --REQUIRES/ADJUSTS--> HEURISTIC
    if sign_type:
        stmt = (
            select(Edge)
            .where(Edge.source_id == sign_type)
            .where(Edge.relationship_type.in_(["REQUIRES", "ADJUSTS", "APPLIES_TO"]))
            .where(Edge.status.in_(allowed_statuses))
        )
        result = await session.execute(stmt)
        for edge in result.scalars().all():
            heuristic_ids.add(edge.target_id)

    # 3) Filter heuristics that IMPACT the requested work code
    filtered_ids = set()
    if work_code and heuristic_ids:
        for hid in heuristic_ids:
            stmt = (
                select(Edge)
                .where(Edge.source_id == hid)
                .where(Edge.target_id == work_code)
                .where(Edge.relationship_type.in_(["IMPACTS", "APPLIES_TO", "ADJUSTS"]))
                .where(Edge.status.in_(allowed_statuses))
            )
            result = await session.execute(stmt)
            if result.scalars().first() is not None:
                filtered_ids.add(hid)
    else:
        # No work_code filter — return all found heuristics
        filtered_ids = heuristic_ids

    # 4) Build adjustment records
    combined = 1.0
    for hid in filtered_ids:
        node = await session.get(Node, hid)
        if node is None or node.type != "HEURISTIC":
            continue

        props = node.properties or {}
        factor = float(props.get("adjustment_factor", 1.0))
        conf = float(props.get("confidence", 0.5))
        notes = str(props.get("note", props.get("notes", "")))

        # Build evidence chain: which nodes led to this heuristic
        chain = []
        if employee_id:
            chain.append(employee_id)
        chain.append(hid)
        if work_code:
            chain.append(work_code)

        adjustments.append({
            "heuristic_id": hid,
            "label": node.label,
            "adjustment_factor": factor,
            "confidence": conf,
            "evidence_chain": chain,
            "notes": notes,
        })

        combined *= factor

    return adjustments, round(combined, 6)


# ── Failure Mode Lookup ───────────────────────────────────────────────────── #

async def get_related_failures(
    session: AsyncSession,
    node_id: str,
) -> List[Node]:
    """Find FAILURE_MODE nodes reachable from *node_id* via CAUSED_BY / LEARNED_FROM."""
    nodes, edges, _ = await traverse(
        session,
        node_id,
        relationship_types=["CAUSED_BY", "LEARNED_FROM"],
        max_depth=3,
        direction="both",
    )
    return [n for n in nodes if n.type == "FAILURE_MODE"]


# ── Neighbourhood (for UI) ────────────────────────────────────────────────── #

async def get_node_neighborhood(
    session: AsyncSession,
    node_id: str,
    depth: int = 1,
) -> Tuple[List[Node], List[Edge]]:
    """Return the local subgraph around *node_id*."""
    nodes, edges, _ = await traverse(
        session, node_id, max_depth=depth, direction="both"
    )
    return nodes, edges


# ── Stats ─────────────────────────────────────────────────────────────────── #

async def compute_graph_stats(session: AsyncSession) -> dict:
    """Count nodes and edges by type."""
    # Nodes by type
    stmt = select(Node.type, func.count(Node.id)).group_by(Node.type)
    result = await session.execute(stmt)
    nodes_by_type = [{"type": t, "count": c} for t, c in result.all()]

    # Edges by relationship type
    stmt = select(Edge.relationship_type, func.count(Edge.id)).group_by(
        Edge.relationship_type
    )
    result = await session.execute(stmt)
    edges_by_type = [{"type": t, "count": c} for t, c in result.all()]

    total_nodes = sum(x["count"] for x in nodes_by_type)
    total_edges = sum(x["count"] for x in edges_by_type)

    return {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "nodes_by_type": nodes_by_type,
        "edges_by_type": edges_by_type,
    }


# ── Batch Ingest (upsert) ────────────────────────────────────────────────── #

def _normalize_id(raw: str) -> str:
    """Trim, uppercase, spaces→hyphens, collapse repeated hyphens."""
    s = raw.strip().upper().replace(" ", "-")
    return re.sub(r"-{2,}", "-", s)


def _deep_merge(base: dict, incoming: dict) -> dict:
    """Merge incoming into base. Incoming keys overwrite base keys."""
    merged = dict(base)
    for k, v in incoming.items():
        if (
            k in merged
            and isinstance(merged[k], dict)
            and isinstance(v, dict)
        ):
            merged[k] = _deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


async def batch_ingest(
    session: AsyncSession,
    nodes: list,
    edges: list,
    source: str = "knowex",
    mode: str = "strict",
) -> dict:
    """
    Upsert nodes and edges in a single transaction.

    Nodes: create if new, merge properties if exists (type must match).
    Edges: create if new (by unique triple), update confidence (take max)
           and merge evidence if exists.

    mode="strict": any error rolls back the entire batch, raises.
    mode="best_effort": skip errors, commit what succeeds.

    Returns {"nodes_created", "nodes_updated", "edges_created",
             "edges_updated", "edges_skipped", "errors"}.
    """
    stats = {
        "nodes_created": 0,
        "nodes_updated": 0,
        "edges_created": 0,
        "edges_updated": 0,
        "edges_skipped": 0,
        "errors": [],
    }

    # ── Phase 1: Upsert nodes ────────────────────────────────────────────
    for n in nodes:
        nid = _normalize_id(n.id)
        ntype = n.type.value if hasattr(n.type, "value") else str(n.type).upper()
        try:
            existing = await session.get(Node, nid)
            if existing is None:
                node = Node(
                    id=nid,
                    type=ntype,
                    label=n.label or nid,
                    properties=n.properties or {},
                    source=source,
                )
                session.add(node)
                stats["nodes_created"] += 1
            else:
                if existing.type != ntype:
                    msg = (
                        f"Node {nid}: type mismatch "
                        f"(existing={existing.type}, incoming={ntype})"
                    )
                    if mode == "strict":
                        raise ValueError(msg)
                    stats["errors"].append(msg)
                    continue
                # Merge properties
                existing.properties = _deep_merge(
                    existing.properties or {}, n.properties or {}
                )
                if n.label:
                    existing.label = n.label
                existing.updated_at = datetime.now(timezone.utc)
                stats["nodes_updated"] += 1
        except ValueError:
            raise
        except Exception as exc:
            msg = f"Node {nid}: {exc}"
            if mode == "strict":
                raise ValueError(msg) from exc
            stats["errors"].append(msg)

    # Flush nodes so edges can reference them
    await session.flush()

    # ── Phase 2: Upsert edges ────────────────────────────────────────────
    for e in edges:
        src = _normalize_id(e.source_id)
        tgt = _normalize_id(e.target_id)
        rel = (
            e.relationship_type.value
            if hasattr(e.relationship_type, "value")
            else str(e.relationship_type).upper()
        )
        edge_status = (
            e.status.value
            if hasattr(e.status, "value")
            else str(getattr(e, "status", "proposed"))
        )
        try:
            # Validate endpoints exist
            if await session.get(Node, src) is None:
                msg = f"Edge {src}->{tgt}: source node not found"
                if mode == "strict":
                    raise ValueError(msg)
                stats["errors"].append(msg)
                stats["edges_skipped"] += 1
                continue
            if await session.get(Node, tgt) is None:
                msg = f"Edge {src}->{tgt}: target node not found"
                if mode == "strict":
                    raise ValueError(msg)
                stats["errors"].append(msg)
                stats["edges_skipped"] += 1
                continue

            # Check for existing edge by unique triple
            stmt = select(Edge).where(
                and_(
                    Edge.source_id == src,
                    Edge.target_id == tgt,
                    Edge.relationship_type == rel,
                )
            )
            result = await session.execute(stmt)
            existing_edge = result.scalars().first()

            if existing_edge is None:
                edge = Edge(
                    source_id=src,
                    target_id=tgt,
                    relationship_type=rel,
                    confidence=e.confidence,
                    status=edge_status,
                    evidence=e.evidence or {},
                )
                session.add(edge)
                stats["edges_created"] += 1
            else:
                # Update: take higher confidence, merge evidence
                existing_edge.confidence = max(
                    existing_edge.confidence, e.confidence
                )
                if e.evidence:
                    existing_edge.evidence = _deep_merge(
                        existing_edge.evidence or {}, e.evidence
                    )
                # Never auto-promote proposed → validated
                # Only allow explicit status change in strict mode
                if edge_status != existing_edge.status:
                    if mode == "strict" and edge_status in (
                        "validated", "rejected"
                    ):
                        existing_edge.status = edge_status
                    # In best_effort: skip status change silently
                stats["edges_updated"] += 1
        except ValueError:
            raise
        except Exception as exc:
            msg = f"Edge {src}->{tgt}: {exc}"
            if mode == "strict":
                raise ValueError(msg) from exc
            stats["errors"].append(msg)
            stats["edges_skipped"] += 1

    return stats
