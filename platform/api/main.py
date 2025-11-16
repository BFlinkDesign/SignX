"""
SignX Studio Platform API

Main entry point for the integrated platform.
All modules register their routes with this application.
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from platform.registry import registry, ModuleDefinition, get_registry
from platform.events import event_bus, Event, get_event_bus
from typing import List
import os


# Create FastAPI application
app = FastAPI(
    title="SignX Studio",
    description="The integrated platform of the Sign Industry - All-in-one integrated platform",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Platform-level endpoints
@app.get("/api/v1/platform/health")
async def health_check():
    """
    Platform health check
    
    Returns overall health status and module count.
    """
    return {
        "status": "healthy",
        "version": "2.0.0",
        "platform": "SignX Studio",
        "description": "The integrated platform of the Sign Industry",
        "modules": {
            "total": len(registry.modules),
            "enabled": len([m for m in registry.modules.values() if m.enabled])
        }
    }


@app.get("/api/v1/platform/modules", response_model=List[ModuleDefinition])
async def list_modules(reg: object = Depends(get_registry)):
    """
    List all registered modules
    
    Returns module definitions with API routes, UI routes, and event integrations.
    Used by the frontend to build navigation and discover capabilities.
    """
    return registry.list_modules()


@app.get("/api/v1/platform/modules/{module_name}")
async def get_module(module_name: str):
    """Get specific module definition"""
    module = registry.get_module(module_name)
    if not module:
        return JSONResponse(
            status_code=404,
            content={"error": f"Module '{module_name}' not found"}
        )
    return module


@app.get("/api/v1/platform/events")
async def get_event_history(
    event_type: str = None,
    limit: int = 100,
    bus: object = Depends(get_event_bus)
):
    """
    Get recent event history
    
    Used for debugging and monitoring module interactions.
    """
    return {
        "events": event_bus.get_history(event_type, limit),
        "count": len(event_bus.get_history(event_type, limit))
    }


@app.post("/api/v1/platform/events/publish")
async def publish_event(event: Event):
    """
    Manually publish an event (for testing)
    
    In production, modules publish events directly via the event_bus.
    """
    await event_bus.publish(event)
    return {"status": "published", "event_id": event.id}


@app.get("/")
async def root():
    """Root endpoint - redirect to docs"""
    return {
        "platform": "SignX Studio",
        "version": "2.0.0",
        "description": "The integrated platform of the Sign Industry",
        "docs": "/api/docs",
        "modules": "/api/v1/platform/modules"
    }


# Module registration happens in modules/__init__.py
# Each module imports registry and calls registry.register()
# Then we include their routers here

def register_modules():
    """
    Register all modules with the platform
    
    This is called after all modules have been imported.
    Each module registers itself via registry.register().
    """
    logger.info("\n🚀 SignX Studio Platform Starting...")
    logger.info("=" * 60)
    
    # Import all modules (they auto-register via their __init__.py)
    try:
        from modules import engineering
        app.include_router(engineering.router)
    except ImportError as e:
        logger.info(f"⚠️ Engineering module not available: {e}")
    
    try:
        from modules import intelligence
        app.include_router(intelligence.router)
    except ImportError as e:
        logger.info(f"⚠️ Intelligence module not available: {e}")
    
    try:
        from modules import workflow
        app.include_router(workflow.router)
    except ImportError as e:
        logger.info(f"⚠️ Workflow module not available: {e}")
    
    try:
        from modules import documents
        app.include_router(documents.router)
    except ImportError as e:
        logger.info(f"⚠️ Documents module not available: {e}")
        
    try:
        from modules import quoting
        app.include_router(quoting.router)
    except ImportError as e:
        logger.info(f"⚠️ Quoting module not available: {e}")
    
    logger.info("=" * 60)
    logger.info(f"✅ Platform ready with {len(registry.modules)} module(s)")
    logger.info(f"📚 API docs: http://localhost:8000/api/docs")
    logger.info("=" * 60 + "\n")


@app.on_event("startup")
async def startup_event():
    """Register modules on startup"""
    register_modules()


if __name__ == "__main__":
    import uvicorn
import logging

logger = logging.getLogger(__name__)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

