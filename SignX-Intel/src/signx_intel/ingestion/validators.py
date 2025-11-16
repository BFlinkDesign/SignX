"""Data validation for extracted cost records."""
from typing import Dict, Any, List
from decimal import Decimal


class CostDataValidator:
    """Validate extracted cost data before storing."""
    
    @staticmethod
    def validate_cost_record(record: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate a cost record.
        
        Args:
            record: Cost record dictionary
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        if not record.get("total_cost"):
            errors.append("Missing total_cost")
        else:
            # Validate total_cost is positive
            try:
                total = float(record["total_cost"])
                if total <= 0:
                    errors.append("total_cost must be positive")
            except (ValueError, TypeError):
                errors.append("total_cost must be a valid number")
        
        # Validate cost breakdown sums to total (if provided)
        if all(key in record for key in ["labor_cost", "material_cost", "total_cost"]):
            try:
                total = float(record["total_cost"] or 0)
                labor = float(record["labor_cost"] or 0)
                material = float(record["material_cost"] or 0)
                equipment = float(record.get("equipment_cost", 0) or 0)
                overhead = float(record.get("overhead_cost", 0) or 0)
                
                breakdown_sum = labor + material + equipment + overhead
                
                # Allow 5% tolerance for rounding
                if breakdown_sum > 0 and abs(breakdown_sum - total) / total > 0.05:
                    errors.append(
                        f"Cost breakdown ({breakdown_sum}) doesn't match total ({total})"
                    )
            except (ValueError, TypeError) as e:
                errors.append(f"Invalid cost values: {e}")
        
        # Validate drivers (if any)
        drivers = record.get("drivers", {})
        if drivers:
            # Check numeric drivers are positive
            numeric_drivers = ["sign_height_ft", "sign_area_sqft", "wind_speed_mph"]
            for driver in numeric_drivers:
                if driver in drivers:
                    try:
                        value = float(drivers[driver])
                        if value <= 0:
                            errors.append(f"{driver} must be positive")
                    except (ValueError, TypeError):
                        errors.append(f"{driver} must be a valid number")
        
        return (len(errors) == 0, errors)
    
    @staticmethod
    def clean_cost_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and normalize a cost record.
        
        Args:
            record: Raw cost record
        
        Returns:
            Cleaned cost record
        """
        cleaned = record.copy()
        
        # Convert cost fields to Decimal
        cost_fields = [
            "total_cost", "labor_cost", "material_cost",
            "equipment_cost", "overhead_cost", "tax", "shipping"
        ]
        for field in cost_fields:
            if field in cleaned and cleaned[field] is not None:
                try:
                    cleaned[field] = float(cleaned[field])
                except (ValueError, TypeError):
                    cleaned[field] = None
        
        # Ensure drivers is a dict
        if "drivers" not in cleaned:
            cleaned["drivers"] = {}
        
        # Remove None values from drivers
        cleaned["drivers"] = {
            k: v for k, v in cleaned["drivers"].items()
            if v is not None
        }
        
        return cleaned

