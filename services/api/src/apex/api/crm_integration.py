"""KeyedIn CRM webhook integration for bidirectional sync."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

import structlog
import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from .models_audit import CRMWebhook
from .audit import log_audit
from .deps import settings

logger = structlog.get_logger(__name__)


class CRMWebhookPayload(BaseModel):
    """Standardized webhook payload format."""
    
    event_type: str  # project.created, calculation.completed, cost.updated
    source: str  # keyedin, calcusign
    project_id: Optional[str] = None
    calculation_id: Optional[str] = None
    data: dict
    timestamp: Optional[datetime] = None


class CRMClient:
    """Client for sending webhooks to KeyedIn CRM."""
    
    def __init__(self, webhook_url: Optional[str] = None, api_key: Optional[str] = None):
        self.webhook_url = webhook_url or settings.KEYEDIN_WEBHOOK_URL if hasattr(settings, "KEYEDIN_WEBHOOK_URL") else None
        self.api_key = api_key or settings.KEYEDIN_API_KEY if hasattr(settings, "KEYEDIN_API_KEY") else None
        self.timeout = 30.0
    
    async def send_webhook(
        self,
        event_type: str,
        data: dict,
        direction: str = "outbound",
        db: Optional[AsyncSession] = None,
    ) -> bool:
        """Send webhook to KeyedIn CRM.
        
        Args:
            event_type: Event type (e.g., "calculation.completed")
            data: Payload data
            direction: "outbound" (calcusign → keyedin) or "inbound" (keyedin → calcusign)
            db: Optional database session for logging
        
        Returns:
            True if webhook sent successfully, False otherwise
        """
        if not self.webhook_url:
            logger.warning("crm.webhook_not_configured", event_type=event_type)
            return False
        
        payload = {
            "event_type": event_type,
            "source": "calcusign",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "APEX-Calcusign/1.0",
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Log webhook attempt
        webhook_record = CRMWebhook(
            event_type=event_type,
            direction=direction,
            source="calcusign",
            payload=payload,
            status="pending",
        )
        
        if db:
            db.add(webhook_record)
            await db.commit()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers=headers,
                )
                
                webhook_record.status = "delivered" if response.status_code < 400 else "failed"
                webhook_record.response_code = response.status_code
                webhook_record.response_body = response.text[:1000]  # Truncate long responses
                webhook_record.processed_at = datetime.now(timezone.utc)
                
                if db:
                    await db.commit()
                
                if response.status_code >= 400:
                    logger.error(
                        "crm.webhook_failed",
                        event_type=event_type,
                        status_code=response.status_code,
                        response=response.text[:200],
                    )
                    return False
                
                logger.info("crm.webhook_sent", event_type=event_type, status_code=response.status_code)
                return True
                
        except Exception as e:
            webhook_record.status = "failed"
            webhook_record.response_body = str(e)[:1000]
            webhook_record.processed_at = datetime.now(timezone.utc)
            
            if db:
                await db.commit()
            
            logger.error("crm.webhook_error", event_type=event_type, error=str(e))
            return False
    
    async def handle_inbound_webhook(
        self,
        payload: CRMWebhookPayload,
        db: AsyncSession,
        user_id: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> dict:
        """Handle inbound webhook from KeyedIn CRM.
        
        Events from KeyedIn:
        - project.created: New project created in KeyedIn
        - project.updated: Project updated in KeyedIn
        - project.deleted: Project deleted in KeyedIn
        
        Returns:
            Processing result
        """
        # Log webhook
        webhook_record = CRMWebhook(
            event_type=payload.event_type,
            direction="inbound",
            source="keyedin",
            payload=payload.data,
            status="pending",
        )
        db.add(webhook_record)
        await db.commit()
        
        try:
            if payload.event_type == "project.created":
                # Create project in Calcusign from KeyedIn
                result = await self._create_project_from_keyedin(payload, db, user_id, account_id)
                
            elif payload.event_type == "project.updated":
                # Update project in Calcusign
                result = await self._update_project_from_keyedin(payload, db, user_id, account_id)
                
            elif payload.event_type == "project.deleted":
                # Mark project as deleted (soft delete)
                result = await self._delete_project_from_keyedin(payload, db, user_id, account_id)
                
            else:
                logger.warning("crm.unknown_event_type", event_type=payload.event_type)
                result = {"status": "ignored", "reason": "unknown_event_type"}
            
            webhook_record.status = "delivered"
            webhook_record.processed_at = datetime.now(timezone.utc)
            await db.commit()
            
            # Log audit
            await log_audit(
                db=db,
                action=f"crm.webhook_received",
                resource_type="webhook",
                resource_id=str(webhook_record.webhook_id),
                user_id=user_id or "system",
                account_id=account_id or "unknown",
                after_state={"event_type": payload.event_type, "result": result},
            )
            
            return result
            
        except Exception as e:
            webhook_record.status = "failed"
            webhook_record.response_body = str(e)[:1000]
            webhook_record.processed_at = datetime.now(timezone.utc)
            await db.commit()
            
            logger.error("crm.webhook_processing_failed", event_type=payload.event_type, error=str(e))
            raise
    
    async def _create_project_from_keyedin(
        self,
        payload: CRMWebhookPayload,
        db: AsyncSession,
        user_id: Optional[str],
        account_id: Optional[str],
    ) -> dict:
        """Create project in Calcusign from KeyedIn project data."""
        from .db import Project
        
        keyedin_id = payload.data.get("keyedin_id")
        project_name = payload.data.get("name", "Unknown Project")
        
        # Check if project already exists (by KeyedIn ID or name)
        from sqlalchemy import select
        
        existing = await db.execute(
            select(Project).where(Project.name == project_name)
        )
        if existing.scalar_one_or_none():
            return {"status": "exists", "message": "Project already exists"}
        
        # Create new project
        project = Project(
            project_id=f"keyedin-{keyedin_id}" if keyedin_id else f"imported-{datetime.now(timezone.utc).isoformat()}",
            account_id=account_id or "unknown",
            name=project_name,
            customer=payload.data.get("customer"),
            description=payload.data.get("description"),
            status="draft",
            created_by=user_id or "keyedin-import",
            updated_by=user_id or "keyedin-import",
        )
        
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        logger.info("crm.project_created", project_id=project.project_id, keyedin_id=keyedin_id)
        
        return {"status": "created", "project_id": project.project_id}
    
    async def _update_project_from_keyedin(
        self,
        payload: CRMWebhookPayload,
        db: AsyncSession,
        user_id: Optional[str],
        account_id: Optional[str],
    ) -> dict:
        """Update project in Calcusign from KeyedIn updates."""
        from .db import Project
        from sqlalchemy import select
        
        keyedin_id = payload.data.get("keyedin_id")
        
        # Find project by KeyedIn ID or name
        project = await db.execute(
            select(Project).where(Project.project_id.like(f"%{keyedin_id}%"))
        )
        project = project.scalar_one_or_none()
        
        if not project:
            return {"status": "not_found", "message": "Project not found"}
        
        # Update fields
        if "name" in payload.data:
            project.name = payload.data["name"]
        if "customer" in payload.data:
            project.customer = payload.data["customer"]
        if "description" in payload.data:
            project.description = payload.data["description"]
        if "status" in payload.data:
            project.status = payload.data["status"]
        
        project.updated_by = user_id or "keyedin-import"
        await db.commit()
        
        logger.info("crm.project_updated", project_id=project.project_id)
        
        return {"status": "updated", "project_id": project.project_id}
    
    async def _delete_project_from_keyedin(
        self,
        payload: CRMWebhookPayload,
        db: AsyncSession,
        user_id: Optional[str],
        account_id: Optional[str],
    ) -> dict:
        """Soft delete project (mark as deleted)."""
        from .db import Project
        from sqlalchemy import select
        
        keyedin_id = payload.data.get("keyedin_id")
        
        project = await db.execute(
            select(Project).where(Project.project_id.like(f"%{keyedin_id}%"))
        )
        project = project.scalar_one_or_none()
        
        if not project:
            return {"status": "not_found"}
        
        # Soft delete: update status
        project.status = "deleted"
        project.updated_by = user_id or "keyedin-import"
        await db.commit()
        
        logger.info("crm.project_deleted", project_id=project.project_id)
        
        return {"status": "deleted", "project_id": project.project_id}


# Global CRM client instance
crm_client = CRMClient()

