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
    get_section_properties_async,
    get_section_properties_sync,
    validate_section_properties,
    AISCSectionProperties,
    AISCDatabaseError,
)

from .concrete_rebar_service import (
    ConcreteRebarService,
    RebarSize,
    ConcreteGrade,
    FoundationType,
    RebarScheduleInput,
    RebarBar,
    ConcreteVolume,
    RebarScheduleResult,
    DevelopmentLengthResult,
)

from .wind_loads_service import (
    WindLoadService,
    ExposureCategory,
    RiskCategory,
    WindLoadInput,
    VelocityPressureResult,
    WindForceResult,
)

from .cad_export_service import (
    CADExportService,
    CADExportOptions,
    CADFormat,
    DrawingScale,
    CADExportResult,
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
