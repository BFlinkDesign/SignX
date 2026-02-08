"""
Domain Services for Signage Engineering

Service layer provides business logic for structural calculations
with dependency injection, comprehensive error handling, and audit trails.

Architecture:
- Services are stateful classes (not pure functions)
- Support dependency injection for testing
- Comprehensive logging and error handling
- Type-safe with Pydantic validation
"""

from .aisc_database import (
    AISCDatabaseError,
    AISCSectionProperties,
    get_section_properties_async,
    get_section_properties_sync,
    validate_section_properties,
)
from .cad_export_service import (
    CADExportOptions,
    CADExportResult,
    CADExportService,
    CADFormat,
    DrawingScale,
)
from .concrete_rebar_service import (
    ConcreteGrade,
    ConcreteRebarService,
    ConcreteVolume,
    DevelopmentLengthResult,
    FoundationType,
    RebarBar,
    RebarScheduleInput,
    RebarScheduleResult,
    RebarSize,
)
from .wind_loads_service import (
    ExposureCategory,
    RiskCategory,
    VelocityPressureResult,
    WindForceResult,
    WindLoadInput,
    WindLoadService,
)

__all__ = [
    # AISC Database Service
    "get_section_properties_async",
    "get_section_properties_sync",
    "validate_section_properties",
    "AISCSectionProperties",
    "AISCDatabaseError",
    # Concrete & Rebar Service
    "ConcreteRebarService",
    "RebarSize",
    "ConcreteGrade",
    "FoundationType",
    "RebarScheduleInput",
    "RebarBar",
    "ConcreteVolume",
    "RebarScheduleResult",
    "DevelopmentLengthResult",
    # Wind Load Service
    "WindLoadService",
    "ExposureCategory",
    "RiskCategory",
    "WindLoadInput",
    "VelocityPressureResult",
    "WindForceResult",
    # CAD Export Service
    "CADExportService",
    "CADExportOptions",
    "CADFormat",
    "DrawingScale",
    "CADExportResult",
]
