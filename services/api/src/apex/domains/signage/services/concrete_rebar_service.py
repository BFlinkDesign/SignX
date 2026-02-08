"""
Concrete and Rebar Design Service - ACI 318-19 Implementation

Provides rebar detailing, development lengths, and concrete volume calculations
for sign structure foundations with complete material takeoff for cost estimation.

Standards: ACI 318-19, IBC 2024 Section 1905-1907

Author: Claude Code
Date: 2025-11-02
"""

from __future__ import annotations

import math
from enum import Enum

import structlog
from pydantic import BaseModel, Field

from ..exceptions import CalculationError, ValidationError

logger = structlog.get_logger(__name__)


# ============================================================================
# Domain Models
# ============================================================================

class RebarSize(str, Enum):
    """Standard rebar sizes per ASTM A615."""
    NO3 = "#3"    # 0.375" diameter
    NO4 = "#4"    # 0.500" diameter
    NO5 = "#5"    # 0.625" diameter
    NO6 = "#6"    # 0.750" diameter
    NO7 = "#7"    # 0.875" diameter
    NO8 = "#8"    # 1.000" diameter
    NO9 = "#9"    # 1.128" diameter
    NO10 = "#10"  # 1.270" diameter
    NO11 = "#11"  # 1.410" diameter


class ConcreteGrade(str, Enum):
    """Standard concrete compressive strengths."""
    FC_2500 = "2500"  # 2500 psi (residential)
    FC_3000 = "3000"  # 3000 psi (typical)
    FC_4000 = "4000"  # 4000 psi (commercial)
    FC_5000 = "5000"  # 5000 psi (high-strength)


class FoundationType(str, Enum):
    """Foundation types for sign structures."""
    DIRECT_BURIAL = "direct_burial"      # Pole embedded in concrete
    DRILLED_PIER = "drilled_pier"        # Cylindrical pier
    SPREAD_FOOTING = "spread_footing"    # Rectangular footing with base plate


# Rebar properties database (ASTM A615)
REBAR_PROPERTIES = {
    RebarSize.NO3: {"diameter_in": 0.375, "area_in2": 0.11, "weight_plf": 0.376},
    RebarSize.NO4: {"diameter_in": 0.500, "area_in2": 0.20, "weight_plf": 0.668},
    RebarSize.NO5: {"diameter_in": 0.625, "area_in2": 0.31, "weight_plf": 1.043},
    RebarSize.NO6: {"diameter_in": 0.750, "area_in2": 0.44, "weight_plf": 1.502},
    RebarSize.NO7: {"diameter_in": 0.875, "area_in2": 0.60, "weight_plf": 2.044},
    RebarSize.NO8: {"diameter_in": 1.000, "area_in2": 0.79, "weight_plf": 2.670},
    RebarSize.NO9: {"diameter_in": 1.128, "area_in2": 1.00, "weight_plf": 3.400},
    RebarSize.NO10: {"diameter_in": 1.270, "area_in2": 1.27, "weight_plf": 4.303},
    RebarSize.NO11: {"diameter_in": 1.410, "area_in2": 1.56, "weight_plf": 5.313},
}


class RebarScheduleInput(BaseModel):
    """Input for rebar schedule design."""

    foundation_type: FoundationType = Field(
        default=FoundationType.DIRECT_BURIAL,
        description="Type of foundation"
    )

    # Foundation geometry
    diameter_ft: float = Field(gt=0, le=10, description="Foundation diameter (ft)")
    depth_ft: float = Field(gt=0, le=20, description="Foundation depth (ft)")

    # For spread footings
    width_ft: float | None = Field(None, ge=0, description="Footing width (ft)")
    length_ft: float | None = Field(None, ge=0, description="Footing length (ft)")
    thickness_ft: float | None = Field(None, ge=0, description="Footing thickness (ft)")

    # Material properties
    fc_ksi: float = Field(
        default=3.0,
        gt=0,
        le=10,
        description="Concrete compressive strength (ksi)"
    )
    fy_ksi: float = Field(
        default=60.0,
        gt=0,
        le=100,
        description="Rebar yield strength (ksi)"
    )

    # Design preferences
    min_rebar_size: RebarSize = Field(
        default=RebarSize.NO4,
        description="Minimum rebar size"
    )
    cover_in: float = Field(
        default=3.0,
        ge=1.5,
        le=6,
        description="Concrete cover (in)"
    )


class RebarBar(BaseModel):
    """Individual rebar specification."""

    mark: str = Field(description="Bar mark (e.g., 'V1', 'H1')")
    size: RebarSize = Field(description="Bar size")
    quantity: int = Field(gt=0, description="Number of bars")
    length_ft: float = Field(gt=0, description="Length per bar (ft)")
    spacing_in: float | None = Field(None, description="Spacing (in)")
    location: str = Field(description="Location description")

    @property
    def total_length_ft(self) -> float:
        """Total length for all bars of this mark."""
        return self.quantity * self.length_ft

    @property
    def weight_lb(self) -> float:
        """Total weight for all bars of this mark."""
        props = REBAR_PROPERTIES[self.size]
        return self.total_length_ft * props["weight_plf"]


class ConcreteVolume(BaseModel):
    """Concrete volume calculation."""

    volume_cf: float = Field(gt=0, description="Volume (cubic feet)")
    volume_cy: float = Field(gt=0, description="Volume (cubic yards)")
    weight_ton: float = Field(gt=0, description="Weight (tons)")
    waste_factor: float = Field(default=1.10, description="Waste factor")

    @property
    def order_volume_cy(self) -> float:
        """Volume to order including waste."""
        return self.volume_cy * self.waste_factor


class RebarScheduleResult(BaseModel):
    """Complete rebar schedule with material takeoff."""

    # Rebar schedule
    vertical_bars: list[RebarBar] = Field(description="Vertical reinforcement")
    horizontal_bars: list[RebarBar] = Field(description="Horizontal/spiral reinforcement")

    # Concrete
    concrete: ConcreteVolume = Field(description="Concrete quantities")

    # Development lengths
    development_length_in: float = Field(description="Required development length (in)")

    # Material summary
    total_rebar_weight_lb: float = Field(description="Total rebar weight (lb)")
    total_rebar_weight_ton: float = Field(description="Total rebar weight (ton)")

    # Cost estimation inputs
    concrete_cy_to_order: float = Field(description="Concrete to order (CY)")
    rebar_ton_to_order: float = Field(description="Rebar to order (ton)")

    # Code references
    code_references: list[str] = Field(description="ACI 318 references")

    class Config:
        frozen = True


class DevelopmentLengthResult(BaseModel):
    """Development length calculation per ACI 318-19."""

    ld_in: float = Field(description="Required development length (in)")
    db_in: float = Field(description="Bar diameter (in)")
    bar_size: RebarSize = Field(description="Bar size")
    fc_ksi: float = Field(description="Concrete strength (ksi)")
    fy_ksi: float = Field(description="Rebar yield strength (ksi)")
    coating_factor: float = Field(description="Coating factor ψe")
    size_factor: float = Field(description="Size factor ψs")
    code_ref: str = Field(description="ACI 318 section reference")

    class Config:
        frozen = True


# ============================================================================
# Concrete & Rebar Service
# ============================================================================

class ConcreteRebarService:
    """
    ACI 318-19 Concrete and Rebar Design Service.

    Provides deterministic rebar schedules, development lengths, and
    concrete volume calculations for sign structure foundations.

    This service is essential for:
    - Material takeoff and cost estimation
    - Construction drawings and details
    - Code compliance documentation

    Standards:
        ACI 318-19 Building Code Requirements for Structural Concrete
        IBC 2024 Section 1905-1907

    Examples:
        >>> service = ConcreteRebarService(code_version="ACI318-19")
        >>> schedule = service.design_rebar_schedule(
        ...     foundation_type=FoundationType.DIRECT_BURIAL,
        ...     diameter_ft=3.0,
        ...     depth_ft=6.0,
        ...     fc_ksi=3.0,
        ... )
        >>> print(f"Concrete: {schedule.concrete_cy_to_order:.2f} CY")
        Concrete: 2.34 CY
    """

    def __init__(self, code_version: str = "ACI318-19"):
        """
        Initialize concrete/rebar service.

        Args:
            code_version: Code version string for traceability
        """
        self.code_version = code_version
        logger.info("concrete_rebar_service.initialized", code_version=code_version)

    def calculate_development_length(
        self,
        bar_size: RebarSize,
        fc_ksi: float = 3.0,
        fy_ksi: float = 60.0,
        coated: bool = False,
        top_bar: bool = False,
    ) -> DevelopmentLengthResult:
        """
        Calculate tension development length per ACI 318-19 Section 25.4.2.

        Implements: ld = (fy * ψt * ψe * ψs) / (25 * λ * √fc) * db

        Args:
            bar_size: Rebar size
            fc_ksi: Concrete compressive strength (ksi)
            fy_ksi: Rebar yield strength (ksi)
            coated: True if epoxy-coated bars
            top_bar: True if bar is top reinforcement (>12" of fresh concrete below)

        Returns:
            DevelopmentLengthResult with required length and factors

        References:
            - ACI 318-19 Section 25.4.2: Development of Deformed Bars in Tension
            - ACI 318-19 Table 25.4.2.4: Modification Factors
        """
        # Get bar properties
        props = REBAR_PROPERTIES[bar_size]
        db_in = props["diameter_in"]

        # Modification factors per ACI 318-19 Table 25.4.2.4
        psi_t = 1.3 if top_bar else 1.0  # Top bar factor
        psi_e = 1.5 if coated else 1.0   # Coating factor

        # Size factor ψs
        if bar_size in {RebarSize.NO3, RebarSize.NO4, RebarSize.NO5, RebarSize.NO6}:
            psi_s = 0.8  # Smaller bars
        else:
            psi_s = 1.0  # Larger bars

        # Lightweight concrete factor λ (normal weight = 1.0)
        lambda_factor = 1.0

        # ACI 318-19 Equation 25.4.2.3a
        # ld = (fy * ψt * ψe * ψs) / (25 * λ * √fc) * db
        fc_psi = fc_ksi * 1000.0
        fy_psi = fy_ksi * 1000.0

        ld_in = (
            (fy_psi * psi_t * psi_e * psi_s)
            / (25.0 * lambda_factor * math.sqrt(fc_psi))
            * db_in
        )

        # Minimum development length per ACI 318-19 Section 25.4.2.1
        ld_min_in = max(12.0, ld_in)

        logger.info(
            "concrete.development_length_calculated",
            bar_size=bar_size.value,
            ld_in=round(ld_in, 2),
            fc_ksi=fc_ksi,
            fy_ksi=fy_ksi,
        )

        return DevelopmentLengthResult(
            ld_in=ld_min_in,
            db_in=db_in,
            bar_size=bar_size,
            fc_ksi=fc_ksi,
            fy_ksi=fy_ksi,
            coating_factor=psi_e,
            size_factor=psi_s,
            code_ref=f"{self.code_version} Section 25.4.2",
        )

    def calculate_concrete_volume(
        self,
        foundation_type: FoundationType,
        diameter_ft: float | None = None,
        depth_ft: float | None = None,
        width_ft: float | None = None,
        length_ft: float | None = None,
        thickness_ft: float | None = None,
        waste_factor: float = 1.10,
    ) -> ConcreteVolume:
        """
        Calculate concrete volume for foundation.

        Args:
            foundation_type: Type of foundation
            diameter_ft: Diameter for cylindrical foundations (ft)
            depth_ft: Depth for cylindrical foundations (ft)
            width_ft: Width for rectangular footings (ft)
            length_ft: Length for rectangular footings (ft)
            thickness_ft: Thickness for rectangular footings (ft)
            waste_factor: Waste/overorder factor (default 1.10 = 10%)

        Returns:
            ConcreteVolume with quantities in CF, CY, and tons

        Raises:
            ValidationError: If required dimensions missing
        """
        # Calculate volume based on foundation type
        if foundation_type in {FoundationType.DIRECT_BURIAL, FoundationType.DRILLED_PIER}:
            if diameter_ft is None or depth_ft is None:
                raise ValidationError(
                    message="Cylindrical foundation requires diameter_ft and depth_ft",
                    code_ref=f"{self.code_version} Section 13.3",
                )

            # Volume of cylinder: V = π * r² * h
            radius_ft = diameter_ft / 2.0
            volume_cf = math.pi * (radius_ft ** 2) * depth_ft

        elif foundation_type == FoundationType.SPREAD_FOOTING:
            if width_ft is None or length_ft is None or thickness_ft is None:
                raise ValidationError(
                    message="Spread footing requires width_ft, length_ft, and thickness_ft",
                    code_ref=f"{self.code_version} Section 13.2",
                )

            # Volume of rectangular prism: V = l * w * h
            volume_cf = width_ft * length_ft * thickness_ft

        else:
            raise CalculationError(
                message=f"Unknown foundation type: {foundation_type}",
                code_ref=f"{self.code_version}",
            )

        # Convert to cubic yards
        volume_cy = volume_cf / 27.0

        # Weight (concrete density ≈ 150 pcf for normal weight)
        weight_lb = volume_cf * 150.0
        weight_ton = weight_lb / 2000.0

        logger.info(
            "concrete.volume_calculated",
            foundation_type=foundation_type.value,
            volume_cy=round(volume_cy, 2),
            weight_ton=round(weight_ton, 2),
        )

        return ConcreteVolume(
            volume_cf=volume_cf,
            volume_cy=volume_cy,
            weight_ton=weight_ton,
            waste_factor=waste_factor,
        )

    def design_rebar_schedule(
        self,
        input_data: RebarScheduleInput,
    ) -> RebarScheduleResult:
        """
        Design complete rebar schedule for foundation with material takeoff.

        This is the main method for generating construction-ready rebar details
        and material quantities for cost estimation.

        Args:
            input_data: Foundation geometry and material properties

        Returns:
            RebarScheduleResult with complete schedule and quantities

        References:
            - ACI 318-19 Section 13.3: Drilled Piers
            - ACI 318-19 Section 25.4: Development of Reinforcement
        """
        # Calculate development length for typical vertical bar
        dev_length = self.calculate_development_length(
            bar_size=input_data.min_rebar_size,
            fc_ksi=input_data.fc_ksi,
            fy_ksi=input_data.fy_ksi,
        )

        # Design rebar schedule based on foundation type
        if input_data.foundation_type in {FoundationType.DIRECT_BURIAL, FoundationType.DRILLED_PIER}:
            vertical_bars, horizontal_bars = self._design_cylindrical_rebar(
                diameter_ft=input_data.diameter_ft,
                depth_ft=input_data.depth_ft,
                min_size=input_data.min_rebar_size,
                cover_in=input_data.cover_in,
            )

            concrete = self.calculate_concrete_volume(
                foundation_type=input_data.foundation_type,
                diameter_ft=input_data.diameter_ft,
                depth_ft=input_data.depth_ft,
            )

        elif input_data.foundation_type == FoundationType.SPREAD_FOOTING:
            vertical_bars, horizontal_bars = self._design_spread_footing_rebar(
                width_ft=input_data.width_ft,
                length_ft=input_data.length_ft,
                thickness_ft=input_data.thickness_ft,
                min_size=input_data.min_rebar_size,
                cover_in=input_data.cover_in,
            )

            concrete = self.calculate_concrete_volume(
                foundation_type=input_data.foundation_type,
                width_ft=input_data.width_ft,
                length_ft=input_data.length_ft,
                thickness_ft=input_data.thickness_ft,
            )

        else:
            raise ValidationError(
                message=f"Unsupported foundation type: {input_data.foundation_type}",
                code_ref=f"{self.code_version}",
            )

        # Calculate total rebar weight
        total_weight_lb = sum(bar.weight_lb for bar in vertical_bars + horizontal_bars)
        total_weight_ton = total_weight_lb / 2000.0

        # Add 5% waste for rebar
        rebar_ton_to_order = total_weight_ton * 1.05

        code_refs = [
            f"{self.code_version} Section 13.3: Drilled Piers",
            f"{self.code_version} Section 25.4: Development of Reinforcement",
            f"{self.code_version} Section 20.6: Minimum Reinforcement",
            f"{self.code_version} Table 20.6.1.3.1: Minimum Cover",
        ]

        logger.info(
            "rebar_schedule.designed",
            total_rebar_ton=round(total_weight_ton, 3),
            concrete_cy=round(concrete.volume_cy, 2),
            vertical_bars=len(vertical_bars),
            horizontal_bars=len(horizontal_bars),
        )

        return RebarScheduleResult(
            vertical_bars=vertical_bars,
            horizontal_bars=horizontal_bars,
            concrete=concrete,
            development_length_in=dev_length.ld_in,
            total_rebar_weight_lb=total_weight_lb,
            total_rebar_weight_ton=total_weight_ton,
            concrete_cy_to_order=concrete.order_volume_cy,
            rebar_ton_to_order=rebar_ton_to_order,
            code_references=code_refs,
        )

    def _design_cylindrical_rebar(
        self,
        diameter_ft: float,
        depth_ft: float,
        min_size: RebarSize,
        cover_in: float,
    ) -> tuple[list[RebarBar], list[RebarBar]]:
        """
        Design rebar for cylindrical direct burial or drilled pier.

        Per ACI 318-19 Section 13.3, drilled piers require:
        - Minimum 6 vertical bars (or 0.5% of gross area)
        - Spiral or ties for confinement
        """
        # Vertical bars (minimum 6 bars per ACI 318-19 13.3.4.3)
        num_vertical = max(6, int(math.pi * diameter_ft * 12 / 12))  # ~1 bar per foot of circumference

        # Vertical bar length = depth + anchorage
        vertical_length_ft = depth_ft + 2.0  # Add 2 ft for anchorage

        vertical_bars = [
            RebarBar(
                mark="V1",
                size=min_size,
                quantity=num_vertical,
                length_ft=vertical_length_ft,
                spacing_in=None,
                location="Vertical reinforcement, equally spaced around perimeter",
            )
        ]

        # Spiral or ties (use spiral for simplicity)
        # Spacing: 3-6 inches typical
        spiral_spacing_in = 4.0
        num_spirals = int((depth_ft * 12) / spiral_spacing_in)

        # Spiral length = circumference of cage
        cage_diameter_in = (diameter_ft * 12) - (2 * cover_in)
        spiral_length_ft = (math.pi * cage_diameter_in / 12.0) * 1.1  # Add 10% for overlap

        horizontal_bars = [
            RebarBar(
                mark="S1",
                size=RebarSize.NO3,  # Spiral typically smaller
                quantity=num_spirals,
                length_ft=spiral_length_ft,
                spacing_in=spiral_spacing_in,
                location=f"Spiral @ {spiral_spacing_in}\" o.c.",
            )
        ]

        return vertical_bars, horizontal_bars

    def _design_spread_footing_rebar(
        self,
        width_ft: float,
        length_ft: float,
        thickness_ft: float,
        min_size: RebarSize,
        cover_in: float,
    ) -> tuple[list[RebarBar], list[RebarBar]]:
        """
        Design rebar for spread footing.

        Per ACI 318-19 Section 13.2, spread footings require:
        - Bottom reinforcement in both directions
        - Minimum steel ratio 0.0018 for grade 60 rebar
        """
        # Calculate required steel area (minimum 0.0018 * gross area)
        gross_area_in2 = (width_ft * 12) * (thickness_ft * 12)
        as_required_in2 = 0.0018 * gross_area_in2

        # Bar properties
        bar_area_in2 = REBAR_PROPERTIES[min_size]["area_in2"]

        # Number of bars in each direction
        num_bars_width = max(3, int(as_required_in2 / bar_area_in2 / 2))
        num_bars_length = max(3, int(as_required_in2 / bar_area_in2 / 2))

        # Bar lengths (full dimension + development)
        bar_length_width = width_ft + 1.0  # Add 1 ft for hooks
        bar_length_length = length_ft + 1.0

        # Spacing
        spacing_width_in = (length_ft * 12) / (num_bars_width - 1)
        spacing_length_in = (width_ft * 12) / (num_bars_length - 1)

        vertical_bars = []  # No vertical bars in spread footing

        horizontal_bars = [
            RebarBar(
                mark="B1",
                size=min_size,
                quantity=num_bars_width,
                length_ft=bar_length_width,
                spacing_in=spacing_width_in,
                location=f"Bottom mat, parallel to width @ {spacing_width_in:.1f}\" o.c.",
            ),
            RebarBar(
                mark="B2",
                size=min_size,
                quantity=num_bars_length,
                length_ft=bar_length_length,
                spacing_in=spacing_length_in,
                location=f"Bottom mat, parallel to length @ {spacing_length_in:.1f}\" o.c.",
            ),
        ]

        return vertical_bars, horizontal_bars
