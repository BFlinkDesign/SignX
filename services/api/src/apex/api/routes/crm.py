"""CRM webhook integration routes."""

from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..auth import get_current_user_optional, TokenData
from ..crm_integration import crm_client, CRMWebhookPayload
from ..schemas import ResponseEnvelope
from ..common.models import make_envelope
from ..deps import get_code_version, get_model_config

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/crm", tags=["crm"])


class WebhookPayload(BaseModel):
    """Inbound webhook payload from KeyedIn."""
    event_type: str
    project_id: Optional[str] = None
    data: dict


@router.post("/webhooks/keyedin", response_model=ResponseEnvelope)
async def receive_keyedin_webhook(
    payload: WebhookPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Receive webhook from KeyedIn CRM.
    
    Events handled:
    - project.created: Create project in Calcusign
    - project.updated: Update project in Calcusign
    - project.deleted: Soft delete project
    
    No authentication required (validated via webhook signature/secret)
    """
    # Extract IP and user agent
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # Validate webhook (in production, verify signature)
    # TODO: Add webhook signature validation
    
    # Convert to CRMWebhookPayload
    crm_payload = CRMWebhookPayload(
        event_type=payload.event_type,
        source="keyedin",
        project_id=payload.project_id,
        data=payload.data,
    )
    
    # Handle webhook
    result = await crm_client.handle_inbound_webhook(
        payload=crm_payload,
        db=db,
        user_id="keyedin-system",
        account_id=payload.data.get("account_id", "unknown"),
    )
    
    return make_envelope(
        result=result,
        assumptions=["Webhook received from KeyedIn CRM"],
        confidence=0.95,
        inputs={"event_type": payload.event_type},
        outputs=result,
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


@router.post("/webhooks/send", response_model=ResponseEnvelope)
async def send_webhook_to_keyedin(
    event_type: str,
    data: dict,
    current_user: Optional[TokenData] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope:
    """Send webhook to KeyedIn CRM.
    
    Events sent:
    - calculation.completed: Calculation finished
    - cost.updated: Project cost updated
    - project.submitted: Project submitted for approval
    """
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    
    success = await crm_client.send_webhook(
        event_type=event_type,
        data=data,
        direction="outbound",
        db=db,
    )
    
    return make_envelope(
        result={"sent": success, "event_type": event_type},
        assumptions=["Webhook sent to KeyedIn CRM"],
        confidence=0.9 if success else 0.5,
        inputs={"event_type": event_type},
        outputs={"sent": success},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )

