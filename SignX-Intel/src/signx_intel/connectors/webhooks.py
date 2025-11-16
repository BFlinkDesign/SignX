"""Webhook support for event-driven integrations."""
from typing import Dict, Any, Callable
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel


class WebhookEvent(BaseModel):
    """Webhook event schema."""
    event_type: str
    source: str
    payload: Dict[str, Any]
    timestamp: str


class WebhookManager:
    """Manage webhook registrations and dispatch."""
    
    def __init__(self):
        """Initialize webhook manager."""
        self.handlers: Dict[str, list[Callable]] = {}
        self.router = APIRouter()
        
        # Register webhook endpoint
        @self.router.post("/webhooks/{source}")
        async def receive_webhook(source: str, request: Request):
            """Receive and dispatch webhook events."""
            body = await request.json()
            event = WebhookEvent(
                event_type=body.get("event_type", "unknown"),
                source=source,
                payload=body.get("payload", {}),
                timestamp=body.get("timestamp", "")
            )
            
            await self.dispatch(event)
            
            return {"status": "received", "event_type": event.event_type}
    
    def register_handler(self, event_type: str, handler: Callable):
        """
        Register a handler for an event type.
        
        Args:
            event_type: Event type to listen for
            handler: Async function to handle the event
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    async def dispatch(self, event: WebhookEvent):
        """
        Dispatch event to registered handlers.
        
        Args:
            event: Webhook event
        """
        handlers = self.handlers.get(event.event_type, [])
        
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                print(f"Error in webhook handler for {event.event_type}: {e}")
    
    async def send_webhook(
        self,
        url: str,
        event_type: str,
        payload: Dict[str, Any]
    ):
        """
        Send webhook to external system.
        
        Args:
            url: Webhook URL
            event_type: Event type
            payload: Event payload
        """
        import httpx
        from datetime import datetime
        
        async with httpx.AsyncClient() as client:
            await client.post(
                url,
                json={
                    "event_type": event_type,
                    "source": "signx-intel",
                    "payload": payload,
                    "timestamp": datetime.utcnow().isoformat()
                },
                timeout=10.0
            )

