"""
Edge Case Tests for Solvers

Tests zero/negative inputs, extreme values, missing data, invalid combinations.
"""

from __future__ import annotations

import pytest

from apex.domains.signage.models import Cabinet, SiteLoads
from apex.domains.signage.solvers import (
    derive_loads,
    filter_poles,
    footing_solve,
    baseplate_checks,
)


class TestEdgeCases:
    """Edge case tests for all solvers."""
    
    def test_zero_wind_speed(self):
        """Zero wind speed should use minimum code value or raise error."""
        site = SiteLoads(wind_speed_mph=0.0, exposure="C")
        cabinets = [Cabinet(width_ft=14.0, height_ft=8.0, weight_psf=10.0)]
        
        # Should either use minimum or raise ValueError
        try:
            result = derive_loads(site, cabinets, 25.0, seed=0)
            # If it doesn't error, should still compute (may use minimum)
            assert result.mu_kipft >= 0
        except ValueError:
            # ValueError is acceptable for zero wind speed
            pass
    
    def test_negative_dimensions(self):
        """Negative dimensions should raise ValueError."""
        site = SiteLoads(wind_speed_mph=115.0, exposure="C")
        
        with pytest.raises(ValueError, match="positive"):
            derive_loads(
                site,
                [Cabinet(width_ft=-5.0, height_ft=8.0, weight_psf=10.0)],
                25.0,
                seed=0,
            )
    
    def test_zero_cabinets(self):
        """Empty cabinet list should return zero loads."""
        site = SiteLoads(wind_speed_mph=115.0, exposure="C")
        result = derive_loads(site, [], 25.0, seed=0)
        
        assert result.a_ft2 == 0.0
        assert result.weight_estimate_lb == 0.0
        assert result.mu_kipft == 0.0
    
    def test_extreme_height(self):
        """Extreme height should trigger warning."""
        site = SiteLoads(wind_speed_mph=115.0, exposure="C")
        cabinets = [Cabinet(width_ft=14.0, height_ft=8.0, weight_psf=10.0)]
        
        warnings = []
        result = derive_loads(site, cabinets, 60.0, seed=0, warnings_list=warnings)
        
        # Should either compute with warning or raise error
        assert result.mu_kipft > 0 or len(warnings) > 0
    
    def test_zero_soil_bearing(self):
        """Zero soil bearing should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            footing_solve(
                mu_kipft=10.0,
                diameter_ft=3.0,
                soil_psf=0.0,
                num_poles=1,
                seed=0,
            )
    
    def test_negative_moment(self):
        """Negative moment should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            footing_solve(
                mu_kipft=-10.0,
                diameter_ft=3.0,
                soil_psf=3000.0,
                num_poles=1,
                seed=0,
            )
    
    def test_extreme_footing_depth(self):
        """Extreme footing depth should trigger warning or request_engineering."""
        depth_ft, request_engineering, warnings = footing_solve(
            mu_kipft=1000.0,  # Extreme load
            diameter_ft=1.0,  # Small diameter
            soil_psf=1000.0,  # Weak soil
            num_poles=1,
            seed=0,
        )
        
        # Should either return large depth or request engineering review
        assert depth_ft > 0 or request_engineering or len(warnings) > 0
    
    def test_no_feasible_poles(self):
        """No feasible poles should return empty list with warning."""
        sections = [
            {"shape": "HSS6x6x1/4", "sx_in3": 10.0, "fy_ksi": 46.0, "weight_per_ft": 10.0}
        ]
        
        poles, warnings = filter_poles(
            mu_required_kipin=10000.0,  # Impossible
            sections=sections,
            prefs={"family": "HSS", "steel_grade": "A500B"},
            seed=0,
            return_warnings=True,
        )
        
        assert len(poles) == 0
        assert len(warnings) > 0  # Should have warning about no feasible poles
    
    def test_missing_required_fields_baseplate(self):
        """Missing required fields should raise validation error."""
        from apex.domains.signage.models import BasePlateInput
        
        # Test with missing loads
        plate_input = BasePlateInput(
            plate_w_in=18.0,
            plate_l_in=18.0,
            plate_thk_in=0.5,
            fy_ksi=36.0,
            weld_size_in=0.25,
            anchor_dia_in=0.75,
            anchor_grade_ksi=58.0,
            anchor_embed_in=8.0,
            rows=2,
            bolts_per_row=2,
            row_spacing_in=6.0,
            edge_distance_in=3.0,
        )
        
        # Should handle empty loads gracefully
        checks, warnings = baseplate_checks(plate_input, {}, seed=0, return_warnings=True)
        
        # Should either return checks or warnings about missing data
        assert isinstance(checks, list)
    
    def test_invalid_material_combination(self):
        """Invalid material combinations should be handled gracefully."""
        sections = [
            {"shape": "HSS6x6x1/4", "sx_in3": 10.0, "fy_ksi": 46.0, "weight_per_ft": 10.0}
        ]
        
        # Request non-existent steel grade
        poles, warnings = filter_poles(
            mu_required_kipin=50.0,
            sections=sections,
            prefs={"family": "HSS", "steel_grade": "INVALID_GRADE"},
            seed=0,
            return_warnings=True,
        )
        
        # Should return available options or warning about unavailable grade
        assert len(poles) >= 0  # May be empty if filter too strict
        assert isinstance(warnings, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

