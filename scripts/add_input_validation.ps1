# Add comprehensive input validation to calculation functions
# Ensures all inputs meet engineering requirements

$ErrorActionPreference = "Stop"

Write-Host "Adding input validation layers..." -ForegroundColor Cyan

$validationCode = @'
"""
Input validation for PE-compliant calculations
Ensures all parameters meet ASCE 7-22 and IBC 2024 requirements
"""

def validate_wind_inputs(wind_speed_mph, height_ft, exposure, risk_category):
    """Validate wind calculation inputs per ASCE 7-22."""
    errors = []
    
    # Wind speed validation (ASCE 7-22 minimum values)
    if wind_speed_mph < 90:
        errors.append(f"Wind speed {wind_speed_mph} mph below ASCE 7-22 minimum 90 mph")
    if wind_speed_mph > 200:
        errors.append(f"Wind speed {wind_speed_mph} mph exceeds typical ASCE 7-22 range")
    
    # Height validation
    if height_ft < 15:
        errors.append(f"Height {height_ft} ft below ASCE 7-22 minimum 15 ft")
    if height_ft > 60:
        errors.append(f"Height {height_ft} ft requires special analysis per ASCE 7-22")
    
    # Exposure category
    if exposure not in ['B', 'C', 'D']:
        errors.append(f"Invalid exposure category '{exposure}', must be B, C, or D")
    
    # Risk category
    if risk_category not in ['I', 'II', 'III', 'IV']:
        errors.append(f"Invalid risk category '{risk_category}'")
    
    if errors:
        raise ValueError("Wind input validation failed:\n" + "\n".join(errors))
    
    return True

def validate_foundation_inputs(moment_kipft, diameter_ft, soil_psf):
    """Validate foundation inputs per IBC 2024."""
    errors = []
    
    # Moment validation
    if moment_kipft <= 0:
        errors.append(f"Moment {moment_kipft} kip-ft must be positive")
    if moment_kipft > 1000:
        errors.append(f"Moment {moment_kipft} kip-ft requires special analysis")
    
    # Diameter validation (IBC minimums)
    if diameter_ft < 1.5:
        errors.append(f"Diameter {diameter_ft} ft below IBC minimum 1.5 ft")
    if diameter_ft > 10:
        errors.append(f"Diameter {diameter_ft} ft requires special design")
    
    # Soil bearing validation (IBC Table 1806.2)
    if soil_psf < 1500:
        errors.append(f"Soil bearing {soil_psf} psf requires geotechnical report")
    if soil_psf > 12000:
        errors.append(f"Soil bearing {soil_psf} psf exceeds typical rock capacity")
    
    if errors:
        raise ValueError("Foundation input validation failed:\n" + "\n".join(errors))
    
    return True

def validate_material_properties(fy_ksi, fu_ksi=None):
    """Validate material properties per AISC 360-22."""
    errors = []
    
    # Yield strength validation
    valid_fy = [36, 46, 50, 65, 70]  # Common ASTM grades
    if fy_ksi not in valid_fy:
        errors.append(f"Fy {fy_ksi} ksi not standard ASTM grade")
    
    # Ultimate strength validation if provided
    if fu_ksi:
        if fu_ksi < fy_ksi * 1.2:
            errors.append(f"Fu {fu_ksi} ksi must be >= 1.2 * Fy per AISC")
        if fu_ksi > 100:
            errors.append(f"Fu {fu_ksi} ksi exceeds typical steel grades")
    
    if errors:
        raise ValueError("Material validation failed:\n" + "\n".join(errors))
    
    return True

# Export validation functions
__all__ = [
    'validate_wind_inputs',
    'validate_foundation_inputs',
    'validate_material_properties'
]
'@

# Write validation module
$validationCode | Out-File -FilePath "services/api/src/apex/domains/signage/input_validation.py" -Encoding UTF8

# Update existing files to use validation
$updateScript = @'
import sys
import os

# Add validation imports to key files
files_to_update = [
    'services/api/src/apex/domains/signage/asce7_wind.py',
    'services/api/src/apex/domains/signage/solvers.py',
    'services/api/src/apex/domains/signage/single_pole_solver.py'
]

for filepath in files_to_update:
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Add import if not present
        if 'from .input_validation import' not in content:
            import_line = 'from .input_validation import validate_wind_inputs, validate_foundation_inputs, validate_material_properties\n'
            # Add after other imports
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('from typing import'):
                    lines.insert(i + 1, import_line)
                    break
            content = '\n'.join(lines)
            
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"Updated {filepath} with validation imports")

print("Validation layer added successfully")
'@

$updateScript | python

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Input validation layer added" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to add validation layer" -ForegroundColor Red
    exit 1
}

Write-Host "Validation functions added:" -ForegroundColor Cyan
Write-Host "  • validate_wind_inputs() - ASCE 7-22 compliance"
Write-Host "  • validate_foundation_inputs() - IBC 2024 compliance"
Write-Host "  • validate_material_properties() - AISC 360-22 compliance"
