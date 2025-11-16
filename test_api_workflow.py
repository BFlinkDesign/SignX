#!/usr/bin/env python
"""Test monument API endpoints workflow"""

import asyncio
import json
import sys
import os

# Add the API source to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'services', 'api', 'src'))

from apex.domains.signage.monument_solver import (
    MonumentSolver, MonumentConfig, SectionProperties,
    ExposureCategory, ImportanceFactor
)

async def test_api_workflow():
    """Test the monument solver API workflow"""
    
    print("=" * 60)
    print("TESTING MONUMENT API WORKFLOW")
    print("Using HSS14X14X5/8 for passing design")
    print("=" * 60)
    
    try:
        # Create test configuration
        config = MonumentConfig(
            project_id="eagle_test_api",
            config_id="monument_api_test_001",
            pole_height_ft=25.0,
            pole_section="HSS14X14X5/8",
            sign_width_ft=10.0,
            sign_height_ft=8.0,
            sign_area_sqft=80.0,
            basic_wind_speed_mph=115.0,
            exposure_category=ExposureCategory.C,
            importance_factor=ImportanceFactor.II,
            soil_bearing_capacity_psf=2000.0
        )
        
        # Create section properties (from database lookup)
        section_props = SectionProperties(
            designation="HSS14X14X5/8",
            type="HSS",
            weight_plf=110.4,
            area_in2=32.6,
            ix_in4=897.0,
            sx_in3=128.0,
            rx_in=5.27,
            fy_ksi=50.0,
            is_a1085=True
        )
        
        print(f"1. CONFIGURATION")
        print(f"   Project: {config.project_id}")
        print(f"   Pole: {config.pole_section} x {config.pole_height_ft} ft")
        print(f"   Sign: {config.sign_width_ft} x {config.sign_height_ft} ft")
        print(f"   Wind: {config.basic_wind_speed_mph} mph, {config.exposure_category.value} exposure")
        
        print(f"\n2. SECTION PROPERTIES")
        print(f"   Designation: {section_props.designation}")
        print(f"   Weight: {section_props.weight_plf:.1f} lb/ft")
        print(f"   Ix: {section_props.ix_in4:.0f} in4")
        print(f"   Sx: {section_props.sx_in3:.1f} in3")
        print(f"   A1085: {section_props.is_a1085}")
        
        print(f"\n3. RUNNING MONUMENT ANALYSIS")
        
        # Initialize solver
        solver = MonumentSolver()
        
        # Perform analysis
        results = solver.analyze_monument_sign(config, section_props)
        
        print(f"   Analysis complete!")
        
        print(f"\n4. WIND ANALYSIS RESULTS")
        print(f"   Design pressure: {results.design_wind_pressure_psf:.1f} psf")
        print(f"   Total wind force: {results.total_wind_force_lbs:.0f} lbs")
        print(f"   Wind moment: {results.wind_moment_at_base_kipft:.1f} kip-ft")
        print(f"   Velocity pressure: {results.velocity_pressure_qz_psf:.1f} psf")
        
        print(f"\n5. STRUCTURAL ANALYSIS RESULTS")
        print(f"   Max bending stress: {results.max_bending_stress_ksi:.1f} ksi")
        print(f"   Stress ratio: {results.combined_stress_ratio:.3f}")
        print(f"   Max deflection: {results.max_deflection_in:.2f} in")
        print(f"   Deflection ratio: L/{results.deflection_ratio:.0f}")
        print(f"   Pole adequate: {results.pole_adequate}")
        
        print(f"\n6. FOUNDATION ANALYSIS RESULTS")
        print(f"   Overturning moment: {results.overturning_moment_kipft:.1f} kip-ft")
        print(f"   Safety factor: {results.overturning_safety_factor:.2f}")
        print(f"   Max soil pressure: {results.max_soil_pressure_psf:.0f} psf")
        print(f"   Foundation size: {results.foundation_width_ft:.1f} x {results.foundation_length_ft:.1f} ft")
        print(f"   Foundation adequate: {results.foundation_adequate}")
        
        print(f"\n7. OVERALL STATUS")
        print(f"   Overall passes: {results.overall_passes}")
        print(f"   Status: {'APPROVED' if results.overall_passes else 'REQUIRES REVISION'}")
        
        if results.warnings:
            print(f"\n   Warnings:")
            for warning in results.warnings:
                print(f"   - {warning}")
        
        if results.design_notes:
            print(f"\n   Design Notes:")
            for note in results.design_notes:
                print(f"   - {note}")
        
        print(f"\n8. ASSUMPTIONS")
        for assumption in results.assumptions[:10]:  # Show first 10
            print(f"   - {assumption}")
        if len(results.assumptions) > 10:
            print(f"   ... and {len(results.assumptions) - 10} more assumptions")
        
        print(f"\n[SUCCESS] API workflow test complete!")
        print(f"Monument design for Eagle Sign: {'APPROVED' if results.overall_passes else 'NEEDS REVISION'}")
        
        # Summary for user
        print(f"\n" + "=" * 60)
        print(f"EAGLE SIGN MONUMENT DESIGN SUMMARY")
        print(f"=" * 60)
        print(f"Project: {config.project_id}")
        print(f"Pole: {section_props.designation} x {config.pole_height_ft}' tall")
        print(f"Sign: {config.sign_width_ft}' x {config.sign_height_ft}' ({config.sign_area_sqft} sq ft)")
        print(f"Wind Load: {config.basic_wind_speed_mph} mph, Exposure {config.exposure_category.value}")
        print(f"")
        print(f"RESULTS:")
        print(f"- Wind Moment: {results.wind_moment_at_base_kipft:.1f} kip-ft")
        print(f"- Pole Stress Ratio: {results.combined_stress_ratio:.2f} ({'OK' if results.combined_stress_ratio <= 0.9 else 'HIGH'})")
        print(f"- Deflection: L/{results.deflection_ratio:.0f} ({'OK' if results.deflection_ratio >= 200 else 'EXCESSIVE'})")
        print(f"- Foundation Safety: {results.overturning_safety_factor:.1f} ({'OK' if results.overturning_safety_factor >= 1.5 else 'LOW'})")
        print(f"")
        print(f"STATUS: {'✓ APPROVED FOR CONSTRUCTION' if results.overall_passes else '✗ REQUIRES DESIGN REVISION'}")
        
    except Exception as e:
        print(f"\n[ERROR] API workflow test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api_workflow())