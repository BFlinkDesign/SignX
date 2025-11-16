from __future__ import annotations

import uuid
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..common.utils import build_envelope


router = APIRouter(prefix="/projects", tags=["projects"])

# In-memory stub store (dev only)
_PROJECTS: dict[str, dict[str, Any]] = {}


class ProjectCreate(BaseModel):
    name: str
    notes: str | None = None


@router.get("")
async def list_projects():
    return build_envelope(result={"projects": list(_PROJECTS.values())}, inputs={"count": len(_PROJECTS)})


@router.post("")
async def create_project(payload: ProjectCreate):
    pid = str(uuid.uuid4())
    data = {"id": pid, "name": payload.name, "notes": payload.notes or "", "status": "draft"}
    _PROJECTS[pid] = data
    return build_envelope(result=data, assumptions=["in_memory_store"], inputs=payload.model_dump())


@router.get("/{project_id}")
async def get_project(project_id: str):
    proj = _PROJECTS.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="not_found")
    return build_envelope(result=proj)
