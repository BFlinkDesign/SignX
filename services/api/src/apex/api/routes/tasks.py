"""Background task status endpoints."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException

from ..common.models import make_envelope
from ..deps import get_code_version, get_model_config
from ..schemas import ResponseEnvelope
from ..utils.celery_client import get_celery_client

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=ResponseEnvelope)
async def get_task_status(
    task_id: str,
) -> ResponseEnvelope:
    """Get status of a background task.
    
    Returns task state: PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED
    On success, includes result. On failure, includes error.
    """
    logger.info("task.status", task_id=task_id)
    assumptions: list[str] = []
    
    celery = get_celery_client()
    
    try:
        result = celery.AsyncResult(task_id)
        
        # Get task state and result
        state = result.state
        
        response_data: dict[str, Any] = {
            "task_id": task_id,
            "state": state,
        }
        
        if state == "SUCCESS":
            response_data["result"] = result.get()
            confidence = 0.95
        elif state == "FAILURE":
            response_data["error"] = str(result.info)
            confidence = 0.9
            add_assumption(assumptions, "Task failed")
        elif state == "PENDING":
            confidence = 0.5
            add_assumption(assumptions, "Task is still queued")
        elif state == "STARTED":
            confidence = 0.7
            add_assumption(assumptions, "Task is in progress")
        elif state == "RETRY":
            confidence = 0.6
            add_assumption(assumptions, "Task will be retried")
        else:
            confidence = 0.8
            response_data["info"] = result.info
        
        return make_envelope(
            result=response_data,
            assumptions=assumptions,
            confidence=confidence,
            inputs={"task_id": task_id},
            intermediates={"state": state},
            outputs=response_data,
            code_version=get_code_version(),
            model_config=get_model_config(),
        )
        
    except Exception as e:
        logger.error("task.status.error", task_id=task_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.delete("/{task_id}", response_model=ResponseEnvelope)
async def cancel_task(
    task_id: str,
) -> ResponseEnvelope:
    """Cancel a pending or in-progress task.
    
    Only works for PENDING or STARTED tasks.
    """
    logger.info("task.cancel", task_id=task_id)
    assumptions: list[str] = []
    
    celery = get_celery_client()
    
    try:
        result = celery.AsyncResult(task_id)
        
        # Check current state
        state = result.state
        
        if state in ["SUCCESS", "FAILURE", "REVOKED"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel task in {state} state"
            )
        
        # Revoke the task
        celery.control.revoke(task_id, terminate=True)
        
        assumptions.append(f"Task cancelled from {state} state")
        
        return make_envelope(
            result={
                "task_id": task_id,
                "state": "REVOKED",
                "cancelled": True,
            },
            assumptions=assumptions,
            confidence=0.95,
            inputs={"task_id": task_id},
            intermediates={"previous_state": state},
            outputs={"state": "REVOKED"},
            code_version=get_code_version(),
            model_config=get_model_config(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("task.cancel.error", task_id=task_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        )

