#!/usr/bin/env python3
"""
Sign Type Analyzer - Categorizes parts and builds labor guide by sign type
Add this to V9 to create your own ABC guide replacement
"""

import re
from collections import defaultdict
import numpy as np

class SignTypeAnalyzer:
    """Categorize parts by sign type based on patterns"""
    
    def __init__(self):
        # Sign type patterns - customize these based on YOUR part numbering
        self.sign_patterns = {
            'CHANNEL_LETTERS': [
                r'CHL?-\d+',          # CHL-24, CH-36
                r'[A-Z]+-\d+"-[A-Z]+', # ABC-24"-RED
                r'LETTER',            # Description contains LETTER
            ],
            'MONUMENT': [
                r'MON-',
                r'MONUMENT',
                r'GROUND',
            ],
            'PYLON': [
                r'PYL-',
                r'PYLON',
                r'POLE\s*SIGN',
            ],
            'CABINET': [
                r'CAB-',
                r'CABINET',
                r'LIGHT\s*BOX',
                r'(?:SINGLE|DOUBLE)\s*FACE',
            ],
            'DIMENSIONAL': [
                r'DIM-',
                r'DIMENSIONAL',
                r'STUD\s*MOUNT',
                r'STAND\s*OFF',
            ],
            'VINYL': [
                r'VIN-',
                r'VINYL',
                r'WINDOW\s*GRAPHIC',
                r'DECAL',
            ],
            'DIRECTIONAL': [
                r'DIR-',
                r'WAYFIND',
                r'DIRECTORY',
                r'DIRECTIONAL',
            ],
            'ELECTRONIC': [
                r'EMC-',
                r'LED\s*DISPLAY',
                r'ELECTRONIC',
                r'DIGITAL',
            ]
        }
        
        # Size detection patterns
        self.size_patterns = {
            'inches': r'(\d+)"',                    # 24"
            'feet': r"(\d+)'",                      # 8'
            'dimensions': r'(\d+)\s*[xX]\s*(\d+)',  # 4x8
            'area_sf': r'(\d+)\s*SF',               # 32SF
        }
    
    def categorize_part(self, part_number, description=''):
        """Determine sign type from part number and description"""
        combined = f"{part_number} {description}".upper()
        
        for sign_type, patterns in self.sign_patterns.items():
            for pattern in patterns:
                if re.search(pattern, combined, re.I):
                    return sign_type
        
        return 'UNCATEGORIZED'
    
    def extract_size(self, part_number, description=''):
        """Extract size information"""
        combined = f"{part_number} {description}"
        size_info = {}
        
        # Look for dimensions
        dim_match = re.search(self.size_patterns['dimensions'], combined)
        if dim_match:
            w, h = int(dim_match.group(1)), int(dim_match.group(2))
            size_info['width'] = w
            size_info['height'] = h
            size_info['area_sf'] = (w * h) / 144  # Convert to sq ft
            
        # Look for single measurements
        inch_match = re.search(self.size_patterns['inches'], combined)
        if inch_match:
            size_info['size_inches'] = int(inch_match.group(1))
            
        # Look for area
        area_match = re.search(self.size_patterns['area_sf'], combined)
        if area_match:
            size_info['area_sf'] = int(area_match.group(1))
            
        return size_info
    
    def build_labor_guide(self, analyzer_results):
        """Build labor guide organized by sign type"""
        guide = defaultdict(lambda: defaultdict(list))
        
        # Process each part
        for part_num, part_data in analyzer_results['parts'].items():
            # Get sign type
            sign_type = self.categorize_part(part_num)
            
            # Get size info
            size_info = self.extract_size(part_num)
            
            # Collect labor hours by code
            for code, estimate in part_data['labor_estimates'].items():
                if estimate.sample_size >= 5:  # Minimum samples
                    guide[sign_type][code].append({
                        'part': part_num,
                        'hours': estimate.recommended_hours,
                        'samples': estimate.sample_size,
                        'size_info': size_info
                    })
        
        return guide
    
    def generate_guide_report(self, guide):
        """Generate formatted labor guide"""
        lines = []
        lines.append("EAGLE SIGN LABOR GUIDE - Built from Your Data")
        lines.append("="*80)
        
        for sign_type in sorted(guide.keys()):
            lines.append(f"\n{sign_type}")
            lines.append("-"*40)
            
            for code in sorted(guide[sign_type].keys()):
                entries = guide[sign_type][code]
                
                # Calculate statistics
                all_hours = [e['hours'] for e in entries]
                avg_hours = np.mean(all_hours)
                min_hours = np.min(all_hours)
                max_hours = np.max(all_hours)
                total_samples = sum(e['samples'] for e in entries)
                
                # Get code description
                desc = {
                    '0260': 'FACES',
                    '0340': 'ELECTRICAL',
                    '0520': 'CUT VINYL',
                    '0550': 'APPLY VINYL',
                    # Add all codes...
                }.get(code, f'Code {code}')
                
                lines.append(f"  {code} {desc:<20} {avg_hours:6.2f} hrs (range: {min_hours:.1f}-{max_hours:.1f}, n={total_samples})")
                
                # Size analysis if available
                sizes = [e['size_info'] for e in entries if e['size_info']]
                if sizes:
                    areas = [s.get('area_sf', 0) for s in sizes if s.get('area_sf')]
                    if areas:
                        avg_area = np.mean(areas)
                        hrs_per_sf = avg_hours / avg_area if avg_area > 0 else 0
                        lines.append(f"       Avg size: {avg_area:.1f} SF | {hrs_per_sf:.3f} hrs/SF")
        
        lines.append("\n" + "="*80)
        lines.append("This guide is based on YOUR actual production data")
        lines.append("Update regularly as you complete more jobs")
        
        return "\n".join(lines)

# Integration with V9
def enhance_v9_with_sign_types(v9_results):
    """Add sign type analysis to V9 results"""
    analyzer = SignTypeAnalyzer()
    
    # Build guide
    guide = analyzer.build_labor_guide(v9_results)
    
    # Generate report
    report = analyzer.generate_guide_report(guide)
    
    # Save to file
    with open("eagle_labor_guide.txt", 'w') as f:
        f.write(report)
    
    print("✅ Labor guide saved: eagle_labor_guide.txt")
    
    return guide

# Example output:
"""
EAGLE SIGN LABOR GUIDE - Built from Your Data
================================================================================

CHANNEL_LETTERS
----------------------------------------
  0260 FACES               12.50 hrs (range: 8.0-18.0, n=150)
       Avg size: 24.0 SF | 0.521 hrs/SF
  0340 ELECTRICAL           8.75 hrs (range: 6.0-12.0, n=145)
  0420 PRIME AND FINISH     6.25 hrs (range: 4.0-9.0, n=120)

MONUMENT
----------------------------------------
  0215 STRUCTURAL STEEL    18.50 hrs (range: 12.0-28.0, n=45)
  0260 FACES               22.00 hrs (range: 16.0-32.0, n=42)
  0280 CRATING            4.50 hrs (range: 3.0-6.0, n=40)

CABINET
----------------------------------------
  0220 EXTRUSIONS          8.00 hrs (range: 6.0-12.0, n=85)
  0260 FACES              16.50 hrs (range: 12.0-24.0, n=82)
  0340 ELECTRICAL         12.25 hrs (range: 8.0-18.0, n=80)
"""