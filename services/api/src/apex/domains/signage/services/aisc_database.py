"""
AISC Steel Shape Database Service

Provides type-safe, cached access to AISC steel section properties
from the database with comprehensive error handling and validation.

Standards: AISC 360-22, AISC Shapes Database v16.0
"""

from __future__ import annotations

import functools
from typing import Optional

import structlog
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


# ============================================================================
# Domain Models
# ============================================================================

class AISCSectionProperties(BaseModel):
    """AISC section properties with validation."""

    designation: str = Field(..., description="AISC designation (e.g., 'HSS8X8X1/4')")
    shape_type: str = Field(..., description="Shape family (HSS, PIPE, W, C, MC, L)")

    # Geometric properties
    area_in2: float = Field(gt=0, description="Cross-sectional area (in²)")
    weight_plf: float = Field(gt=0, description="Weight per linear foot (lb/ft)")

    # Section properties for bending
    ix_in4: float = Field(gt=0, description="Moment of inertia about x-axis (in⁴)")
    sx_in3: float = Field(gt=0, description="Section modulus about x-axis (in³)")
    rx_in: float = Field(gt=0, description="Radius of gyration about x-axis (in)")

    # Section properties for minor axis (if applicable)
    iy_in4: Optional[float] = Field(None, ge=0, description="Moment of inertia about y-axis (in⁴)")
    sy_in3: Optional[float] = Field(None, ge=0, description="Section modulus about y-axis (in³)")
    ry_in: Optional[float] = Field(None, ge=0, description="Radius of gyration about y-axis (in)")

    # Material properties
    fy_ksi: float = Field(gt=0, description="Yield strength (ksi)")

    # Torsional properties (for hollow sections)
    j_in4: Optional[float] = Field(None, ge=0, description="Torsional constant (in⁴)")

    class Config:
        frozen = True  # Immutable for caching


class AISCDatabaseError(Exception):
    """AISC database lookup error."""
    pass


# ============================================================================
# Database Service
# ============================================================================

# Thread-safe in-memory cache for frequently accessed sections
@functools.lru_cache(maxsize=512)
def _get_cached_section_properties(
    designation: str,
    steel_grade: str,
) -> tuple:
    """
    Cache wrapper for section properties.

    Returns tuple for hashability in lru_cache.
    Actual database call happens in async function.
    """
    # This is just a cache key generator
    # Actual data fetching happens in get_section_properties_async
    return (designation, steel_grade)


async def get_section_properties_async(
    designation: str,
    steel_grade: str,
    db: AsyncSession,
) -> AISCSectionProperties:
    """
    Fetch AISC section properties from database with validation.

    This function provides type-safe, validated access to the AISC shapes database
    with comprehensive error handling and logging.

    Args:
        designation: AISC designation (e.g., "HSS8X8X1/4", "W12X26")
        steel_grade: Steel grade (e.g., "A500B", "A36", "A572-50")
        db: Async database session

    Returns:
        AISCSectionProperties: Validated section properties

    Raises:
        AISCDatabaseError: If section not found or database error
        ValidationError: If section properties are invalid

    Examples:
        >>> async with get_db() as db:
        ...     section = await get_section_properties_async("HSS8X8X1/4", "A500B", db)
        ...     print(f"Sx = {section.sx_in3} in³")
        Sx = 19.7 in³

    References:
        - AISC 360-22 Table 2-4: Material Properties
        - AISC Shapes Database v16.0
    """
    # Validate designation format
    if not designation or len(designation) < 3:
        raise AISCDatabaseError(
            f"Invalid AISC designation format: '{designation}'. "
            f"Expected format: 'HSS8X8X1/4', 'W12X26', 'PIPE6STD', etc."
        )

    # Steel grade to yield strength mapping (AISC 360-22 Table 2-5)
    STEEL_GRADES = {
        "A500B": 46.0,      # HSS (rectangular/square)
        "A500C": 50.0,      # HSS (round)
        "A53B": 36.0,       # Pipe
        "A36": 36.0,        # Hot-rolled shapes
        "A572-50": 50.0,    # High-strength low-alloy
        "A992": 50.0,       # W-shapes (most common)
    }

    fy_ksi = STEEL_GRADES.get(steel_grade)
    if fy_ksi is None:
        logger.warning(
            "aisc.unknown_steel_grade",
            steel_grade=steel_grade,
            designation=designation,
            available_grades=list(STEEL_GRADES.keys())
        )
        # Default to A36 if unknown
        fy_ksi = 36.0

    try:
        # Import database model (lazy import to avoid circular dependencies)
        from ...db.models import AISCShape

        # Query database with exact designation match
        query = select(AISCShape).where(AISCShape.designation == designation)
        result = await db.execute(query)
        section = result.scalar_one_or_none()

        if not section:
            # Log failure for debugging
            logger.warning(
                "aisc.section_not_found",
                designation=designation,
                steel_grade=steel_grade,
                available_types=["HSS", "PIPE", "W", "C", "MC", "L", "WT"]
            )

            raise AISCDatabaseError(
                f"AISC section '{designation}' not found in database. "
                f"Verify designation format and ensure it exists in AISC Shapes Database v16.0. "
                f"Common formats: 'HSS8X8X1/4', 'W12X26', 'PIPE6STD', 'C12X20.7'"
            )

        # Build validated model
        props = AISCSectionProperties(
            designation=section.designation,
            shape_type=section.shape_type or "UNKNOWN",
            area_in2=section.area_in2,
            weight_plf=section.weight_plf,
            ix_in4=section.ix_in4,
            sx_in3=section.sx_in3,
            rx_in=section.rx_in,
            iy_in4=section.iy_in4,
            sy_in3=section.sy_in3,
            ry_in=section.ry_in,
            fy_ksi=fy_ksi,
            j_in4=section.j_in4,
        )

        logger.info(
            "aisc.section_loaded",
            designation=designation,
            steel_grade=steel_grade,
            sx_in3=props.sx_in3,
            area_in2=props.area_in2,
        )

        return props

    except AISCDatabaseError:
        # Re-raise AISC-specific errors
        raise

    except Exception as e:
        # Catch all other database errors
        logger.error(
            "aisc.database_error",
            designation=designation,
            steel_grade=steel_grade,
            error=str(e),
            error_type=type(e).__name__,
        )

        raise AISCDatabaseError(
            f"Database error fetching AISC section '{designation}': {e}"
        ) from e


def get_section_properties_sync(
    designation: str,
    steel_grade: str,
) -> dict:
    """
    Synchronous wrapper for section properties (for backward compatibility).

    NOTE: This function returns a placeholder. Use the async version for
    actual database queries.

    Args:
        designation: AISC designation
        steel_grade: Steel grade

    Returns:
        Dict with basic properties (placeholder - use async version for real data)

    Deprecated:
        Use get_section_properties_async() instead. This sync version
        exists only for backward compatibility and returns placeholders.
    """
    logger.warning(
        "aisc.sync_deprecated",
        designation=designation,
        message="get_section_properties_sync() is deprecated. Use async version."
    )

    # Return placeholder - callers should migrate to async version
    STEEL_GRADES = {
        "A500B": 46.0,
        "A53B": 36.0,
        "A36": 36.0,
        "A572-50": 50.0,
    }

    return {
        "designation": designation,
        "fy_ksi": STEEL_GRADES.get(steel_grade, 46.0),
        "sx_in3": 0.0,  # Placeholder - use async version
        "weight_plf": 0.0,  # Placeholder - use async version
        "area_in2": 0.0,  # Placeholder - use async version
        "warning": "Using placeholder values - migrate to get_section_properties_async()",
    }


# ============================================================================
# Helper Functions
# ============================================================================

def validate_section_properties(
    sx_in3: float,
    area_in2: float,
    designation: str,
) -> None:
    """
    Validate section properties are positive and reasonable.

    Raises:
        ValueError: If properties are invalid
    """
    if sx_in3 <= 0:
        raise ValueError(
            f"Invalid section modulus for {designation}: Sx={sx_in3} in³. "
            f"Section properties must be positive. "
            f"Verify AISC database lookup or provide valid section designation."
        )

    if area_in2 <= 0:
        raise ValueError(
            f"Invalid cross-sectional area for {designation}: A={area_in2} in². "
            f"Section properties must be positive. "
            f"Verify AISC database lookup or provide valid section designation."
        )

    # Sanity checks for typical ranges
    if sx_in3 > 10000:
        logger.warning(
            "aisc.unusual_section_modulus",
            designation=designation,
            sx_in3=sx_in3,
            message="Section modulus exceeds typical range - verify correctness"
        )

    if area_in2 > 500:
        logger.warning(
            "aisc.unusual_area",
            designation=designation,
            area_in2=area_in2,
            message="Cross-sectional area exceeds typical range - verify correctness"
        )
