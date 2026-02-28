"""
models.py — Node + Edge ORM for the 500IQ Knowledge Graph.

Adjacency-list model in SQLite.  Nodes are entities (jobs, employees,
heuristics, materials, failure modes).  Edges are typed, weighted,
confidence-scored relationships between them.

Example graph walk:
  EMPLOYEE-JEFF  --USES-->  HEURISTIC-JEFF-CABINET-PADDING
                              --IMPACTS-->  WORK_CODE-FAB-CABINET
                              --LEARNED_FROM-->  JOB-45678

This lets the system answer: "What adjustments does Jeff apply to
cabinet fabrication, and where did he learn them?"
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    event,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

from database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Node(Base):
    """An entity in the knowledge graph."""

    __tablename__ = "nodes"

    id = Column(String, primary_key=True)
    type = Column(String, nullable=False)
    label = Column(String, nullable=False, default="")
    properties = Column(JSON, nullable=False, default=dict)
    source = Column(String, nullable=False, default="manual")
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    outgoing_edges = relationship(
        "Edge",
        foreign_keys="Edge.source_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    incoming_edges = relationship(
        "Edge",
        foreign_keys="Edge.target_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_nodes_type", "type"),
        Index("ix_nodes_source", "source"),
    )

    def __repr__(self) -> str:
        return f"<Node {self.id!r} type={self.type!r}>"


class Edge(Base):
    """A typed, weighted relationship between two nodes."""

    __tablename__ = "edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(
        String, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False
    )
    target_id = Column(
        String, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type = Column(String, nullable=False)
    weight = Column(Float, nullable=False, default=1.0)
    confidence = Column(Float, nullable=False, default=1.0)
    evidence = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    source_node = relationship(
        "Node", foreign_keys=[source_id], back_populates="outgoing_edges"
    )
    target_node = relationship(
        "Node", foreign_keys=[target_id], back_populates="incoming_edges"
    )

    __table_args__ = (
        Index("ix_edges_source_rel", "source_id", "relationship_type"),
        Index("ix_edges_target_rel", "target_id", "relationship_type"),
        Index("ix_edges_rel_type", "relationship_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<Edge {self.source_id!r} --{self.relationship_type}--> "
            f"{self.target_id!r} conf={self.confidence}>"
        )


# --------------------------------------------------------------------------- #
# Enable SQLite foreign key enforcement (off by default in SQLite)
# --------------------------------------------------------------------------- #
@event.listens_for(Node.__table__, "after_create")
def _enable_fk(target, connection, **kw):
    pass  # handled at engine level


# Node types and relationship types as constants for validation
NODE_TYPES = frozenset({
    "JOB",
    "EMPLOYEE",
    "HEURISTIC",
    "MATERIAL",
    "FAILURE_MODE",
    "WORK_CODE",
    "CUSTOMER",
    "SIGN_TYPE",
    "CONSTRAINT",
})

RELATIONSHIP_TYPES = frozenset({
    "CAUSED_BY",
    "PREFERS",
    "VIOLATES",
    "LEARNED_FROM",
    "USES",
    "IMPACTS",
    "WORKED_ON",
    "SIMILAR_TO",
    "ADJUSTS",
    "APPLIES_TO",
    "INFLUENCED_BY",
    "REQUIRES",
})
