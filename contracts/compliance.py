"""Compliance contracts (Pydantic v2)."""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class ComplianceCheckRequest(BaseModel):
    task_id: str
    context: str = Field(..., description="Textual description or artifact refs")
    inputs: dict = Field(default_factory=dict)
    outputs: dict = Field(default_factory=dict)


class ComplianceCheckResponse(BaseModel):
    task_id: str
    flags: List[str]
    severity: str
    required_actions: List[str]
    audit_trail: List[str]
    signed_checksum: str


def schemas() -> Dict[str, dict]:
    return {
        "ComplianceCheckRequest": ComplianceCheckRequest.model_json_schema(),
        "ComplianceCheckResponse": ComplianceCheckResponse.model_json_schema(),
    }


