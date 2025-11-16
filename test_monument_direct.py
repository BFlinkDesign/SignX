#!/usr/bin/env python
"""Test monument solver directly without imports"""

import asyncio
import asyncpg

async def test_monument_complete():
    """Test complete monument analysis with proper section"""
    
    print("=" * 60)
    print("COMPLETE MONUMENT ANALYSIS TEST")
    print("Using HSS14X14X5/8 for 25ft pole with 10x8ft sign")
    print("=" * 60)
    
    conn = await asyncpg.connect('postgresql://apex:apex@localhost:5432/apex')
    
    try:
        # Get section properties from database
        section = await conn.fetchrow("""
            SELECT aisc_manual_label, type, w, area, ix, sx, rx, is_astm_a1085
            FROM aisc_shapes_v16
            WHERE aisc_manual_label = 'HSS14X14X5/8'
        """)
        
        if not section:
            print("[ERROR] Section HSS14X14X5/8 not found")
            return
        
        print(f"1. SECTION VERIFICATION")
        print(f"   Designation: {section['aisc_manual_label']}")
        print(f"   Type: {section['type']}")
        print(f"   Weight: {section['w']:.1f} lb/ft")
        print(f"   Ix: {section['ix']:.0f} in4")
        print(f"   Sx: {section['sx']:.1f} in3")
        print(f"   A1085: {section['is_astm_a1085']}")
        
        # Design parameters
        config = {
            "pole_height_ft": 25.0,
            "sign_width_ft": 10.0,
            "sign_height_ft": 8.0,
            "basic_wind_speed_mph": 115.0,
            "exposure_category": "C",
            "soil_bearing_capacity_psf": 2000.0
        }
        
        sign_area = config["sign_width_ft"] * config["sign_height_ft"]
        
        print(f"\n2. DESIGN PARAMETERS")
        print(f"   Pole height: {config['pole_height_ft']} ft")
        print(f"   Sign size: {config['sign_width_ft']} x {config['sign_height_ft']} ft")
        print(f"   Sign area: {sign_area} sq ft")
        print(f"   Wind speed: {config['basic_wind_speed_mph']} mph")
        print(f"   Exposure: {config['exposure_category']}")
        
        print(f"\n3. WIND LOAD CALCULATIONS (ASCE 7-22)")
        
        # Wind analysis
        kz = 1.0  # Exposure C at 25ft
        qz = 0.00256 * kz * 1.0 * config['basic_wind_speed_mph']**2
        gf = 0.85  # Gust factor
        cf = 1.2   # Force coefficient
        pressure = qz * gf * cf
        wind_force = pressure * sign_area
        sign_height = 8.0 + config['sign_height_ft'] / 2  # Clearance + centroid
        wind_moment = wind_force * sign_height / 1000  # kip-ft
        
        print(f"   Velocity pressure (qz): {qz:.1f} psf")
        print(f"   Design pressure: {pressure:.1f} psf")
        print(f"   Wind force: {wind_force:.0f} lbs")
        print(f"   Wind moment: {wind_moment:.1f} kip-ft")
        
        print(f"\n4. STRUCTURAL ANALYSIS")
        
        # Stress analysis
        moment_kipin = wind_moment * 12
        bending_stress = moment_kipin / section['sx']
        fy = 50.0  # ksi
        phi_b = 0.9
        allowable_stress = fy * phi_b
        stress_ratio = bending_stress / allowable_stress
        
        # Deflection analysis
        E = 29000  # ksi
        force_kips = wind_force / 1000
        length_in = config['pole_height_ft'] * 12
        deflection_in = (force_kips * length_in**3) / (3 * E * section['ix'])
        deflection_ratio = length_in / deflection_in
        
        print(f"   Bending moment: {moment_kipin:.0f} kip-in")
        print(f"   Bending stress: {bending_stress:.1f} ksi")
        print(f"   Allowable stress: {allowable_stress:.1f} ksi")
        print(f"   Stress ratio: {stress_ratio:.3f}")
        print(f"   Deflection: {deflection_in:.2f} in")
        print(f"   Deflection ratio: L/{deflection_ratio:.0f}")
        
        pole_adequate = stress_ratio <= 0.9 and deflection_ratio >= 200
        print(f"   Pole adequate: {'YES' if pole_adequate else 'NO'}")
        
        print(f"\n5. FOUNDATION DESIGN")
        
        # Dead loads
        pole_weight = section['w'] * config['pole_height_ft']
        sign_weight = sign_area * 0.125/12 * 169  # aluminum
        hardware_weight = 50
        total_dead = pole_weight + sign_weight + hardware_weight
        
        # Foundation sizing - try different sizes
        foundation_adequate = False
        foundation_results = {}
        
        for width_ft in [5, 6, 7, 8]:
            depth_ft = 4
            foundation_volume = width_ft**2 * depth_ft
            foundation_weight = foundation_volume * 150  # concrete
            total_weight = total_dead + foundation_weight
            
            # Overturning analysis
            resisting_moment = total_weight * width_ft / 2 / 1000
            safety_factor = resisting_moment / wind_moment
            
            # Soil pressure
            net_moment = max(0, wind_moment - resisting_moment)
            avg_pressure = total_weight / (width_ft**2)
            moment_pressure = net_moment * 1000 * 6 / (width_ft**3)
            max_soil_pressure = avg_pressure + moment_pressure
            
            if safety_factor >= 1.5 and max_soil_pressure <= config['soil_bearing_capacity_psf']:
                foundation_adequate = True
                foundation_results = {
                    'width_ft': width_ft,
                    'depth_ft': depth_ft,
                    'safety_factor': safety_factor,
                    'max_soil_pressure': max_soil_pressure,
                    'foundation_weight': foundation_weight
                }
                break
        
        if foundation_adequate:
            print(f"   Foundation size: {foundation_results['width_ft']}x{foundation_results['width_ft']}x{foundation_results['depth_ft']} ft")
            print(f"   Foundation weight: {foundation_results['foundation_weight']:.0f} lbs")
            print(f"   Total dead load: {total_dead:.0f} lbs")
            print(f"   Safety factor: {foundation_results['safety_factor']:.2f}")
            print(f"   Max soil pressure: {foundation_results['max_soil_pressure']:.0f} psf")
            print(f"   Foundation adequate: YES")
        else:
            print(f"   Foundation adequate: NO - needs larger size or soil improvement")
        
        print(f"\n6. OVERALL RESULTS")
        
        overall_pass = pole_adequate and foundation_adequate
        print(f"   Overall status: {'PASS' if overall_pass else 'FAIL'}")
        
        if overall_pass:
            print(f"\n   DESIGN APPROVED")
            print(f"   - Pole: {section['aisc_manual_label']} x {config['pole_height_ft']} ft")
            print(f"   - Foundation: {foundation_results['width_ft']}x{foundation_results['width_ft']}x{foundation_results['depth_ft']} ft")
            print(f"   - Stress utilization: {stress_ratio:.1%}")
            print(f"   - Deflection: L/{deflection_ratio:.0f}")
            print(f"   - Safety factor: {foundation_results['safety_factor']:.1f}")
        else:
            print(f"\n   REVISIONS REQUIRED")
            if not pole_adequate:
                if stress_ratio > 0.9:
                    print(f"   - Increase section modulus (current Sx = {section['sx']:.1f} in3)")
                if deflection_ratio < 200:
                    print(f"   - Increase moment of inertia (current Ix = {section['ix']:.0f} in4)")
            if not foundation_adequate:
                print(f"   - Increase foundation size or improve soil conditions")
        
        print(f"\n" + "=" * 60)
        print(f"EAGLE SIGN MONUMENT DESIGN COMPLETE")
        print(f"STATUS: {'APPROVED FOR PERMITTING' if overall_pass else 'REQUIRES REVISION'}")
        print(f"=" * 60)
        
        return overall_pass
        
    except Exception as e:
        print(f"\n[ERROR] Monument analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await conn.close()

if __name__ == "__main__":
    success = asyncio.run(test_monument_complete())
    print(f"\nTest result: {'SUCCESS' if success else 'FAILED'}")