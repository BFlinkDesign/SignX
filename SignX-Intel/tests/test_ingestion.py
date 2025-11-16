"""Test PDF ingestion."""
import pytest
from signx_intel.ingestion.validators import CostDataValidator


def test_validate_valid_record():
    """Test validation of valid cost record."""
    record = {
        "total_cost": 10000.00,
        "labor_cost": 4000.00,
        "material_cost": 5000.00,
        "drivers": {
            "sign_height_ft": 25,
            "sign_area_sqft": 100
        }
    }
    
    is_valid, errors = CostDataValidator.validate_cost_record(record)
    assert is_valid
    assert len(errors) == 0


def test_validate_missing_total_cost():
    """Test validation fails when total_cost is missing."""
    record = {
        "labor_cost": 4000.00,
        "material_cost": 5000.00
    }
    
    is_valid, errors = CostDataValidator.validate_cost_record(record)
    assert not is_valid
    assert any("total_cost" in err for err in errors)


def test_validate_negative_cost():
    """Test validation fails for negative costs."""
    record = {
        "total_cost": -1000.00
    }
    
    is_valid, errors = CostDataValidator.validate_cost_record(record)
    assert not is_valid
    assert any("positive" in err.lower() for err in errors)


def test_clean_cost_record():
    """Test cleaning of cost record."""
    record = {
        "total_cost": "10000.50",
        "labor_cost": None,
        "drivers": {
            "sign_height_ft": 25,
            "removed_field": None
        }
    }
    
    cleaned = CostDataValidator.clean_cost_record(record)
    assert cleaned["total_cost"] == 10000.50
    assert cleaned["labor_cost"] is None
    assert "removed_field" not in cleaned["drivers"]

