#!/usr/bin/env python3
"""Integration test script for Supabase authentication endpoints.

Tests:
1. Registration (if Supabase configured)
2. Login
3. Token validation
4. Authenticated project creation
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8000"


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


def test_health() -> bool:
    """Test API health endpoint."""
    print_status("Testing API health...", "INFO")
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=5.0)
        if response.status_code == 200:
            print_status("API is healthy", "PASS")
            return True
        else:
            print_status(f"API returned {response.status_code}", "FAIL")
            return False
    except Exception as e:
        print_status(f"API not reachable: {e}", "FAIL")
        return False


def test_registration(email: str, password: str, account_id: str) -> dict | None:
    """Test user registration."""
    print_status(f"Testing registration for {email}...", "INFO")
    try:
        response = httpx.post(
            f"{BASE_URL}/auth/register",
            params={
                "email": email,
                "password": password,
                "account_id": account_id,
            },
            timeout=10.0,
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("result"):
                print_status("Registration successful", "PASS")
                return data
            else:
                print_status("Registration returned no result", "WARN")
                return data
        elif response.status_code == 503:
            print_status("Supabase not configured (expected if not set up)", "WARN")
            return None
        else:
            error_detail = response.json().get("detail", "Unknown error")
            print_status(f"Registration failed: {error_detail}", "WARN")
            return None
    except Exception as e:
        print_status(f"Registration error: {e}", "FAIL")
        return None


def test_login(username: str, password: str) -> dict | None:
    """Test user login."""
    print_status(f"Testing login for {username}...", "INFO")
    try:
        response = httpx.post(
            f"{BASE_URL}/auth/token",
            data={
                "grant_type": "password",
                "username": username,
                "password": password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("result", {}).get("access_token")
            if token:
                print_status("Login successful", "PASS")
                print_status(f"Token received: {token[:30]}...", "INFO")
                return data
            else:
                print_status("Login returned no token", "WARN")
                return data
        elif response.status_code == 503:
            print_status("Supabase not configured (expected if not set up)", "WARN")
            return None
        elif response.status_code == 401:
            print_status("Invalid credentials (user may not exist or email not confirmed)", "WARN")
            return None
        else:
            error_detail = response.json().get("detail", "Unknown error")
            print_status(f"Login failed: {error_detail}", "WARN")
            return None
    except Exception as e:
        print_status(f"Login error: {e}", "FAIL")
        return None


def test_authenticated_request(token: str) -> bool:
    """Test authenticated API request."""
    print_status("Testing authenticated project list...", "INFO")
    try:
        response = httpx.get(
            f"{BASE_URL}/projects/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5.0,
        )
        
        if response.status_code == 200:
            print_status("Authenticated request successful", "PASS")
            return True
        elif response.status_code == 401:
            print_status("Token validation failed", "WARN")
            return False
        else:
            print_status(f"Request failed: {response.status_code}", "WARN")
            return False
    except Exception as e:
        print_status(f"Request error: {e}", "FAIL")
        return False


def test_project_creation(token: str | None) -> bool:
    """Test creating a project (with or without auth)."""
    print_status("Testing project creation...", "INFO")
    try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        response = httpx.post(
            f"{BASE_URL}/projects/",
            json={
                "account_id": "test-account",
                "name": "Test Project",
                "customer": "Test Customer",
                "description": "Integration test project",
                "created_by": "test-user",
            },
            headers=headers,
            timeout=5.0,
        )
        
        if response.status_code == 200:
            data = response.json()
            project_id = data.get("result", {}).get("project_id")
            if project_id:
                print_status(f"Project created: {project_id}", "PASS")
                return True
            else:
                print_status("Project creation returned no project_id", "WARN")
                return False
        else:
            error_detail = response.json().get("detail", "Unknown error")
            print_status(f"Project creation failed: {error_detail}", "WARN")
            return False
    except Exception as e:
        print_status(f"Project creation error: {e}", "FAIL")
        return False


def main() -> int:
    """Run integration tests."""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}  SUPABASE AUTHENTICATION INTEGRATION TESTS{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    # Test 1: API Health
    if not test_health():
        print_status("\nAPI not available. Start the API first:", "FAIL")
        print_status("  docker-compose -f infra/compose.yaml up -d api", "INFO")
        return 1
    
    print()
    
    # Test 2: Registration
    test_email = "test@example.com"
    test_password = "Test123!Password"
    test_account = "eagle-sign"
    
    registration_result = test_registration(test_email, test_password, test_account)
    
    print()
    
    # Test 3: Login
    login_result = test_login(test_email, test_password)
    
    token = None
    if login_result and login_result.get("result"):
        token = login_result["result"].get("access_token")
    
    print()
    
    # Test 4: Authenticated Request (if token available)
    if token:
        test_authenticated_request(token)
        print()
    
    # Test 5: Project Creation
    test_project_creation(token)
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print_status("Integration tests complete", "INFO")
    print_status("\nNote: Some tests may be skipped if Supabase is not configured", "WARN")
    print_status("Set APEX_SUPABASE_URL and APEX_SUPABASE_KEY to enable full testing", "INFO")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

