#!/usr/bin/env python
"""Test complete monument workflow with realistic Eagle Sign example"""

import asyncio
import asyncpg
import json
from typing import Dict, Any

DATABASE_URL = "postgresql://apex:apex@localhost:5432/apex"

async def test_monument_analysis():
    """Test monument analysis workflow directly with database"""
    
    print("=" * 60)
    print("TESTING MONUMENT WORKFLOW")
    print("Eagle Sign Example: 25ft pole, 10x8ft sign, HSS10X10X1/2")
    print("=" * 60)
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Test parameters - typical Eagle Sign project
        config = {
            "project_id": "eagle_monument_test",
            "pole_height_ft": 25.0,
            "pole_section": "HSS10X10X1/2",  # Try to find this section
            "sign_width_ft": 10.0,
            "sign_height_ft": 8.0,
            "basic_wind_speed_mph": 115.0,
            "exposure_category": "C",
            "soil_bearing_capacity_psf": 2000.0
        }
        
        print(f"\n1. VERIFYING POLE SECTION: {config['pole_section']}")
        
        # Check if HSS10X10X1/2 exists in database
        section_check = await conn.fetchrow("""
            SELECT aisc_manual_label, type, w, area, ix, sx, rx, is_astm_a1085
            FROM aisc_shapes_v16
            WHERE UPPER(aisc_manual_label) = UPPER($1)
        """, config['pole_section'])
        
        if not section_check:
            # Try alternative HSS10 sections
            alternatives = await conn.fetch("""
                SELECT aisc_manual_label, w, sx, is_astm_a1085
                FROM aisc_shapes_v16
                WHERE type = 'HSS' 
                  AND nominal_depth = 10
                  AND aisc_manual_label LIKE 'HSS10X10%'
                ORDER BY w
                LIMIT 5
            """)
            
            print(f"[NOT FOUND] {config['pole_section']} not found. Available HSS10X10 alternatives:")
            for alt in alternatives:
                print(f"   {alt['aisc_manual_label']:20s} W={alt['w']:.1f} lb/ft Sx={alt['sx']:.1f} in3 A1085={alt['is_astm_a1085']}")
            
            if alternatives:
                config['pole_section'] = alternatives[0]['aisc_manual_label']
                print(f"\n[OK] Using {config['pole_section']} for testing")
                section_check = await conn.fetchrow("""
                    SELECT aisc_manual_label, type, w, area, ix, sx, rx, is_astm_a1085
                    FROM aisc_shapes_v16
                    WHERE UPPER(aisc_manual_label) = UPPER($1)
                """, config['pole_section'])
            else:
                print("[ERROR] No suitable HSS10 sections found")
                return
        else:
            print(f"[OK] Found section: {section_check['aisc_manual_label']}")
        
        print(f"   Type: {section_check['type']}")
        print(f"   Weight: {section_check['w']:.1f} lb/ft")
        print(f"   Sx: {section_check['sx']:.1f} in3")
        print(f"   A1085: {section_check['is_astm_a1085']}")
        
        print(f"\n2. CALCULATING WIND LOADS (ASCE 7-22)")
        
        # Calculate wind loads
        sign_area = config['sign_width_ft'] * config['sign_height_ft']
        
        # Velocity pressure coefficient for Exposure C at 25ft
        kz = 1.0  # Conservative for 25ft height
        qz = 0.00256 * kz * 1.0 * config['basic_wind_speed_mph']**2
        
        # Design wind pressure
        gf = 0.85  # Gust factor
        cf = 1.2   # Force coefficient for flat signs
        pressure = qz * gf * cf
        
        # Wind force and moment
        wind_force = pressure * sign_area
        sign_centroid_height = 8.0 + config['sign_height_ft'] / 2  # 8ft clearance + half sign height
        wind_moment = wind_force * sign_centroid_height / 1000  # kip-ft
        
        print(f"   Sign area: {sign_area:.0f} sq ft")
        print(f"   Velocity pressure: {qz:.1f} psf")
        print(f"   Design pressure: {pressure:.1f} psf")
        print(f"   Wind force: {wind_force:.0f} lbs")
        print(f"   Wind moment at base: {wind_moment:.1f} kip-ft")
        
        print(f"\n3. ANALYZING POLE STRESSES")
        
        # Bending stress
        moment_kipin = wind_moment * 12
        bending_stress = moment_kipin / section_check['sx']
        
        # Allowable stress (simplified)
        fy = 50  # ksi for HSS
        phi_b = 0.9
        allowable_stress = fy * phi_b
        stress_ratio = bending_stress / allowable_stress
        
        # Deflection (simplified cantilever)
        E = 29000  # ksi
        force_kips = wind_force / 1000
        length_in = config['pole_height_ft'] * 12
        deflection_in = (force_kips * length_in**3) / (3 * E * section_check['ix'])
        deflection_ratio = length_in / deflection_in if deflection_in > 0 else float('inf')
        
        print(f"   Bending stress: {bending_stress:.1f} ksi")
        print(f"   Allowable stress: {allowable_stress:.1f} ksi")
        print(f"   Stress ratio: {stress_ratio:.3f}")
        print(f"   Deflection: {deflection_in:.2f} in (L/{deflection_ratio:.0f})")
        
        pole_adequate = stress_ratio <= 0.9 and deflection_ratio >= 200
        print(f"   Pole adequate: {'YES' if pole_adequate else 'NO'}")
        
        print(f"\n4. FOUNDATION ANALYSIS")
        
        # Dead loads
        pole_weight = section_check['w'] * config['pole_height_ft']
        sign_weight = sign_area * 0.125/12 * 169  # 1/8" aluminum
        total_dead_load = pole_weight + sign_weight + 50  # hardware
        
        # Foundation sizing (simplified)
        min_width = max(3.0, (sign_area ** 0.5) / 3)
        foundation_width = 5.0  # Start with 5x5 foundation
        foundation_depth = 4.0
        
        # Foundation weight
        foundation_volume = foundation_width**2 * foundation_depth
        foundation_weight = foundation_volume * 150  # concrete pcf
        total_weight = total_dead_load + foundation_weight
        
        # Overturning analysis
        resisting_moment = total_weight * foundation_width / 2 / 1000  # kip-ft
        safety_factor = resisting_moment / wind_moment if wind_moment > 0 else float('inf')
        
        # Soil pressure
        net_moment = max(0, wind_moment - resisting_moment)
        avg_pressure = total_weight / (foundation_width**2)
        moment_pressure = net_moment * 1000 * 6 / (foundation_width**3)
        max_soil_pressure = avg_pressure + moment_pressure
        
        print(f"   Dead load: {total_dead_load:.0f} lbs")
        print(f"   Foundation: {foundation_width:.0f}x{foundation_width:.0f}x{foundation_depth:.0f} ft")
        print(f"   Foundation weight: {foundation_weight:.0f} lbs")
        print(f"   Overturning safety factor: {safety_factor:.2f}")
        print(f"   Max soil pressure: {max_soil_pressure:.0f} psf")
        
        foundation_adequate = safety_factor >= 1.5 and max_soil_pressure <= config['soil_bearing_capacity_psf']
        print(f"   Foundation adequate: {'YES' if foundation_adequate else 'NO'}")
        
        print(f"\n5. OVERALL RESULTS")
        
        overall_pass = pole_adequate and foundation_adequate
        print(f"   Overall status: {'PASS' if overall_pass else 'FAIL'}")
        
        if not overall_pass:
            print("\n   Recommendations:")
            if not pole_adequate:
                if stress_ratio > 0.9:
                    print("   - Use larger/stronger pole section (higher Sx)")
                if deflection_ratio < 200:
                    print("   - Use stiffer pole section (higher Ix)")
            
            if not foundation_adequate:
                if safety_factor < 1.5:
                    print("   - Increase foundation size for overturning resistance")
                if max_soil_pressure > config['soil_bearing_capacity_psf']:
                    print("   - Increase foundation size to reduce soil pressure")
        
        print(f"\n6. DESIGN SUMMARY")
        print(f"   Project: Eagle Sign Monument")
        print(f"   Pole: {config['pole_section']} x {config['pole_height_ft']} ft")
        print(f"   Sign: {config['sign_width_ft']} x {config['sign_height_ft']} ft ({sign_area:.0f} sq ft)")
        print(f"   Wind: {config['basic_wind_speed_mph']} mph, Exposure {config['exposure_category']}")
        print(f"   Status: {'APPROVED' if overall_pass else 'REVISIONS REQUIRED'}")
        
        print(f"\n[SUCCESS] Monument workflow test complete!")
        
    except Exception as e:
        print(f"\n[ERROR] Error during monument analysis: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_monument_analysis())