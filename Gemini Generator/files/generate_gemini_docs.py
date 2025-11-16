"""
Gemini File Search - Eagle Sign Project Document Generator
Automatically scans G:\ drive, identifies best projects, and generates comprehensive summaries

Author: Brady Flink / Claude
Date: May 2025
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import re
from collections import defaultdict

# Configuration
PROJECT_ROOT = Path("G:\\")  # G:\ = \\ES-FS02\customers2\
OUTPUT_DIR = Path.home() / "Desktop" / "Gemini_Project_Summaries"
WORK_ORDER_FILE = PROJECT_ROOT / "2024 Work order tracking.xlsx"

# Target: 10 diverse projects across types and price ranges
TARGET_COUNTS = {
    'channel_letters': 2,   # $5K-30K range
    'monument': 2,          # $15K-75K range
    'pole': 2,              # $50K-150K range
    'cabinet': 2,           # $10K-60K range
    'pylon': 1,             # $75K-250K range
    'complex': 1            # $40K-120K range
}


def classify_sign_type(description: str) -> str:
    """Classify sign type from work order description"""
    if not description:
        return 'unknown'
    
    desc = str(description).lower()
    
    if any(word in desc for word in ['channel', 'letter', 'reverse', 'halo']):
        return 'channel_letters'
    elif any(word in desc for word in ['monument', 'ground', 'entry']):
        return 'monument'
    elif any(word in desc for word in ['pole', 'tall', 'freestanding']):
        return 'pole'
    elif any(word in desc for word in ['cabinet', 'box', 'lightbox', 'can']):
        return 'cabinet'
    elif any(word in desc for word in ['pylon', 'tower']):
        return 'pylon'
    else:
        return 'complex'


def find_project_folder(project_number: str, root: Path) -> Path:
    """Find project folder matching the work order number"""
    if not project_number:
        return None
    
    # Clean the project number
    clean_num = str(project_number).strip()
    
    # Search alphabetically organized folders
    for letter_dir in root.iterdir():
        if not letter_dir.is_dir() or len(letter_dir.name) != 1:
            continue
        
        try:
            # Look in each customer folder
            for folder in letter_dir.iterdir():
                if not folder.is_dir():
                    continue
                
                # Check if folder name contains the project number
                if clean_num in folder.name:
                    # Verify it has project files
                    files = list(folder.glob('*'))
                    if len(files) >= 3:  # At least 3 files
                        return folder
        except (PermissionError, OSError):
            continue
    
    return None


def scan_project_folder(folder: Path) -> Dict:
    """Scan a project folder and inventory files"""
    inventory = {
        'pdfs': [],
        'drawings': [],
        'images': [],
        'documents': [],
        'cdr_files': []
    }
    
    flags = {
        'has_shop_drawings': False,
        'has_photos': False,
        'has_cost_docs': False,
        'has_permits': False
    }
    
    try:
        for file in folder.iterdir():
            if not file.is_file():
                continue
            
            ext = file.suffix.lower()
            name = file.stem.lower()
            
            if ext == '.pdf':
                inventory['pdfs'].append(file.name)
                if any(term in name for term in ['shop', 'drawing', 'detail']):
                    flags['has_shop_drawings'] = True
                if any(term in name for term in ['cost', 'quote', 'estimate', 'invoice']):
                    flags['has_cost_docs'] = True
                if any(term in name for term in ['permit', 'approval']):
                    flags['has_permits'] = True
                    
            elif ext in ['.dwg', '.dxf']:
                inventory['drawings'].append(file.name)
                flags['has_shop_drawings'] = True
                
            elif ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                inventory['images'].append(file.name)
                flags['has_photos'] = True
                
            elif ext in ['.docx', '.doc', '.xlsx', '.xls']:
                inventory['documents'].append(file.name)
                
            elif ext == '.cdr':
                inventory['cdr_files'].append(file.name)
    
    except (PermissionError, OSError) as e:
        print(f"    Warning: Could not fully scan {folder.name}: {e}")
    
    return {**inventory, **flags}


def generate_project_html(project: Dict, folder_info: Dict) -> str:
    """Generate comprehensive HTML summary for a project"""
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Eagle Sign Project: {project.get('Customer', 'Unknown')} - WO #{project.get('WO #', 'N/A')}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 30px;
            background: #f5f7fa;
            color: #2c3e50;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 28px;
        }}
        .header .subtitle {{
            opacity: 0.9;
            font-size: 16px;
        }}
        .section {{
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #667eea;
            margin-top: 0;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 200px 1fr;
            gap: 15px;
            margin: 15px 0;
        }}
        .info-label {{
            font-weight: 600;
            color: #666;
        }}
        .info-value {{
            color: #2c3e50;
        }}
        .value-highlight {{
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }}
        .file-list {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }}
        .file-list ul {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .file-list li {{
            padding: 5px 0;
            border-bottom: 1px solid #e0e0e0;
        }}
        .file-list li:last-child {{
            border-bottom: none;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 8px;
        }}
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        .badge-info {{
            background: #d1ecf1;
            color: #0c5460;
        }}
        .metadata {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
            font-size: 13px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Project: {project.get('Customer', 'Unknown Customer')}</h1>
        <div class="subtitle">Work Order #{project.get('WO #', 'N/A')} • {classify_sign_type(project.get('Description', '')).replace('_', ' ').title()}</div>
    </div>
    
    <div class="section">
        <h2>Executive Summary</h2>
        <div class="info-grid">
            <div class="info-label">Project Type:</div>
            <div class="info-value">{classify_sign_type(project.get('Description', '')).replace('_', ' ').title()}</div>
            
            <div class="info-label">Total Value:</div>
            <div class="info-value value-highlight">${project.get('Total', 0):,.2f}</div>
            
            <div class="info-label">Completion Date:</div>
            <div class="info-value">{project.get('Completion Date', 'N/A')}</div>
            
            <div class="info-label">Location:</div>
            <div class="info-value">{folder_info.get('folder_path', 'N/A')}</div>
        </div>
    </div>
    
    <div class="section">
        <h2>Project Description</h2>
        <p>{project.get('Description', 'No description available')}</p>
    </div>
    
    <div class="section">
        <h2>Available Documentation</h2>
        
        <div style="margin-bottom: 15px;">
            {f'<span class="badge badge-success">✓ Shop Drawings</span>' if folder_info.get('has_shop_drawings') else ''}
            {f'<span class="badge badge-success">✓ Project Photos</span>' if folder_info.get('has_photos') else ''}
            {f'<span class="badge badge-success">✓ Cost Documentation</span>' if folder_info.get('has_cost_docs') else ''}
            {f'<span class="badge badge-info">✓ Permit Packages</span>' if folder_info.get('has_permits') else ''}
        </div>
"""
    
    # Add file listings
    if folder_info.get('pdfs'):
        html += f"""
        <div class="file-list">
            <strong>PDF Documents ({len(folder_info['pdfs'])} files):</strong>
            <ul>
                {''.join(f'<li>{name}</li>' for name in folder_info['pdfs'][:15])}
                {f'<li><em>...and {len(folder_info["pdfs"]) - 15} more</em></li>' if len(folder_info['pdfs']) > 15 else ''}
            </ul>
        </div>
"""
    
    if folder_info.get('drawings'):
        html += f"""
        <div class="file-list">
            <strong>Technical Drawings ({len(folder_info['drawings'])} files):</strong>
            <ul>
                {''.join(f'<li>{name}</li>' for name in folder_info['drawings'][:15])}
            </ul>
        </div>
"""
    
    if folder_info.get('images'):
        html += f"""
        <div class="file-list">
            <strong>Project Photos ({len(folder_info['images'])} files):</strong>
            <ul>
                {''.join(f'<li>{name}</li>' for name in folder_info['images'][:15])}
                {f'<li><em>...and {len(folder_info["images"]) - 15} more</em></li>' if len(folder_info['images']) > 15 else ''}
            </ul>
        </div>
"""
    
    html += """
    </div>
    
    <div class="metadata">
        <strong>Metadata for RAG Retrieval:</strong><br>
        <strong>Keywords:</strong> """
    
    # Build keyword list
    keywords = [
        project.get('Customer', ''),
        classify_sign_type(project.get('Description', '')).replace('_', ' '),
        f"${project.get('Total', 0):,.0f}",
        str(project.get('Completion Date', ''))
    ]
    html += ', '.join(k for k in keywords if k)
    
    html += f"""<br>
        <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        <strong>Source:</strong> Eagle Sign Co. Work Order Tracking System
    </div>
</body>
</html>
"""
    
    return html


def main():
    """Main execution"""
    print("\n" + "="*70)
    print("EAGLE SIGN - GEMINI FILE SEARCH DOCUMENT GENERATOR")
    print("="*70 + "\n")
    
    # Step 1: Load work order data
    print("Step 1: Loading work order tracking data...")
    try:
        df = pd.read_excel(WORK_ORDER_FILE)
        print(f"✓ Loaded {len(df)} work orders from 2024\n")
    except Exception as e:
        print(f"✗ Error loading work orders: {e}")
        print("  Make sure G:\\2024 Work order tracking.xlsx exists")
        sys.exit(1)
    
    # Step 2: Classify and filter projects
    print("Step 2: Classifying projects by type...")
    df['Sign_Type'] = df['Description'].apply(classify_sign_type)
    df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0)
    
    type_counts = df['Sign_Type'].value_counts()
    print(f"✓ Classification complete:")
    for sign_type, count in type_counts.items():
        print(f"  {sign_type.replace('_', ' ').title()}: {count}")
    print()
    
    # Step 3: Select diverse projects
    print("Step 3: Selecting 10 diverse projects...")
    selected = []
    type_selected = defaultdict(int)
    
    for sign_type, target_count in TARGET_COUNTS.items():
        # Filter by type and sort by value
        candidates = df[df['Sign_Type'] == sign_type].sort_values('Total', ascending=False)
        
        # Select up to target_count projects
        for _, project in candidates.head(target_count).iterrows():
            selected.append(project)
            type_selected[sign_type] += 1
            if len(selected) >= 10:
                break
        
        if len(selected) >= 10:
            break
    
    print(f"✓ Selected {len(selected)} projects:\n")
    for i, proj in enumerate(selected, 1):
        print(f"  {i}. {proj['Customer'][:40]:40} ${proj['Total']:>10,.0f}  {proj['Sign_Type'].replace('_', ' ')}")
    print()
    
    # Step 4: Generate HTML documents
    print("Step 4: Generating comprehensive HTML summaries...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    generated = []
    for i, project in enumerate(selected, 1):
        print(f"\n[{i}/{len(selected)}] Processing: {project['Customer']}")
        
        # Find project folder
        project_folder = find_project_folder(project['WO #'], PROJECT_ROOT)
        
        if project_folder:
            print(f"  ✓ Found folder: {project_folder}")
            folder_info = scan_project_folder(project_folder)
            folder_info['folder_path'] = str(project_folder)
        else:
            print(f"  ⚠ No folder found - using work order data only")
            folder_info = {
                'pdfs': [],
                'drawings': [],
                'images': [],
                'documents': [],
                'cdr_files': [],
                'has_shop_drawings': False,
                'has_photos': False,
                'has_cost_docs': False,
                'has_permits': False,
                'folder_path': 'Not found'
            }
        
        # Generate HTML
        html_content = generate_project_html(project.to_dict(), folder_info)
        
        # Create safe filename
        safe_name = re.sub(r'[^\w\s-]', '', project['Customer'])
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        wo_num = str(project['WO #']).replace('.', '_')
        filename = f"WO{wo_num}_{safe_name}_{project['Sign_Type']}.html"
        
        # Save
        output_path = OUTPUT_DIR / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        generated.append(output_path)
        print(f"  ✓ Saved: {filename}")
    
    # Step 5: Summary
    print("\n" + "="*70)
    print("GENERATION COMPLETE!")
    print("="*70)
    print(f"\n✓ Generated {len(generated)} HTML documents")
    print(f"✓ Output directory: {OUTPUT_DIR}")
    
    print(f"\n📋 NEXT STEPS:")
    print(f"  1. Review the generated HTML files")
    print(f"  2. Visit https://aistudio.google.com")
    print(f"  3. Sign in with your Google account")
    print(f"  4. Click 'Create new corpus'")
    print(f"  5. Name it 'eagle_sign_projects'")
    print(f"  6. Upload all {len(generated)} HTML files")
    print(f"  7. Test with queries like:")
    print(f"     - 'Find monument sign projects in Iowa'")
    print(f"     - 'What installation challenges for pole signs?'")
    print(f"     - 'LED specifications for cabinet signs'")
    
    print(f"\n💡 TIP: HTML files work great with Gemini's multimodal RAG!")
    print(f"   They're readable by both humans and AI, with semantic structure.")
    
    input(f"\n\nPress Enter to exit...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)
