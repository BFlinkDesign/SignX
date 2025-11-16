"""
Workflow Module - Quote automation (EagleHub rewritten in Python)

This module automates the quote-to-project workflow:
- Email monitoring (Outlook "BID REQUEST" folders)
- KeyedIn CRM integration
- File organization with naming conventions
- Automatic project creation

Status: 🔄 In development (converting PowerShell to Python)
"""
from fastapi import APIRouter, BackgroundTasks
from platform.registry import registry, ModuleDefinition
from platform.events import event_bus, Event
import logging

logger = logging.getLogger(__name__)

# Module definition
module_def = ModuleDefinition(
    name="workflow",
    version="1.0.0",
    display_name="Workflow",
    description="Automated quote-to-project pipeline with email monitoring",
    api_prefix="/api/v1/workflow",
    ui_routes=["/workflow/dashboard", "/workflow/activity"],
    nav_order=1,
    icon="flow",
    events_consumed=[],
    events_published=["quote.received", "file.organized", "keyedin.updated"]
)

# API router
router = APIRouter(prefix="/api/v1/workflow", tags=["workflow"])


@router.get("/status")
async def get_workflow_status():
    """Get workflow automation status"""
    return {
        "module": "workflow",
        "status": "monitoring",
        "email_monitoring": True,
        "last_check": "2025-11-10T10:30:00Z",
        "pending_quotes": 3,
        "folders_monitored": [
            "BID REQUEST/Jeff",
            "BID REQUEST/Joe",
            "BID REQUEST/Rich",
            "BID REQUEST/Mike E"
        ]
    }


@router.post("/monitor/email")
async def trigger_email_check(background_tasks: BackgroundTasks):
    """
    Manually trigger email monitoring
    
    Also runs automatically every 30 minutes via scheduler.
    """
    background_tasks.add_task(check_bid_requests)
    return {
        "status": "triggered",
        "message": "Email monitoring started in background"
    }


@router.get("/activity")
async def get_recent_activity(limit: int = 50):
    """
    Get recent workflow activity
    
    Returns recent events for dashboard display:
    - Quotes received
    - Files organized
    - Projects created
    """
    # Get events from event bus
    events = event_bus.get_history("quote.*", limit=limit)
    
    return {
        "activity": [
            {
                "timestamp": e.timestamp,
                "type": e.type,
                "project_id": e.project_id,
                "description": _format_activity(e)
            }
            for e in events
        ],
        "count": len(events)
    }


def _format_activity(event: Event) -> str:
    """Format event as human-readable activity"""
    if event.type == "quote.received":
        customer = event.data.get("customer", "Unknown")
        return f"New quote from {customer}"
    elif event.type == "file.organized":
        return f"Files organized for project"
    return event.type


async def check_bid_requests():
    """
    Check Outlook for new bid requests
    
    This is the Python replacement for EagleHub PowerShell script.
    """
    logger.info("📧 Workflow: Checking for new bid requests...")
    
    # TODO: Implement actual email monitoring
    # from .email_monitor import check_outlook_folders
    # await check_outlook_folders()
    
    # For now, simulate finding a quote
    await event_bus.publish(Event(
        type="quote.received",
        source="workflow",
        project_id="39657",
        data={
            "salesperson": "Jeff",
            "customer": "Valley Church",
            "subject": "BID REQUEST - Valley Church Halo Letters",
            "attachments": ["valley-church-drawing.pdf"]
        }
    ))


# Register with platform
registry.register(module_def, router)

