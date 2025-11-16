#!/usr/bin/env python3
"""
Master Integration Validator - Production Launch Checklist
Validates all 6 agent deliverables and system integration
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests
import logging

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


def print_status(message: str, status: str) -> None:
    """Print colored status message."""
    colors = {
        "PASS": Colors.GREEN,
        "FAIL": Colors.RED,
        "WARN": Colors.YELLOW,
        "INFO": Colors.BLUE,
    }
    logger.info(f"{colors.get(status, '')}[{status}]{Colors.RESET} {message}")


def check_file_exists(filepath: str) -> Tuple[bool, str]:
    """Check if file exists."""
    if Path(filepath).exists():
        return True, f"File exists: {filepath}"
    return False, f"Missing: {filepath}"


def check_linter() -> Tuple[bool, str]:
    """Check for linter errors."""
    try:
        result = subprocess.run(
            ["ruff", "check", ".", "--output-format=json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        errors = json.loads(result.stdout) if result.stdout else []
        if not errors:
            return True, "Zero linter errors"
        return False, f"Found {len(errors)} linter errors"
    except Exception as e:
        return False, f"Linter check failed: {e}"


def check_imports() -> Tuple[bool, str]:
    """Check Python imports resolve correctly."""
    try:
        # Test key imports
        subprocess.run(
            [sys.executable, "-c", "from apex.api.main import app; from apex.domains.signage import models"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            timeout=10,
        )
        return True, "All imports resolve"
    except subprocess.CalledProcessError:
        return False, "Import check failed"
    except Exception as e:
        return False, f"Import error: {e}"


def check_database_schemas() -> Tuple[bool, str]:
    """Check database schema SQL files exist."""
    schemas = [
        "services/api/src/apex/domains/signage/db/schemas.sql",
        "services/api/alembic/versions/001_initial_projects_schema.py",
    ]
    missing = [s for s in schemas if not Path(ROOT / s).exists()]
    if missing:
        return False, f"Missing schemas: {', '.join(missing)}"
    return True, "All schema files present"


def check_docker_compose() -> Tuple[bool, str]:
    """Check Docker Compose configuration."""
    compose_file = ROOT / "infra/compose.yaml"
    if not compose_file.exists():
        return False, "Docker Compose file not found"
    
    try:
        subprocess.run(["docker", "compose", "-f", str(compose_file), "config"], check=True, capture_output=True)
        return True, "Docker Compose valid"
    except subprocess.CalledProcessError:
        return False, "Docker Compose validation failed"
    except Exception as e:
        logger.warning("Exception in production_validator.py: %s", str(e))
        return False, "docker-compose not available"


def check_service_health() -> Tuple[bool, str]:
    """Check if services are running and healthy."""
    health_endpoints = [
        ("http://localhost:8000/health", "API"),
        ("http://localhost:8000/ready", "API Readiness"),
        ("http://localhost:8002/healthz", "Signcalc"),
        ("http://localhost:5432", "PostgreSQL"),
        ("http://localhost:6379", "Redis"),
        ("http://localhost:9200/_cluster/health", "OpenSearch"),
    ]
    
    healthy = []
    for url, name in health_endpoints:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code < 500:
                healthy.append(name)
        except Exception as e:
            logger.warning("Exception in production_validator.py: %s", str(e))
            pass
    
    if not healthy:
        return False, "No services responding"
    if len(healthy) < len(health_endpoints):
        return False, f"Partial: {len(healthy)}/{len(health_endpoints)} services healthy"
    return True, f"All {len(healthy)} services healthy"


def check_envelope_consistency() -> Tuple[bool, str]:
    """Test envelope response format."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        data = response.json()
        
        required = ["result", "assumptions", "confidence", "trace"]
        missing = [k for k in required if k not in data]
        if missing:
            return False, f"Missing envelope fields: {', '.join(missing)}"
        
        if not isinstance(data["assumptions"], list):
            return False, "Assumptions must be list"
        
        if not 0.0 <= data["confidence"] <= 1.0:
            return False, "Confidence out of range"
        
        return True, "Envelope format valid"
    except Exception as e:
        return False, f"Envelope check failed: {e}"


def run_tests() -> Tuple[bool, str]:
    """Run test suite."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return True, "All tests passed"
        return False, f"Tests failed: {result.returncode}"
    except subprocess.TimeoutExpired:
        return False, "Tests timed out"
    except Exception as e:
        return False, f"Test execution failed: {e}"


def main() -> None:
    """Run full production validation."""
    logger.info(f"{Colors.BLUE}{'='*80}{Colors.RESET}")
    logger.info(f"{Colors.BLUE}APEX CalcuSign - Master Integration Validator{Colors.RESET}")
    logger.info(f"{Colors.BLUE}{'='*80}{Colors.RESET}\n")
    
    checks = [
        ("Linter", check_linter),
        ("Imports", check_imports),
        ("Database Schemas", check_database_schemas),
        ("Docker Compose", check_docker_compose),
        ("Services Health", check_service_health),
        ("Envelope Format", check_envelope_consistency),
        ("Test Suite", run_tests),
    ]
    
    results: List[Tuple[str, bool, str]] = []
    
    for name, check_func in checks:
        logger.info(f"Checking {name}...", end=" ")
        try:
            passed, message = check_func()
            results.append((name, passed, message))
            status = "PASS" if passed else "FAIL"
            print_status(message, status)
        except Exception as e:
            results.append((name, False, f"Exception: {e}"))
            print_status(f"Exception: {e}", "FAIL")
    
    logger.info(f"\n{Colors.BLUE}{'='*80}{Colors.RESET}")
    logger.info(f"{Colors.BLUE}Validation Summary{Colors.RESET}")
    logger.info(f"{Colors.BLUE}{'='*80}{Colors.RESET}\n")
    
    passed_count = sum(1 for _, p, _ in results if p)
    total = len(results)
    
    for name, passed, message in results:
        status = "PASS" if passed else "FAIL"
        print_status(f"{name}: {message}", status)
    
    logger.info(f"\n{Colors.BLUE}Results: {passed_count}/{total} checks passed{Colors.RESET}\n")
    
    if passed_count == total:
        logger.info(f"{Colors.GREEN}✅ PRODUCTION READY - ALL SYSTEMS GO{Colors.RESET}")
        sys.exit(0)
    else:
        logger.error(f"{Colors.RED}❌ NOT READY - {total - passed_count} checks failed{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()

