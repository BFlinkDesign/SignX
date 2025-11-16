"""Tests for PDF extraction pipeline."""

from __future__ import annotations

from pathlib import Path
from datetime import date

import pytest

from ..pdf_extractor import PDFExtractor
from ..data_schema import ProjectCostRecord, ExposureCategory, PoleType, FoundationType


@pytest.fixture
def sample_pdf_text():
    """Sample PDF text for testing extraction."""
    return """
    EAGLE SIGN COMPANY - PROJECT COST SUMMARY
    
    Project #: ES-2024-1234
    Project Name: Main Street Monument Sign
    Customer: Acme Corporation
    Job #: J-5678
    Quote Date: 10/15/2024
    
    DESIGN SPECIFICATIONS
    Total Height: 20 ft
    Sign Area: 60 sq.ft
    Sign Width: 10 ft
    Sign Height: 6 ft
    
    WIND LOADS
    Wind Speed: 115 mph
    Exposure Category: C
    Importance Factor: 1.0
    
    STRUCTURAL DESIGN
    Pole Type: Round HSS
    Pole Size: 8 inches
    Steel Grade: A500B
    Foundation: Direct Burial
    Embedment Depth: 8 ft
    Concrete: 10 CY
    
    COST BREAKDOWN
    Material Cost: $5,250.00
    Labor Cost: $3,800.00
    Engineering Cost: $450.00
    Permit Fees: $125.00
    
    TOTAL COST: $9,625.00
    """


def test_extract_field_regex(sample_pdf_text):
    """Test regex field extraction."""
    extractor = PDFExtractor(Path("dummy.pdf"))
    extractor.raw_text = sample_pdf_text
    
    project_id = extractor._extract_field_regex(r"Project\s*[#:]?\s*([A-Z0-9-]+)", sample_pdf_text)
    assert project_id == "ES-2024-1234"
    
    height = extractor._extract_field_regex(r"Total\s+Height\s*[:]?\s*([\d.]+)", sample_pdf_text)
    assert height == "20"


def test_extract_currency(sample_pdf_text):
    """Test currency extraction."""
    extractor = PDFExtractor(Path("dummy.pdf"))
    extractor.raw_text = sample_pdf_text
    
    material_cost = extractor._extract_currency(r"Material\s*Cost\s*[:]?\s*\$?([\d,]+\.?\d*)", sample_pdf_text)
    assert material_cost == 5250.0
    
    total_cost = extractor._extract_currency(r"TOTAL\s*COST\s*[:]?\s*\$?([\d,]+\.?\d*)", sample_pdf_text)
    assert total_cost == 9625.0


def test_normalize_pole_type():
    """Test pole type normalization."""
    extractor = PDFExtractor(Path("dummy.pdf"))
    
    assert extractor._normalize_pole_type("Round HSS") == PoleType.ROUND_HSS
    assert extractor._normalize_pole_type("SQUARE HSS") == PoleType.SQUARE_HSS
    assert extractor._normalize_pole_type("PIPE") == PoleType.PIPE
    assert extractor._normalize_pole_type(None) == PoleType.ROUND_HSS  # Default


def test_normalize_foundation_type():
    """Test foundation type normalization."""
    extractor = PDFExtractor(Path("dummy.pdf"))
    
    assert extractor._normalize_foundation_type("Direct Burial") == FoundationType.DIRECT_BURIAL
    assert extractor._normalize_foundation_type("Base Plate") == FoundationType.BASE_PLATE
    assert extractor._normalize_foundation_type("Drilled Pier") == FoundationType.DRILLED_PIER
    assert extractor._normalize_foundation_type(None) == FoundationType.DIRECT_BURIAL


def test_project_cost_record_validation():
    """Test ProjectCostRecord schema validation."""
    # Valid record
    valid_record = ProjectCostRecord(
        project_id="TEST-001",
        height_ft=20.0,
        sign_area_sqft=60.0,
        wind_speed_mph=115.0,
        exposure_category=ExposureCategory.C,
        pole_type=PoleType.ROUND_HSS,
        pole_size=8.0,
        pole_height_ft=20.0,
        foundation_type=FoundationType.DIRECT_BURIAL,
        total_cost=9625.0,
    )
    
    assert valid_record.project_id == "TEST-001"
    assert valid_record.total_cost == 9625.0
    
    # Invalid record (negative height)
    with pytest.raises(ValueError):
        ProjectCostRecord(
            project_id="TEST-002",
            height_ft=-5.0,  # Invalid
            sign_area_sqft=60.0,
            wind_speed_mph=115.0,
            exposure_category=ExposureCategory.C,
            pole_type=PoleType.ROUND_HSS,
            pole_size=8.0,
            pole_height_ft=20.0,
            foundation_type=FoundationType.DIRECT_BURIAL,
            total_cost=9625.0,
        )


def test_cost_record_to_features():
    """Test conversion to features dictionary."""
    record = ProjectCostRecord(
        project_id="TEST-003",
        height_ft=25.0,
        sign_area_sqft=80.0,
        wind_speed_mph=120.0,
        exposure_category=ExposureCategory.C,
        pole_type=PoleType.SQUARE_HSS,
        pole_size=10.0,
        pole_height_ft=25.0,
        foundation_type=FoundationType.BASE_PLATE,
        total_cost=12500.0,
    )
    
    features = record.to_features_dict()
    
    assert features["height_ft"] == 25.0
    assert features["sign_area_sqft"] == 80.0
    assert features["exposure_code"] == 1  # C → 1
    assert features["pole_type_code"] == 1  # Square HSS → 1
    assert features["foundation_type_code"] == 1  # Base plate → 1
    assert features["total_cost"] == 12500.0

