"""
main.py — FastAPI entry point for the 500IQ Knowledge Graph service.

Run:
    cd SignX-500IQ
    uvicorn main:app --port 8500 --reload

Routes:
    GET  /healthz              Health check
    GET  /schema               JSON schema for Node/Edge
    GET  /stats                Graph statistics

    POST /nodes                Create a node
    GET  /nodes                List / search nodes
    GET  /nodes/{node_id}      Get node + edges
    PATCH /nodes/{node_id}     Update node
    DELETE /nodes/{node_id}    Delete node (cascades edges)

    POST /nodes/batch          Bulk ingest (upsert) from KnowEx/pipelines
    POST /edges                Create an edge
    DELETE /edges/{edge_id}    Delete an edge

    GET  /review/edges         List edges by status (proposed/validated/rejected)
    POST /review/edges/{id}/validate   Approve a proposed edge
    POST /review/edges/{id}/reject     Reject a proposed edge

    POST /traverse             BFS traversal
    POST /paths                Find paths between two nodes
    POST /heuristic            Tribal-knowledge adjustments (validated only)
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db_session, init_db
from logic import (
    batch_ingest,
    compute_graph_stats,
    find_paths,
    get_heuristic_adjustments,
    traverse,
)
from models import Edge, Node
from schemas import (
    BatchIngestRequest,
    BatchIngestResult,
    EdgeCreate,
    EdgeResponse,
    HeuristicAdjustment,
    HeuristicQuery,
    HeuristicResult,
    IQEnvelope,
    NodeCreate,
    NodeListResponse,
    NodeResponse,
    NodeUpdate,
    NodeWithEdges,
    PathRequest,
    PathResult,
    PathStep,
    TraversalRequest,
    TraversalResult,
    make_trace,
)


# ── Lifespan ──────────────────────────────────────────────────────────────── #

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="SignX 500IQ — Knowledge Graph",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Health / Meta ─────────────────────────────────────────────────────────── #

@app.get("/healthz")
async def healthz(session: AsyncSession = Depends(get_db_session)):
    """Health check — verifies DB is reachable."""
    try:
        await session.execute(select(1))
        return {"status": "ok"}
    except Exception:
        return {"status": "degraded"}


@app.get("/schema")
def schema():
    """Return JSON schemas for Node and Edge create models."""
    return {
        "node": NodeCreate.model_json_schema(),
        "edge": EdgeCreate.model_json_schema(),
    }


@app.get("/stats")
async def stats(session: AsyncSession = Depends(get_db_session)):
    """Graph statistics — node/edge counts by type."""
    data = await compute_graph_stats(session)
    return IQEnvelope(
        result=data,
        assumptions=["Counts are real-time from SQLite"],
        confidence=1.0,
        trace=make_trace(data, {"query": "stats"}),
    )


# ── Node CRUD ─────────────────────────────────────────────────────────────── #

@app.post("/nodes", status_code=201)
async def create_node(
    body: NodeCreate,
    session: AsyncSession = Depends(get_db_session),
):
    existing = await session.get(Node, body.id)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Node {body.id!r} already exists")

    node = Node(
        id=body.id,
        type=body.type.value,
        label=body.label,
        properties=body.properties,
        source=body.source,
    )
    session.add(node)
    await session.flush()

    result = NodeResponse.model_validate(node).model_dump(mode="json")
    return IQEnvelope(
        result=result,
        assumptions=[],
        confidence=1.0,
        trace=make_trace(result, body.model_dump(mode="json")),
    )


@app.get("/nodes")
async def list_nodes(
    type: Optional[str] = Query(None, description="Filter by node type"),
    q: Optional[str] = Query(None, description="Search label (case-insensitive)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
):
    stmt = select(Node)
    if type:
        stmt = stmt.where(Node.type == type.upper())
    if q:
        stmt = stmt.where(Node.label.ilike(f"%{q}%"))
    stmt = stmt.order_by(Node.created_at.desc()).offset(offset).limit(limit)

    result = await session.execute(stmt)
    nodes = result.scalars().all()

    # Get total count
    count_stmt = select(Node.id)
    if type:
        count_stmt = count_stmt.where(Node.type == type.upper())
    if q:
        count_stmt = count_stmt.where(Node.label.ilike(f"%{q}%"))
    count_result = await session.execute(count_stmt)
    total = len(count_result.all())

    return NodeListResponse(
        items=[NodeResponse.model_validate(n) for n in nodes],
        total=total,
    )


@app.get("/nodes/{node_id}")
async def get_node(
    node_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    node = await session.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node {node_id!r} not found")

    # Load edges
    out_stmt = select(Edge).where(Edge.source_id == node_id)
    in_stmt = select(Edge).where(Edge.target_id == node_id)
    out_result = await session.execute(out_stmt)
    in_result = await session.execute(in_stmt)

    return NodeWithEdges(
        **NodeResponse.model_validate(node).model_dump(),
        outgoing=[EdgeResponse.model_validate(e) for e in out_result.scalars().all()],
        incoming=[EdgeResponse.model_validate(e) for e in in_result.scalars().all()],
    )


@app.patch("/nodes/{node_id}")
async def update_node(
    node_id: str,
    body: NodeUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    node = await session.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node {node_id!r} not found")

    if body.label is not None:
        node.label = body.label
    if body.properties is not None:
        node.properties = body.properties
    if body.source is not None:
        node.source = body.source

    await session.flush()

    result = NodeResponse.model_validate(node).model_dump(mode="json")
    return IQEnvelope(
        result=result,
        assumptions=[],
        confidence=1.0,
        trace=make_trace(result, body.model_dump(mode="json", exclude_none=True)),
    )


@app.delete("/nodes/{node_id}", status_code=204)
async def delete_node(
    node_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    node = await session.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node {node_id!r} not found")

    # Delete edges first (cascade should handle this, but be explicit)
    await session.execute(
        Edge.__table__.delete().where(
            (Edge.source_id == node_id) | (Edge.target_id == node_id)
        )
    )
    await session.delete(node)


# ── Edge CRUD ─────────────────────────────────────────────────────────────── #

@app.post("/edges", status_code=201)
async def create_edge(
    body: EdgeCreate,
    session: AsyncSession = Depends(get_db_session),
):
    # Validate both nodes exist
    source = await session.get(Node, body.source_id)
    if source is None:
        raise HTTPException(
            status_code=422, detail=f"Source node {body.source_id!r} not found"
        )
    target = await session.get(Node, body.target_id)
    if target is None:
        raise HTTPException(
            status_code=422, detail=f"Target node {body.target_id!r} not found"
        )

    edge = Edge(
        source_id=body.source_id,
        target_id=body.target_id,
        relationship_type=body.relationship_type.value,
        weight=body.weight,
        confidence=body.confidence,
        status=body.status.value,
        evidence=body.evidence,
    )
    session.add(edge)
    await session.flush()

    result = EdgeResponse.model_validate(edge).model_dump(mode="json")
    return IQEnvelope(
        result=result,
        assumptions=[],
        confidence=1.0,
        trace=make_trace(result, body.model_dump(mode="json")),
    )


@app.delete("/edges/{edge_id}", status_code=204)
async def delete_edge(
    edge_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    edge = await session.get(Edge, edge_id)
    if edge is None:
        raise HTTPException(status_code=404, detail=f"Edge {edge_id} not found")
    await session.delete(edge)


# ── Batch Ingest ──────────────────────────────────────────────────────────── #

@app.post("/nodes/batch")
async def batch_ingest_nodes(
    body: BatchIngestRequest,
    mode: str = Query("strict", pattern="^(strict|best_effort)$"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Bulk upsert nodes and edges from KnowEx or other pipelines.

    mode=strict: any error rolls back the entire batch (400).
    mode=best_effort: ingest what succeeds, return errors in response.

    New edges default to status="proposed" — they do NOT affect
    /heuristic results until manually validated via /review/edges.
    """
    try:
        result = await batch_ingest(
            session,
            nodes=body.nodes,
            edges=body.edges,
            source=body.source,
            mode=mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return IQEnvelope(
        result=BatchIngestResult(**result).model_dump(),
        assumptions=[
            f"mode={mode}",
            "New edges default to status=proposed",
            "Node properties are deep-merged on upsert",
            "Edge confidence takes max(existing, incoming)",
        ],
        confidence=1.0,
        trace=make_trace(result, body.model_dump(mode="json")),
    )


# ── Review Workflow ───────────────────────────────────────────────────────── #

@app.get("/review/edges")
async def list_review_edges(
    status: str = Query("proposed", pattern="^(proposed|validated|rejected)$"),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db_session),
):
    """List edges by status. Default: show proposed (pending review)."""
    stmt = (
        select(Edge)
        .where(Edge.status == status)
        .order_by(Edge.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    edges = result.scalars().all()
    return {
        "status_filter": status,
        "count": len(edges),
        "edges": [EdgeResponse.model_validate(e).model_dump(mode="json") for e in edges],
    }


@app.post("/review/edges/{edge_id}/validate")
async def validate_edge(
    edge_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    """Promote a proposed edge to validated — it will now affect /heuristic."""
    edge = await session.get(Edge, edge_id)
    if edge is None:
        raise HTTPException(status_code=404, detail=f"Edge {edge_id} not found")
    edge.status = "validated"
    await session.flush()
    result = EdgeResponse.model_validate(edge).model_dump(mode="json")
    return IQEnvelope(
        result=result,
        assumptions=["Edge is now active in /heuristic queries"],
        confidence=1.0,
        trace=make_trace(result, {"action": "validate", "edge_id": edge_id}),
    )


@app.post("/review/edges/{edge_id}/reject")
async def reject_edge(
    edge_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    """Reject a proposed edge — it will never affect /heuristic."""
    edge = await session.get(Edge, edge_id)
    if edge is None:
        raise HTTPException(status_code=404, detail=f"Edge {edge_id} not found")
    edge.status = "rejected"
    await session.flush()
    result = EdgeResponse.model_validate(edge).model_dump(mode="json")
    return IQEnvelope(
        result=result,
        assumptions=["Edge is now rejected and excluded from queries"],
        confidence=1.0,
        trace=make_trace(result, {"action": "reject", "edge_id": edge_id}),
    )


# ── Graph Queries ─────────────────────────────────────────────────────────── #

@app.post("/traverse")
async def traverse_graph(
    body: TraversalRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """BFS traversal from a start node."""
    rel_types = (
        [r.value for r in body.relationship_types]
        if body.relationship_types
        else None
    )
    nodes, edges, depth = await traverse(
        session,
        body.start_node_id,
        rel_types,
        body.max_depth,
        body.direction.value,
    )

    if not nodes:
        raise HTTPException(
            status_code=404,
            detail=f"Start node {body.start_node_id!r} not found",
        )

    result = TraversalResult(
        nodes=[NodeResponse.model_validate(n) for n in nodes],
        edges=[EdgeResponse.model_validate(e) for e in edges],
        depth_reached=depth,
    )
    return IQEnvelope(
        result=result.model_dump(mode="json"),
        assumptions=["BFS traversal, no cycle re-visiting"],
        confidence=1.0,
        trace=make_trace(
            result.model_dump(mode="json"),
            body.model_dump(mode="json"),
        ),
    )


@app.post("/paths")
async def find_graph_paths(
    body: PathRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Find all paths between two nodes."""
    raw_paths = await find_paths(
        session, body.source_id, body.target_id, body.max_depth
    )

    if not raw_paths:
        return IQEnvelope(
            result=PathResult(paths=[], shortest_length=0).model_dump(mode="json"),
            assumptions=["DFS path search, outgoing edges only"],
            confidence=0.0,
            trace=make_trace({"paths": []}, body.model_dump(mode="json")),
        )

    paths = []
    for raw_path in raw_paths:
        steps = []
        for node, edge in raw_path:
            steps.append(PathStep(
                node=NodeResponse.model_validate(node),
                edge=EdgeResponse.model_validate(edge) if edge else None,
            ))
        paths.append(steps)

    result = PathResult(
        paths=[[s.model_dump(mode="json") for s in p] for p in paths],
        shortest_length=len(raw_paths[0]) - 1 if raw_paths else 0,
    )
    return IQEnvelope(
        result=result.model_dump(mode="json"),
        assumptions=["DFS path search, outgoing edges only"],
        confidence=1.0,
        trace=make_trace(
            result.model_dump(mode="json"),
            body.model_dump(mode="json"),
        ),
    )


@app.post("/heuristic")
async def query_heuristics(
    body: HeuristicQuery,
    include_proposed: bool = Query(
        False,
        description="Include proposed (unvalidated) edges. Debug only.",
    ),
    session: AsyncSession = Depends(get_db_session),
):
    """
    The killer endpoint.

    Ask: "What tribal-knowledge adjustments apply when Employee X
    works on WorkCode Y for SignType Z?"

    SAFETY: Only uses validated edges by default. Set include_proposed=true
    for debugging to see what proposed heuristics would add.

    Returns adjustment factors with confidence and evidence chains.
    """
    if not any([body.employee_id, body.work_code, body.sign_type]):
        raise HTTPException(
            status_code=422,
            detail="Provide at least one of: employee_id, work_code, sign_type",
        )

    raw_adjustments, combined = await get_heuristic_adjustments(
        session,
        employee_id=body.employee_id,
        work_code=body.work_code,
        sign_type=body.sign_type,
        include_proposed=include_proposed,
    )

    adjustments = [HeuristicAdjustment(**a) for a in raw_adjustments]
    result = HeuristicResult(
        adjustments=adjustments,
        combined_factor=combined,
        query=body,
    )

    # Confidence is the minimum of all individual adjustment confidences,
    # or 0.0 if no heuristics matched
    confidence = (
        min(a.confidence for a in adjustments) if adjustments else 0.0
    )

    assumptions = [
        "Graph walk: EMPLOYEE --USES--> HEURISTIC --IMPACTS--> WORK_CODE",
        "Combined factor is the product of individual factors",
        f"Edge filter: {'validated+proposed' if include_proposed else 'validated only'}",
    ]
    if not adjustments:
        assumptions.append("No matching heuristics found in the graph")

    return IQEnvelope(
        result=result.model_dump(mode="json"),
        assumptions=assumptions,
        confidence=confidence,
        trace=make_trace(
            result.model_dump(mode="json"),
            body.model_dump(mode="json"),
        ),
    )
