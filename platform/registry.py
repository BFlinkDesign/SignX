"""
Module Registry - modular platform-style plugin system

Allows modules to register themselves with the platform and discover each other.
"""
from typing import Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field
from datetime import datetime


class ModuleDefinition(BaseModel):
    """
    Definition of a platform module
    
    Each module in SignX Studio registers itself using this definition.
    Modules are loosely coupled and communicate via events.
    """
    name: str = Field(..., description="Unique module identifier")
    version: str = Field(..., description="Semantic version")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Module purpose")
    
    # API configuration
    api_prefix: str = Field(..., description="API route prefix (e.g., /api/v1/engineering)")
    
    # UI configuration
    ui_routes: List[str] = Field(default_factory=list, description="React routes this module owns")
    nav_order: int = Field(default=100, description="Order in navigation menu")
    icon: str = Field(default="cube", description="Icon name for UI")
    
    # Event integration
    events_consumed: List[str] = Field(default_factory=list, description="Events this module listens to")
    events_published: List[str] = Field(default_factory=list, description="Events this module emits")
    
    # Metadata
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    enabled: bool = Field(default=True)
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "engineering",
                "version": "1.0.0",
                "display_name": "Engineering",
                "description": "Structural calculations and design",
                "api_prefix": "/api/v1/engineering",
                "ui_routes": ["/projects/:id/engineering"],
                "nav_order": 2,
                "icon": "calculator",
                "events_consumed": ["project.created", "design.updated"],
                "events_published": ["calculations.completed", "design.approved"]
            }
        }


class ModuleRegistry:
    """
    Central registry for all platform modules
    
    Manages module lifecycle, discovery, and dependency resolution.
    """
    
    def __init__(self):
        self.modules: Dict[str, ModuleDefinition] = {}
        self.routers: Dict[str, APIRouter] = {}
        
    def register(
        self,
        module: ModuleDefinition,
        router: APIRouter
    ) -> APIRouter:
        """
        Register a module with the platform
        
        Args:
            module: Module definition
            router: FastAPI router with module endpoints
            
        Returns:
            The same router (for chaining)
            
        Example:
            ```python
            from platform.registry import registry, ModuleDefinition
import logging

logger = logging.getLogger(__name__)
            
            module_def = ModuleDefinition(
                name="engineering",
                version="1.0.0",
                display_name="Engineering",
                description="Structural calculations",
                api_prefix="/api/v1/engineering"
            )
            
            router = APIRouter(prefix="/api/v1/engineering")
            registry.register(module_def, router)
            ```
        """
        if module.name in self.modules:
            raise ValueError(f"Module '{module.name}' is already registered")
            
        self.modules[module.name] = module
        self.routers[module.name] = router
        
        logger.info(f"✅ Registered module: {module.display_name} v{module.version}")
        return router
        
    def get_module(self, name: str) -> Optional[ModuleDefinition]:
        """Get module definition by name"""
        return self.modules.get(name)
        
    def get_router(self, name: str) -> Optional[APIRouter]:
        """Get module router by name"""
        return self.routers.get(name)
        
    def list_modules(self, enabled_only: bool = True) -> List[ModuleDefinition]:
        """
        List all registered modules
        
        Args:
            enabled_only: If True, only return enabled modules
        """
        modules = list(self.modules.values())
        if enabled_only:
            modules = [m for m in modules if m.enabled]
        return sorted(modules, key=lambda m: m.nav_order)
        
    def get_event_subscribers(self, event_type: str) -> List[str]:
        """Get list of module names that subscribe to an event"""
        return [
            name for name, module in self.modules.items()
            if event_type in module.events_consumed
        ]
        
    def get_event_publishers(self, event_type: str) -> List[str]:
        """Get list of module names that publish an event"""
        return [
            name for name, module in self.modules.items()
            if event_type in module.events_published
        ]


# Global registry instance
registry = ModuleRegistry()


def get_registry() -> ModuleRegistry:
    """Dependency injection for FastAPI routes"""
    return registry

