"""
Gemini File Search - Eagle Sign Documentation Corpus Generator

Scans BOT TRAINING directory and creates structured knowledge base

Author: Brady Flink / Claude  
Date: November 2025
Version: 2.0 - Document-Centric Approach
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import re
from collections import defaultdict

# Configuration
DOC_ROOT = Path(r"C:\Scripts\SignX\Eagle Data\BOT TRAINING")
OUTPUT_DIR = Path.home() / "Desktop" / "Gemini_Eagle_Knowledge_Base"

# Target categories from your BOT TRAINING structure
CATEGORIES = {
    'cat_scale': {
        'path': 'Cat Scale',
        'description': 'Cat Scale pricing, parts, cost analyses, engineering specs',
        'priority': 1  # Highest priority - most valuable data
    },
    'engineering': {
        'path': '../Engineering',  # Up one level
        'description': 'AISC specs, structural design, wind load calculations',
        'priority': 2
    },
    'estimating': {
        'path': '../Estimating',
        'description': 'ABC pricing guides, Bluebeam workflows, cost estimation',
        'priority': 2
    },
    'learning_ai': {
        'path': '- LEARNING -',
        'description': 'AI automation, forensic cost analysis, Claude workflows',
        'priority': 3
    },
    'sales': {
        'path': '../Sales',
        'description': 'Gross margin analysis by salesperson',
        'priority': 3
    }
}


def scan_directory_tree(root_path: Path, max_depth: int = 3) -> List[Tuple[Path, str]]:
    """
    Recursively scan directory and return list of (file_path, category) tuples
    Only includes PDFs, CSVs, and key documents
    """
    documents = []
    
    def _scan(path: Path, depth: int = 0):
        if depth > max_depth:
            return
        
        try:
            for item in path.iterdir():
                if item.is_file():
                    # Only include these file types
                    if item.suffix.lower() in ['.pdf', '.csv', '.xlsx', '.txt', '.md']:
                        # Skip temp files
                        if not item.name.startswith('~'):
                            documents.append((item, path.relative_to(root_path)))
                            
                elif item.is_dir():
                    # Skip hidden/system directories
                    if not item.name.startswith('.') and not item.name.startswith('__'):
                        _scan(item, depth + 1)
                        
        except (PermissionError, OSError) as e:
            logger.info(f"    ⚠ Skipping {path.name}: {e}")
    
    _scan(root_path)
    return documents


def categorize_document(file_path: Path, rel_path: Path) -> str:
    """Determine document category based on path and content"""
    path_str = str(rel_path).lower()
    name_str = file_path.name.lower()
    
    # Cat Scale has highest priority
    if 'cat scale' in path_str or 'cat scale' in name_str:
        return 'cat_scale'
    
    # Engineering 
    elif 'engineering' in path_str or 'aisc' in name_str or 'structural' in name_str:
        return 'engineering'
    
    # Estimating
    elif 'estimating' in path_str or 'abc' in name_str or 'pricing' in name_str:
        return 'estimating'
    
    # AI/Learning
    elif 'learning' in path_str or 'ai' in name_str or 'claude' in name_str:
        return 'learning_ai'
    
    # Sales
    elif 'sales' in path_str or 'gm' in name_str or 'gross margin' in name_str:
        return 'sales'
    
    # Default to general
    else:
        return 'general'


def generate_document_html(file_path: Path, category: str, rel_path: Path) -> str:
    """Generate HTML summary for a document"""
    
    # Get file stats
    file_size = file_path.stat().st_size
    file_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
    
    # Build context from path
    path_context = str(rel_path).replace('\\', ' > ').replace('/', ' > ')
    
    # Determine document type
    doc_type = file_path.suffix.upper().replace('.', '')
    if doc_type == 'PDF':
        doc_type_desc = "PDF Document"
    elif doc_type in ['CSV', 'XLSX']:
        doc_type_desc = "Data Spreadsheet"
    elif doc_type == 'TXT':
        doc_type_desc = "Text Document"
    elif doc_type == 'MD':
        doc_type_desc = "Markdown Documentation"
    else:
        doc_type_desc = f"{doc_type} File"
    
    # Category display
    cat_display = CATEGORIES.get(category, {}).get('description', category)
    
    # Generate keywords from filename and path
    keywords = []
    keywords.extend(file_path.stem.replace('_', ' ').replace('-', ' ').split())
    keywords.extend(str(rel_path.parent.name).split())
    keywords = list(set(kw.lower() for kw in keywords if len(kw) > 2))
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Eagle Sign - {file_path.name}</title>
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
            font-size: 24px;
        }}
        .header .subtitle {{
            opacity: 0.9;
            font-size: 14px;
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
            font-size: 18px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 180px 1fr;
            gap: 12px;
            margin: 15px 0;
        }}
        .info-label {{
            font-weight: 600;
            color: #666;
            font-size: 14px;
        }}
        .info-value {{
            color: #2c3e50;
            font-size: 14px;
        }}
        .path-breadcrumb {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            color: #666;
            margin: 15px 0;
        }}
        .metadata {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
            font-size: 13px;
            color: #666;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 8px;
        }}
        .badge-primary {{
            background: #e3f2fd;
            color: #1976d2;
        }}
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        .keywords {{
            margin: 15px 0;
        }}
        .keyword {{
            display: inline-block;
            background: #e9ecef;
            padding: 5px 12px;
            border-radius: 15px;
            margin: 3px;
            font-size: 12px;
            color: #495057;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{file_path.name}</h1>
        <div class="subtitle">{doc_type_desc} • Category: {cat_display}</div>
    </div>
    
    <div class="section">
        <h2>Document Information</h2>
        <div class="info-grid">
            <div class="info-label">Category:</div>
            <div class="info-value"><span class="badge badge-primary">{category.replace('_', ' ').title()}</span></div>
            
            <div class="info-label">File Type:</div>
            <div class="info-value">{doc_type} ({doc_type_desc})</div>
            
            <div class="info-label">File Size:</div>
            <div class="info-value">{file_size:,} bytes ({file_size/1024:.1f} KB)</div>
            
            <div class="info-label">Last Modified:</div>
            <div class="info-value">{file_modified.strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        <div class="path-breadcrumb">
            📁 {path_context}
        </div>
    </div>
    
    <div class="section">
        <h2>Context & Usage</h2>
        <p><strong>Purpose:</strong> {cat_display}</p>
        <p><strong>Location:</strong> This document is part of Eagle Sign Co.'s internal knowledge base, specifically within the {category.replace('_', ' ')} category.</p>
        <p><strong>File Name:</strong> {file_path.name}</p>
    </div>
    
    <div class="metadata">
        <strong>Metadata for RAG Retrieval:</strong><br><br>
        
        <strong>Source System:</strong> Eagle Sign Co. - BOT TRAINING Knowledge Base<br>
        <strong>Category:</strong> {category}<br>
        <strong>File Path:</strong> {str(file_path)}<br><br>
        
        <div class="keywords">
            <strong>Keywords:</strong><br>
            {''.join(f'<span class="keyword">{kw}</span>' for kw in keywords[:20])}
        </div>
        
        <br>
        <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        <strong>Generator:</strong> Eagle Sign Gemini Corpus Builder v2.0
    </div>
</body>
</html>
"""
    
    return html


def main():
    """Main execution"""
    logger.info("\n" + "="*70)
    logger.info("EAGLE SIGN - GEMINI KNOWLEDGE BASE GENERATOR v2.0")
    logger.info("Document-Centric Approach")
    logger.info("="*70 + "\n")
    
    # Verify source directory
    if not DOC_ROOT.exists():
        logger.error(f"✗ ERROR: Source directory not found: {DOC_ROOT}")
        logger.info(f"  Please verify the BOT TRAINING directory location")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    # Step 1: Scan directory tree
    logger.info("Step 1: Scanning BOT TRAINING directory...")
    logger.info(f"Source: {DOC_ROOT}\n")
    
    documents = scan_directory_tree(DOC_ROOT)
    logger.info(f"✓ Found {len(documents)} documents\n")
    
    if len(documents) == 0:
        logger.info("✗ No documents found! Check directory structure")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    # Step 2: Categorize documents
    logger.info("Step 2: Categorizing documents...")
    categorized = defaultdict(list)
    
    for file_path, rel_path in documents:
        category = categorize_document(file_path, rel_path)
        categorized[category].append((file_path, rel_path))
    
    logger.info(f"✓ Categorization complete:\n")
    for category, docs in sorted(categorized.items(), key=lambda x: -len(x[1])):
        cat_info = CATEGORIES.get(category, {})
        desc = cat_info.get('description', category)
        logger.info(f"  {category.replace('_', ' ').title():20} {len(docs):4} docs  - {desc}")
    logger.info()
    
    # Step 3: Generate HTML documents
    logger.info("Step 3: Generating HTML summaries...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    generated = []
    skipped = []
    
    for category, docs in categorized.items():
        # Create category subdirectory
        cat_dir = OUTPUT_DIR / category
        cat_dir.mkdir(exist_ok=True)
        
        logger.info(f"\n Processing {category.replace('_', ' ').title()} ({len(docs)} documents)...")
        
        for i, (file_path, rel_path) in enumerate(docs, 1):
            try:
                # Generate HTML
                html_content = generate_document_html(file_path, category, rel_path)
                
                # Create safe filename
                safe_name = re.sub(r'[^\w\s-]', '', file_path.stem)
                safe_name = re.sub(r'[-\s]+', '_', safe_name)
                html_filename = f"{safe_name}.html"
                
                # Save
                output_path = cat_dir / html_filename
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                generated.append(output_path)
                
                if i % 10 == 0:  # Progress indicator every 10 files
                    logger.info(f"  {i}/{len(docs)} processed...")
                    
            except Exception as e:
                logger.info(f"  ⚠ Skipped {file_path.name}: {e}")
                skipped.append((file_path, str(e)))
    
    # Step 4: Generate index/summary
    logger.info("\nStep 4: Creating master index...")
    
    index_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Eagle Sign Knowledge Base - Master Index</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            max-width: 1200px;
            margin: 40px auto;
            padding: 30px;
            background: #f5f7fa;
            color: #2c3e50;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0 0 15px 0;
            font-size: 32px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-number {{
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }}
        .stat-label {{
            color: #666;
            font-size: 14px;
        }}
        .category-section {{
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .category-section h2 {{
            color: #667eea;
            margin-top: 0;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🦅 Eagle Sign Knowledge Base</h1>
        <p style="font-size: 16px; margin: 0;">Comprehensive Documentation Corpus for Gemini File Search RAG</p>
        <p style="font-size: 14px; margin-top: 10px; opacity: 0.9;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-number">{len(generated)}</div>
            <div class="stat-label">Total Documents</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{len(categorized)}</div>
            <div class="stat-label">Categories</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{len(skipped)}</div>
            <div class="stat-label">Skipped Files</div>
        </div>
    </div>
"""
    
    for category in sorted(categorized.keys()):
        docs = categorized[category]
        cat_info = CATEGORIES.get(category, {})
        desc = cat_info.get('description', category)
        
        index_html += f"""
    <div class="category-section">
        <h2>{category.replace('_', ' ').title()} ({len(docs)} documents)</h2>
        <p>{desc}</p>
        <p style="color: #666; font-size: 14px;">Files generated in: ./{category}/</p>
    </div>
"""
    
    index_html += """
    <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 20px; border-radius: 8px; margin-top: 30px;">
        <h3 style="margin-top: 0; color: #856404;">📋 Next Steps</h3>
        <ol style="color: #856404; line-height: 1.8;">
            <li>Visit <a href="https://aistudio.google.com" target="_blank">https://aistudio.google.com</a></li>
            <li>Sign in with your Google account</li>
            <li>Click "Create new corpus" or use existing corpus</li>
            <li>Upload ALL HTML files from this directory (organized by category folders)</li>
            <li>Test with queries like:
                <ul>
                    <li>"What are Cat Scale standard part pricing?"</li>
                    <li>"AISC structural steel specifications"</li>
                    <li>"ABC estimating workflow"</li>
                </ul>
            </li>
        </ol>
    </div>
</body>
</html>
"""
    
    index_path = OUTPUT_DIR / "INDEX.html"
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    # Final Summary
    logger.info("\n" + "="*70)
    logger.info("GENERATION COMPLETE!")
    logger.info("="*70)
    logger.info(f"\n✅ Generated {len(generated)} HTML documents")
    logger.info(f"✅ Organized into {len(categorized)} categories")
    logger.info(f"✅ Output directory: {OUTPUT_DIR}")
    logger.info(f"✅ Master index: INDEX.html")
    
    if skipped:
        logger.info(f"\n⚠ Skipped {len(skipped)} files (see details above)")
    
    logger.info(f"\n📋 NEXT STEPS:")
    logger.info(f"  1. Open INDEX.html in your browser to review")
    logger.info(f"  2. Visit https://aistudio.google.com")
    logger.info(f"  3. Create new corpus: 'eagle_sign_knowledge_base'")
    logger.info(f"  4. Upload all HTML files (by category folders)")
    logger.info(f"  5. Test with domain-specific queries")
    
    logger.info(f"\n💡 CATEGORIES GENERATED:")
    for category in sorted(categorized.keys()):
        logger.info(f"  • {category.replace('_', ' ').title()}: {len(categorized[category])} documents")
    
    logger.info(f"\n🚀 This corpus contains your CURATED knowledge base!")
    logger.info(f"   Much better than trying to extract from work orders.")
    
    input(f"\n\nPress Enter to exit...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n\n✗ ERROR: {e}")
        import traceback
import logging

logger = logging.getLogger(__name__)
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)

