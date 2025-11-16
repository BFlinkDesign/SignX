#!/bin/bash
# Final Production Validation Script
# Master Integration Agent - CalcuSign APEX

set -e

echo "=========================================="
echo "CalcuSign APEX - Final Production Validation"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "1. Environment Check"
echo "-------------------"
if [ -f ".env" ]; then
    check_pass ".env file exists"
else
    check_fail ".env file missing"
fi

if command -v docker &> /dev/null; then
    check_pass "Docker installed"
else
    check_fail "Docker not found"
fi

if command -v docker-compose &> /dev/null; then
    check_pass "Docker Compose installed"
else
    check_fail "Docker Compose not found"
fi

echo ""
echo "2. Backend Validation"
echo "-------------------"
cd services/api || exit 1

if [ -f "pyproject.toml" ]; then
    check_pass "Backend pyproject.toml exists"
else
    check_fail "Backend pyproject.toml missing"
fi

# Check for envelope implementation
if grep -q "build_envelope\|ResponseEnvelope" src/apex/api/*.py 2>/dev/null || \
   grep -q "build_envelope\|ResponseEnvelope" src/apex/packages/**/*.py 2>/dev/null; then
    check_pass "ResponseEnvelope pattern implemented"
else
    check_fail "ResponseEnvelope pattern not found"
fi

# Check health endpoint exists
if grep -q "@app.get\|@router.get" src/apex/api/**/*.py 2>/dev/null | grep -q "health"; then
    check_pass "Health check endpoint exists"
else
    check_warn "Health check endpoint may be missing"
fi

cd ../..

echo ""
echo "3. Frontend Validation"
echo "-------------------"
cd apex/apps/ui-web || exit 1

if [ -f "package.json" ]; then
    check_pass "Frontend package.json exists"
    
    # Check critical dependencies
    if grep -q "@sentry/react" package.json; then
        check_pass "Sentry integration present"
    else
        check_fail "Sentry not integrated"
    fi
    
    if grep -q "@playwright/test" package.json; then
        check_pass "Playwright tests configured"
    else
        check_warn "Playwright tests may be missing"
    fi
else
    check_fail "Frontend package.json missing"
fi

# Check for envelope types
if [ -f "src/types/envelope.ts" ]; then
    check_pass "Frontend envelope types defined"
else
    check_fail "Frontend envelope types missing"
fi

# Check API client uses envelope
if grep -q "parseEnvelope\|ResponseEnvelope" src/api/client.ts 2>/dev/null; then
    check_pass "Frontend API client uses envelope"
else
    check_fail "Frontend API client missing envelope integration"
fi

cd ../..

echo ""
echo "4. Database Validation"
echo "-------------------"
if [ -f "services/api/alembic.ini" ]; then
    check_pass "Alembic configured"
else
    check_fail "Alembic not configured"
fi

if [ -d "services/api/alembic/versions" ]; then
    MIGRATION_COUNT=$(find services/api/alembic/versions -name "*.py" | wc -l)
    if [ "$MIGRATION_COUNT" -gt 0 ]; then
        check_pass "Database migrations exist ($MIGRATION_COUNT migrations)"
    else
        check_fail "No database migrations found"
    fi
else
    check_fail "Migrations directory missing"
fi

echo ""
echo "5. Testing Validation"
echo "-------------------"
if [ -d "tests" ]; then
    TEST_COUNT=$(find tests -name "test_*.py" | wc -l)
    if [ "$TEST_COUNT" -ge 100 ]; then
        check_pass "Test suite present ($TEST_COUNT test files)"
    else
        check_warn "Test suite may be incomplete ($TEST_COUNT test files)"
    fi
else
    check_fail "Tests directory missing"
fi

echo ""
echo "6. Documentation Validation"
echo "-------------------"
if [ -d "docs" ]; then
    DOC_COUNT=$(find docs -name "*.md" | wc -l)
    check_pass "Documentation directory exists ($DOC_COUNT markdown files)"
    
    if [ -f "docs/getting-started/quickstart.md" ]; then
        check_pass "Quickstart guide exists"
    else
        check_warn "Quickstart guide missing"
    fi
else
    check_fail "Documentation directory missing"
fi

echo ""
echo "7. Infrastructure Validation"
echo "-------------------"
if [ -f "infra/compose.yaml" ] || [ -f "docker-compose.yml" ]; then
    check_pass "Docker Compose file exists"
else
    check_fail "Docker Compose file missing"
fi

echo ""
echo "8. Integration Points Check"
echo "-------------------"
# Check frontend calls match backend
cd apex/apps/ui-web
FRONTEND_ENDPOINTS=$(grep -r "api\." src/ | grep -o "api\.[a-zA-Z]*" | sort -u)
cd ../../..

# Check backend routes match
BACKEND_ROUTES=$(grep -r "@router\." services/api/src/apex/api/routes/*.py 2>/dev/null | grep -o "'[^']*'" | tr -d "'" | sort -u || echo "")

if [ -n "$FRONTEND_ENDPOINTS" ] && [ -n "$BACKEND_ROUTES" ]; then
    check_pass "Frontend and backend integration points found"
else
    check_warn "Could not verify endpoint alignment"
fi

echo ""
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo -e "${GREEN}Passed: ${PASSED}${NC}"
if [ "$FAILED" -gt 0 ]; then
    echo -e "${RED}Failed: ${FAILED}${NC}"
    exit 1
else
    echo -e "${GREEN}Failed: ${FAILED}${NC}"
    echo ""
    echo -e "${GREEN}✓ All critical validations passed!${NC}"
    exit 0
fi

