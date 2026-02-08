"""Verification script to test if solvers are ready for Agent integration.

This script simulates an Agent calling the solvers with JSON-like inputs.
If this fails, the Solvers are not ready for the AI.
"""

import asyncio
import json
from dataclasses import asdict

from apex.domains.signage.monument_solver import MonumentConfig, MonumentSolver, SectionProperties, ExposureCategory, ImportanceFactor

def test_monument_solver_interface():
    print("--- Testing Monument Solver Interface ---")
    
    # 1. Simulate LLM-generated JSON input
    # The Agent will generate this dictionary based on user prompt "20ft pole, 100mph wind"
    llm_input = {
        "project_id": "test-001",
        "config_id": "cfg-001",
        "pole_height_ft": 20.0,
        "pole_section": "HSS8X8X.500",  # The agent needs to know valid sections!
        "sign_width_ft": 10.0,
        "sign_height_ft": 5.0,
        "sign_area_sqft": 50.0,
        "basic_wind_speed_mph": 115.0,
        "exposure_category": "C",
        "importance_factor": "II"
    }
    
    print(f"Agent Input: {json.dumps(llm_input, indent=2)}")
    
    # 2. Map JSON to Domain Objects (The "Tool Wrapper" logic)
    try:
        config = MonumentConfig(
            project_id=llm_input["project_id"],
            config_id=llm_input["config_id"],
            pole_height_ft=llm_input["pole_height_ft"],
            pole_section=llm_input["pole_section"],
            sign_width_ft=llm_input["sign_width_ft"],
            sign_height_ft=llm_input["sign_height_ft"],
            sign_area_sqft=llm_input["sign_area_sqft"],
            basic_wind_speed_mph=llm_input["basic_wind_speed_mph"],
            exposure_category=ExposureCategory(llm_input["exposure_category"]),
            importance_factor=ImportanceFactor(llm_input["importance_factor"])
        )
        
        # Mock section properties (In real app, we look this up in DB)
        section = SectionProperties(
            designation="HSS8X8X.500",
            type="HSS",
            weight_plf=48.85,
            area_in2=13.5,
            ix_in4=130.0,
            sx_in3=32.5,
            rx_in=3.10,
            fy_ksi=50
        )
        
        # 3. Call the Solver
        solver = MonumentSolver()
        results = solver.analyze_monument_sign(config, section)
        
        # 4. Verify Output is Serializable
        output = asdict(results)
        print(f"Solver Output: {json.dumps(output, default=str, indent=2)}")
        print("✅ Monument Solver is Agent-Ready")
        
    except Exception as e:
        print(f"❌ Solver Failed: {e}")
        raise

if __name__ == "__main__":
    test_monument_solver_interface()
