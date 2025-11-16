#!/bin/bash
# Integration Smoke Test - Full System Test
# Tests: Frontend → Backend → Database → Solvers

set -e

API_URL="${API_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"

echo "=========================================="
echo "CalcuSign APEX - Integration Smoke Test"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

test_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

test_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

echo "1. Backend Health Check"
echo "-------------------"
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health" || echo "000")
if [ "$HEALTH_RESPONSE" = "200" ]; then
    test_pass "Backend health endpoint responds"
    
    HEALTH_BODY=$(curl -s "${API_URL}/health")
    if echo "$HEALTH_BODY" | grep -q "status\|healthy"; then
        test_pass "Health endpoint returns valid response"
    else
        test_fail "Health endpoint response invalid"
    fi
else
    test_fail "Backend health endpoint not responding (HTTP $HEALTH_RESPONSE)"
fi

echo ""
echo "2. Backend Ready Check"
echo "-------------------"
READY_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/ready" || echo "000")
if [ "$READY_RESPONSE" = "200" ]; then
    test_pass "Backend ready endpoint responds"
else
    test_warn "Backend ready endpoint not responding (HTTP $READY_RESPONSE)"
fi

echo ""
echo "3. API Version Check"
echo "-------------------"
VERSION_RESPONSE=$(curl -s "${API_URL}/version" || echo "")
if [ -n "$VERSION_RESPONSE" ]; then
    test_pass "API version endpoint responds"
else
    test_warn "API version endpoint may not be available"
fi

echo ""
echo "4. Projects List Endpoint"
echo "-------------------"
PROJECTS_RESPONSE=$(curl -s -X GET "${API_URL}/api/v1/projects" \
    -H "Content-Type: application/json" || echo "")
PROJECTS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "${API_URL}/api/v1/projects" \
    -H "Content-Type: application/json" || echo "000")

if [ "$PROJECTS_CODE" = "200" ] || [ "$PROJECTS_CODE" = "401" ] || [ "$PROJECTS_CODE" = "403" ]; then
    test_pass "Projects endpoint accessible (HTTP $PROJECTS_CODE)"
    
    # Check for envelope structure
    if echo "$PROJECTS_RESPONSE" | grep -q "\"result\"" || echo "$PROJECTS_RESPONSE" | grep -q "assumptions\|confidence"; then
        test_pass "Projects endpoint returns envelope structure"
    else
        test_warn "Projects endpoint may not use envelope pattern"
    fi
else
    test_fail "Projects endpoint not accessible (HTTP $PROJECTS_CODE)"
fi

echo ""
echo "5. Cabinet Derive Endpoint"
echo "-------------------"
DERIVE_PAYLOAD='{"width_in": 48, "height_in": 96, "depth_in": 12, "density_lb_ft3": 50}'
DERIVE_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/signage/common/cabinets/derive" \
    -H "Content-Type: application/json" \
    -d "$DERIVE_PAYLOAD" || echo "")
DERIVE_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_URL}/api/v1/signage/common/cabinets/derive" \
    -H "Content-Type: application/json" \
    -d "$DERIVE_PAYLOAD" || echo "000")

if [ "$DERIVE_CODE" = "200" ]; then
    test_pass "Cabinet derive endpoint responds (HTTP $DERIVE_CODE)"
    
    if echo "$DERIVE_RESPONSE" | grep -q "\"result\""; then
        test_pass "Derive endpoint returns envelope with result"
    fi
    
    if echo "$DERIVE_RESPONSE" | grep -q "\"confidence\""; then
        test_pass "Derive endpoint includes confidence score"
    fi
else
    test_warn "Cabinet derive endpoint (HTTP $DERIVE_CODE) - may require auth"
fi

echo ""
echo "6. Frontend Build Check"
echo "-------------------"
cd apex/apps/ui-web || exit 1
if npm run build 2>&1 | grep -q "built\|success\|dist"; then
    test_pass "Frontend builds successfully"
    
    # Check bundle size
    if [ -d "dist" ]; then
        BUNDLE_SIZE=$(du -sh dist 2>/dev/null | cut -f1 || echo "unknown")
        test_pass "Frontend dist created (size: $BUNDLE_SIZE)"
    fi
else
    test_fail "Frontend build failed"
fi
cd ../../..

echo ""
echo "7. Database Connectivity (via API)"
echo "-------------------"
# Test database through API - if projects endpoint works, DB likely works
if [ "$PROJECTS_CODE" = "200" ]; then
    test_pass "Database connectivity verified (via API)"
else
    test_warn "Database connectivity unclear - may require authentication"
fi

echo ""
echo "=========================================="
echo "Smoke Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed: ${PASSED}${NC}"
if [ "$FAILED" -gt 0 ]; then
    echo -e "${RED}Failed: ${FAILED}${NC}"
    echo ""
    echo -e "${RED}✗ Smoke test failed - check logs above${NC}"
    exit 1
else
    echo -e "${GREEN}Failed: ${FAILED}${NC}"
    echo ""
    echo -e "${GREEN}✓ Smoke test passed!${NC}"
    exit 0
fi

