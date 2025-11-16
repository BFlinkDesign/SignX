"""
Script to convert print() statements to proper logging calls.

This addresses SonarQube maintainability issues by replacing print()
with structured logging.
"""
import re
import sys
from pathlib import Path
from typing import Tuple
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
        stripped = line.strip()
        if stripped.startswith('import ') or stripped.startswith('from '):
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


def convert_prints_to_logging(content: str, filepath: Path) -> Tuple[str, int]:
    """Convert print() statements to logging calls.

    Returns:
        Tuple of (fixed_content, number_of_fixes)
    """
    fixes = 0

    # Skip test files and scripts that are meant to print
    skip_patterns = ['test_', 'conftest.py', 'setup.py', 'smoke.py']
    if any(pattern in filepath.name for pattern in skip_patterns):
        return content, 0

    # Pattern to match print() statements
    # Handle both print(...) and print(...)
    def replace_print(match):
        nonlocal fixes
        fixes += 1
        indent = match.group(1) or ''
        args = match.group(2)

        # Determine log level based on content
        args_lower = args.lower()
        if 'error' in args_lower or 'fail' in args_lower:
            level = 'error'
        elif 'warn' in args_lower:
            level = 'warning'
        elif 'debug' in args_lower:
            level = 'debug'
        else:
            level = 'info'

        return f'{indent}logger.{level}({args})'

    # Match print statements with various formats
    pattern = r'^(\s*)print\((.*?)\)\s*$'
    lines = content.split('\n')
    new_lines = []

    for line in lines:
        match = re.match(pattern, line)
        if match:
            new_line = replace_print(match)
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    return '\n'.join(new_lines), fixes


def process_file(filepath: Path) -> bool:
    """Process a single Python file.

    Returns:
        True if file was modified, False otherwise
    """
    try:
        content = filepath.read_text(encoding='utf-8')
        original_content = content

        # Check if file has print statements
        if 'print(' not in content:
            return False

        # Convert prints to logging
        content, fixes = convert_prints_to_logging(content, filepath)

        if fixes == 0:
            return False

        # Add logging import if needed and there were fixes
        if not has_logging_import(content):
            content = add_logging_import(content)

        # Only write if content changed
        if content != original_content:
            filepath.write_text(content, encoding='utf-8')
            logger.info(f"[OK] Converted {fixes} print() to logging in {filepath.name}")
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
        'node_modules', 'archive', 'SignX-Studio', 'tests'
    }

    # Find all Python files
    python_files = []
    for py_file in root.rglob('*.py'):
        # Skip if in excluded directory
        if any(skip_dir in py_file.parts for skip_dir in skip_dirs):
            continue
        python_files.append(py_file)

    logger.info(f"Found {len(python_files)} Python files to check (excluding tests)")

    # Process files
    modified_count = 0
    for py_file in python_files:
        if process_file(py_file):
            modified_count += 1

    logger.info(f"\n[DONE] Converted print() to logging in {modified_count} files")


if __name__ == '__main__':
    main()
