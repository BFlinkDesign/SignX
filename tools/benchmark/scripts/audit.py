#!/usr/bin/env python3
"""Audit script for running linting and testing on the benchmark project.

This script runs flake8 for style checking and pytest for testing,
providing a single command to validate code quality.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle its output.

    Args:
        cmd: List of command arguments to run
        description: Human-readable description of the command

    Returns:
        bool: True if command succeeded, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Running {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        if result.stdout:
            print("STDOUT:")
            print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        if result.returncode == 0:
            print(f"✅ {description} PASSED")
            return True
        else:
            print(f"❌ {description} FAILED (exit code: {result.returncode})")
            return False

    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        print(f"Make sure {cmd[0]} is installed and available in PATH")
        return False
    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False


def check_dependencies():
    """Check if required tools are available."""
    print("Checking dependencies...")

    dependencies = ["flake8", "pytest", "mypy"]
    missing = []

    for dep in dependencies:
        try:
            subprocess.run([dep, "--version"], capture_output=True, check=True)
            print(f"✅ {dep} is available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"❌ {dep} is not available")
            missing.append(dep)

    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print("Install them with: pip install " + " ".join(missing))
        return False

    return True


def run_linting():
    """Run flake8 linting on the project."""
    cmd = [
        "flake8",
        "benchmark/",
        "tests/",
        "scripts/",
        "--max-line-length=79",
        "--extend-ignore=E203,W503",  # Black compatibility
        "--show-source",
        "--statistics",
    ]

    return run_command(cmd, "Flake8 Linting")


def run_type_checking():
    """Run mypy type checking on the project."""
    cmd = [
        "mypy",
        "benchmark/",
        "--ignore-missing-imports",
        "--strict-optional",
        "--warn-redundant-casts",
        "--warn-unused-ignores",
    ]

    return run_command(cmd, "MyPy Type Checking")


def run_tests():
    """Run pytest on the test suite."""
    cmd = ["pytest", "tests/", "-v", "--tb=short", "--show-capture=all"]

    return run_command(cmd, "PyTest Testing")


def run_coverage():
    """Run pytest with coverage reporting."""
    cmd = [
        "pytest",
        "tests/",
        "--cov=benchmark",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "-v",
    ]

    return run_command(cmd, "Test Coverage Analysis")


def main():
    """Main audit function that runs all checks."""
    print("🔍 Starting Code Audit")
    print(f"Working directory: {os.getcwd()}")

    # Check if we're in the right directory
    project_root = Path(__file__).parent.parent
    if not (project_root / "benchmark").exists():
        print(f"❌ Project structure not found in {project_root}")
        return 1

    # Check dependencies
    if not check_dependencies():
        print("\n❌ Dependency check failed")
        return 1

    # Run all checks
    checks = []

    # Linting
    checks.append(("Linting", run_linting))

    # Type checking (optional - may not be critical for initial implementation)
    if "--with-mypy" in sys.argv:
        checks.append(("Type Checking", run_type_checking))

    # Testing
    checks.append(("Testing", run_tests))

    # Coverage (optional)
    if "--with-coverage" in sys.argv:
        checks.append(("Coverage", run_coverage))

    # Execute all checks
    results = {}
    for name, check_func in checks:
        results[name] = check_func()

    # Summary
    print(f"\n{'='*60}")
    print("AUDIT SUMMARY")
    print(f"{'='*60}")

    passed = 0
    total = len(results)

    for name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{name:<20}: {status}")
        if success:
            passed += 1

    print(f"\nOverall: {passed}/{total} checks passed")

    if passed == total:
        print("🎉 All audit checks PASSED!")
        return 0
    else:
        print("💥 Some audit checks FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
