"""
Event Bus - Inter-module communication

Provides pub/sub messaging for loosely coupled module integration.
All events are stored in the database for audit trails.
"""
import asyncio
from typing import Callable, Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import json
import uuid
import logging

logger = logging.getLogger(__name__)


class Event(BaseModel):
    """
    Platform event
    
    Events enable modules to communicate without tight coupling.
    Every event is stored in the database for complete audit trail.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = Field(..., description="Event type (e.g., 'project.created')")
    source: str = Field(..., description="Module that emitted the event")
    project_id: Optional[str] = Field(None, description="Related project ID")
    user_id: Optional[str] = Field(None, description="User who triggered event")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event payload")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "project.created",
                "source": "workflow",
                "project_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "brady@eaglesign.net",
                "data": {
                    "customer": "Valley Church",
                    "quote_number": "39657",
                    "salesperson": "Jeff"
                }
            }
        }


class EventBus:
    """
    Pub/sub event bus for module communication
    
    Modules subscribe to event types and receive callbacks when events occur.
    All events are persisted to database for audit trails.
    """
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_history: List[Event] = []  # In-memory cache (last 1000)
        
    def subscribe(self, event_type: str, handler: Callable):
        """
        Subscribe to an event type
        
        Args:
            event_type: Event type pattern (e.g., "project.created" or "project.*")
            handler: Async function to call when event occurs
            
        Example:
            ```python
            async def on_project_created(event: Event):
                logger.info(f"New project: {event.project_id}")
                
            event_bus.subscribe("project.created", on_project_created)
            ```
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        logger.info(f"📡 Subscribed to event: {event_type}")
        
    async def publish(self, event: Event):
        """
        Publish event to all subscribers
        
        Args:
            event: Event to publish
            
        The event will be:
        1. Stored in database for audit trail
        2. Added to in-memory cache
        3. Delivered to all matching subscribers
        """
        # Store in database
        await self._store_event(event)
        
        # Add to cache
        self.event_history.append(event)
        if len(self.event_history) > 1000:
            self.event_history = self.event_history[-1000:]
        
        # Find matching subscribers
        handlers = []
        for pattern, subs in self.subscribers.items():
            if self._matches(event.type, pattern):
                handlers.extend(subs)
        
        # Notify subscribers (non-blocking)
        if handlers:
            logger.info(f"🚀 Publishing event: {event.type} to {len(handlers)} subscriber(s)")
            try:
                await asyncio.gather(*[handler(event) for handler in handlers])
            except Exception as e:
                logger.error(f"⚠️ Error in event handler: {e}")
                # Don't let subscriber errors break the publisher
        
    async def _store_event(self, event: Event):
        """
        Store event in database
        
        TODO: Implement actual database storage
        Currently just logs to console
        """
        # This will eventually insert into project_events table
        logger.info(f"💾 Event stored: {event.type} [{event.id}]")
        
    def _matches(self, event_type: str, pattern: str) -> bool:
        """
        Check if event type matches subscription pattern
        
        Supports:
        - Exact match: "project.created"
        - Wildcard: "project.*" matches "project.created", "project.updated", etc.
        """
        if pattern == event_type:
            return True
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return event_type.startswith(prefix + ".")
        return False
        
    def get_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[Event]:
        """
        Get recent event history
        
        Args:
            event_type: Filter by event type (None = all)
            limit: Max number of events to return
        """
        events = self.event_history
        if event_type:
            events = [e for e in events if self._matches(e.type, event_type)]
        return events[-limit:]


# Global event bus instance
event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Dependency injection for FastAPI routes"""
    return event_bus

