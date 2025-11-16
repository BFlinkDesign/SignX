"""
Script to fix bare exception handlers across the codebase.

This script:
1. Finds all Python files with bare 'except Exception:' handlers
2. Adds logging import if not present
3. Replaces bare exception handlers with proper logging
"""
import re
import sys
from pathlib import Path
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


def has_logging_import(content: str) -> bool:
    """Check if file already has logging import."""
    return bool(re.search(r'^import logging', content, re.MULTILINE))


def add_logging_import(content: str) -> str:
    """Add logging import after other imports."""
    lines = content.split('\n')

    # Find the last import line
    last_import_idx = -1
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            last_import_idx = i

    if last_import_idx == -1:
        # No imports found, add at top after docstring
        for i, line in enumerate(lines):
            if not line.strip().startswith('"""') and not line.strip().startswith("'''"):
                if i > 0:
                    last_import_idx = i - 1
                    break

    # Insert logging import and logger initialization
    if last_import_idx >= 0:
        lines.insert(last_import_idx + 1, 'import logging')
        lines.insert(last_import_idx + 2, '')
        lines.insert(last_import_idx + 3, 'logger = logging.getLogger(__name__)')

    return '\n'.join(lines)


def fix_bare_exception_handlers(content: str, filepath: Path) -> Tuple[str, int]:
    """Fix bare exception handlers in content.

    Returns:
        Tuple of (fixed_content, number_of_fixes)
    """
    fixes = 0

    # Pattern to match: except Exception: followed by pass or continue
    # We'll fix these by adding exception variable and logging
    pattern = r'except Exception:\s*\n(\s+)(pass|continue|return [^#\n]*)'

    def replace_handler(match):
        nonlocal fixes
        fixes += 1
        indent = match.group(1)
        action = match.group(2)

        # Generate appropriate log message based on context
        log_msg = f'logger.warning("Exception in {filepath.name}: %s", str(e))'

        return f'except Exception as e:\n{indent}{log_msg}\n{indent}{action}'

    content = re.sub(pattern, replace_handler, content)

    return content, fixes


def process_file(filepath: Path) -> bool:
    """Process a single Python file.

    Returns:
        True if file was modified, False otherwise
    """
    try:
        content = filepath.read_text(encoding='utf-8')
        original_content = content

        # Check if file has bare exception handlers
        if 'except Exception:' not in content:
            return False

        # Fix exception handlers
        content, fixes = fix_bare_exception_handlers(content, filepath)

        if fixes == 0:
            return False

        # Add logging import if needed and there were fixes
        if not has_logging_import(content):
            content = add_logging_import(content)

        # Only write if content changed
        if content != original_content:
            filepath.write_text(content, encoding='utf-8')
            logger.info(f"[OK] Fixed {fixes} exception handler(s) in {filepath}")
            return True

        return False

    except Exception as e:
        logger.error(f"[ERROR] Error processing {filepath}: {e}", file=sys.stderr)
        return False


def main():
    """Main function to fix all Python files."""
    root = Path(__file__).parent.parent

    # Directories to skip
    skip_dirs = {
        'venv', '.venv', '__pycache__', '.pytest_cache',
        'node_modules', 'archive', 'SignX-Studio'
    }

    # Find all Python files
    python_files: List[Path] = []
    for py_file in root.rglob('*.py'):
        # Skip if in excluded directory
        if any(skip_dir in py_file.parts for skip_dir in skip_dirs):
            continue
        python_files.append(py_file)

    logger.info(f"Found {len(python_files)} Python files to check")

    # Process files
    modified_count = 0
    for py_file in python_files:
        if process_file(py_file):
            modified_count += 1

    logger.info(f"\n[DONE] Complete! Modified {modified_count} files")


if __name__ == '__main__':
    main()
