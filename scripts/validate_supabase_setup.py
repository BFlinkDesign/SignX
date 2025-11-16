#!/usr/bin/env python3
"""Validate Supabase integration setup.

Checks:
1. All required files exist
2. Imports are correct
3. Settings configuration
4. Docker Compose configuration
5. Dependencies in pyproject.toml
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


class Colors:
    """ANSI color codes."""
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
    color = colors.get(status, "")
    print(f"{color}[{status}]{Colors.RESET} {message}")


def check_file_exists(filepath: Path) -> tuple[bool, str]:
    """Check if file exists."""
    if filepath.exists():
        return True, f"File exists: {filepath.relative_to(ROOT)}"
    return False, f"Missing: {filepath.relative_to(ROOT)}"


def check_imports() -> tuple[bool, list[str]]:
    """Check that required imports are present."""
    issues: list[str] = []
    
    # Check supabase_client.py
    client_file = ROOT / "services/api/src/apex/api/supabase_client.py"
    if client_file.exists():
        content = client_file.read_text()
        if "from supabase import create_client" not in content:
            issues.append("Missing supabase import in supabase_client.py")
        if "from gotrue.errors import AuthApiError" not in content:
            issues.append("Missing gotrue.errors import in supabase_client.py")
    
    # Check routes/auth.py
    auth_routes = ROOT / "services/api/src/apex/api/routes/auth.py"
    if auth_routes.exists():
        content = auth_routes.read_text()
        if "from ..supabase_client import get_supabase_client" not in content:
            issues.append("Missing supabase_client import in routes/auth.py")
        if "from gotrue.errors import AuthApiError" not in content:
            issues.append("Missing AuthApiError import in routes/auth.py")
    
    # Check auth.py
    auth_file = ROOT / "services/api/src/apex/api/auth.py"
    if auth_file.exists():
        content = auth_file.read_text()
        if "from .supabase_client import get_supabase_client" not in content:
            issues.append("Missing supabase_client import in auth.py")
    
    return len(issues) == 0, issues


def check_settings() -> tuple[bool, list[str]]:
    """Check Settings class includes Supabase fields."""
    deps_file = ROOT / "services/api/src/apex/api/deps.py"
    if not deps_file.exists():
        return False, ["deps.py not found"]
    
    content = deps_file.read_text()
    issues: list[str] = []
    
    if "SUPABASE_URL" not in content:
        issues.append("SUPABASE_URL not in Settings")
    if "SUPABASE_KEY" not in content:
        issues.append("SUPABASE_KEY not in Settings")
    if "SUPABASE_SERVICE_KEY" not in content:
        issues.append("SUPABASE_SERVICE_KEY not in Settings")
    
    return len(issues) == 0, issues


def check_dependencies() -> tuple[bool, list[str]]:
    """Check pyproject.toml includes supabase."""
    pyproject = ROOT / "services/api/pyproject.toml"
    if not pyproject.exists():
        return False, ["pyproject.toml not found"]
    
    content = pyproject.read_text()
    if '"supabase' not in content and "'supabase" not in content:
        return False, ["supabase not in dependencies"]
    
    return True, []


def check_docker_compose() -> tuple[bool, list[str]]:
    """Check Docker Compose includes Supabase service and env vars."""
    compose_file = ROOT / "infra/compose.yaml"
    if not compose_file.exists():
        return False, ["compose.yaml not found"]
    
    content = compose_file.read_text()
    issues: list[str] = []
    
    if "supabase-db:" not in content:
        issues.append("supabase-db service not in compose.yaml")
    if "APEX_SUPABASE_URL" not in content:
        issues.append("APEX_SUPABASE_URL not in api service env")
    if "APEX_SUPABASE_KEY" not in content:
        issues.append("APEX_SUPABASE_KEY not in api service env")
    if "supabase_db:" not in content:
        issues.append("supabase_db volume not defined")
    
    return len(issues) == 0, issues


def check_rls_sql() -> tuple[bool, str]:
    """Check RLS policies SQL file exists."""
    rls_file = ROOT / "services/api/src/apex/domains/signage/db/rls_policies.sql"
    if rls_file.exists():
        return True, f"RLS policies file exists: {rls_file.relative_to(ROOT)}"
    return False, f"Missing: {rls_file.relative_to(ROOT)}"


def check_project_integration() -> tuple[bool, list[str]]:
    """Check projects route integrates with auth."""
    projects_file = ROOT / "services/api/src/apex/api/routes/projects.py"
    if not projects_file.exists():
        return False, ["projects.py not found"]
    
    content = projects_file.read_text()
    issues: list[str] = []
    
    if "get_current_user_optional" not in content:
        issues.append("get_current_user_optional not used in create_project")
    if "from ..auth import" not in content:
        issues.append("Auth imports missing in projects.py")
    if "TokenData" not in content:
        issues.append("TokenData not imported/used in projects.py")
    
    return len(issues) == 0, issues


def main() -> int:
    """Run all validation checks."""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}  SUPABASE INTEGRATION VALIDATION{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    all_passed = True
    
    # File existence checks
    print_status("File Existence Checks", "INFO")
    files_to_check = [
        ROOT / "services/api/src/apex/api/supabase_client.py",
        ROOT / "services/api/src/apex/api/routes/auth.py",
        ROOT / "services/api/src/apex/domains/signage/db/rls_policies.sql",
        ROOT / "SUPABASE_SETUP.md",
    ]
    
    for filepath in files_to_check:
        exists, msg = check_file_exists(filepath)
        print_status(msg, "PASS" if exists else "FAIL")
        if not exists:
            all_passed = False
    
    # Import checks
    print_status("\nImport Validation", "INFO")
    imports_ok, import_issues = check_imports()
    if imports_ok:
        print_status("All imports correct", "PASS")
    else:
        for issue in import_issues:
            print_status(issue, "FAIL")
            all_passed = False
    
    # Settings checks
    print_status("\nSettings Configuration", "INFO")
    settings_ok, setting_issues = check_settings()
    if settings_ok:
        print_status("Supabase settings configured", "PASS")
    else:
        for issue in setting_issues:
            print_status(issue, "FAIL")
            all_passed = False
    
    # Dependencies
    print_status("\nDependencies", "INFO")
    deps_ok, dep_issues = check_dependencies()
    if deps_ok:
        print_status("supabase in pyproject.toml", "PASS")
    else:
        for issue in dep_issues:
            print_status(issue, "FAIL")
            all_passed = False
    
    # Docker Compose
    print_status("\nDocker Compose", "INFO")
    compose_ok, compose_issues = check_docker_compose()
    if compose_ok:
        print_status("Supabase service and env vars configured", "PASS")
    else:
        for issue in compose_issues:
            print_status(issue, "FAIL")
            all_passed = False
    
    # RLS SQL
    print_status("\nRLS Policies", "INFO")
    rls_ok, rls_msg = check_rls_sql()
    print_status(rls_msg, "PASS" if rls_ok else "FAIL")
    if not rls_ok:
        all_passed = False
    
    # Project integration
    print_status("\nProject Route Integration", "INFO")
    project_ok, project_issues = check_project_integration()
    if project_ok:
        print_status("Projects route integrates with auth", "PASS")
    else:
        for issue in project_issues:
            print_status(issue, "FAIL")
            all_passed = False
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    if all_passed:
        print_status("All validation checks passed!", "PASS")
        print(f"\n{Colors.GREEN}[OK] Supabase integration is correctly configured{Colors.RESET}")
        print(f"{Colors.YELLOW}[WARN] Remember to set Supabase environment variables{Colors.RESET}")
        return 0
    else:
        print_status("Some validation checks failed", "FAIL")
        print(f"\n{Colors.RED}[ERROR] Please fix the issues above{Colors.RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

