#!/usr/bin/env python
"""
Update all Python files to use dotenv for database connections
Replaces hardcoded credentials with environment variables
"""

import os
import re
from pathlib import Path

# Files to update (relative to project root)
FILES_TO_UPDATE = [
    "fix_aisc_cosmetic.py",
    "fix_minor_issues.py",
    "fix_monument_function.py",
    "run_migrations.py",
    "scripts/import_aisc_database.py",
    "scripts/seed_aisc_sections.py",
    "scripts/seed_defaults.py",
]

# Import block to add
DOTENV_IMPORTS = """import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Build database URL from environment variables
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "signx_studio")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
"""

# Patterns to replace
OLD_PATTERNS = [
    (r'DATABASE_URL\s*=\s*"postgresql://apex:apex@localhost:5432/apex"',
     'DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"'),
    (r"DATABASE_URL\s*=\s*'postgresql://apex:apex@localhost:5432/apex'",
     'DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"'),
    (r'db_url\s*=\s*os\.environ\.get\("DATABASE_URL",\s*"postgresql://apex:apex@localhost:5432/apex"\)',
     'db_url = os.environ.get("DATABASE_URL", f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")'),
    (r"await asyncpg\.connect\('postgresql://apex:apex@localhost:5432/apex'\)",
     'await asyncpg.connect(DATABASE_URL)'),
]

def update_file(filepath):
    """Update a single file to use dotenv"""
    if not os.path.exists(filepath):
        logger.info(f"  [SKIP] File not found: {filepath}")
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Check if already has dotenv import
    if 'from dotenv import load_dotenv' in content:
        logger.info(f"  [SKIP] Already updated: {filepath}")
        return False

    # Add dotenv imports after existing imports
    import_section_end = 0
    lines = content.split('\n')

    for i, line in enumerate(lines):
        if line.strip().startswith('import ') or line.strip().startswith('from '):
            import_section_end = i + 1
        elif import_section_end > 0 and line.strip() == '':
            break

    # Insert dotenv code after imports
    if import_section_end > 0:
        lines.insert(import_section_end, '')
        lines.insert(import_section_end + 1, DOTENV_IMPORTS)
        content = '\n'.join(lines)

    # Replace hardcoded DATABASE_URL patterns
    modified = False
    for pattern, replacement in OLD_PATTERNS:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            modified = True

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"  [OK] Updated: {filepath}")
        return True
    else:
        logger.info(f"  [SKIP] No changes needed: {filepath}")
        return False

def main():
    logger.info("=" * 60)
    logger.info("Updating Python Files to Use dotenv")
    logger.info("=" * 60)
    logger.info()

    project_root = Path(__file__).parent
    updated_count = 0

    for filepath in FILES_TO_UPDATE:
        full_path = project_root / filepath
        if update_file(str(full_path)):
            updated_count += 1

    logger.info()
    logger.info("=" * 60)
    logger.info(f"Summary: {updated_count} files updated")
    logger.info("=" * 60)
    logger.info()
    logger.info("Next steps:")
    logger.info("1. Create .env file with your database credentials")
    logger.info("2. Install python-dotenv: pip install python-dotenv")
    logger.info("3. Test database connection")
    logger.info()

if __name__ == "__main__":
    main()
