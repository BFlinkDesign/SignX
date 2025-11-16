#!/bin/bash
# Health Check Script for All Solver Endpoints

set -e

API_URL="${API_URL:-http://localhost:8000}"
SIGNCALC_URL="${SIGNCALC_URL:-http://localhost:8002}"

echo "Solver Endpoints Health Check"
echo "=============================="
echo ""

# Test 1: Cabinet Derivation
echo "1. Testing Cabinet Derivation..."
RESPONSE=$(curl -s -X POST "${API_URL}/signage/common/cabinets/derive" \
  -H "Content-Type: application/json" \
  -d '{"site":{"wind_speed_mph":115.0,"exposure":"C"},"cabinets":[{"width_ft":14.0,"height_ft":8.0,"weight_psf":10.0}],"height_ft":25.0}')

if echo "$RESPONSE" | jq -e '.result.A_ft2' > /dev/null 2>&1; then
    echo "   ✅ PASS: Cabinet derivation working"
else
    echo "   ❌ FAIL: Cabinet derivation error"
    echo "$RESPONSE" | jq '.'
fi

# Test 2: Pole Selection
echo ""
echo "2. Testing Pole Selection..."
RESPONSE=$(curl -s -X POST "${API_URL}/signage/poles/options" \
  -H "Content-Type: application/json" \
  -d '{"mu_required_kipin":50.0,"prefs":{"family":"HSS","steel_grade":"A500B"}}')

if echo "$RESPONSE" | jq -e '.result' > /dev/null 2>&1; then
    echo "   ✅ PASS: Pole selection working"
else
    echo "   ❌ FAIL: Pole selection error"
    echo "$RESPONSE" | jq '.'
fi

# Test 3: Footing Solve
echo ""
echo "3. Testing Footing Solve..."
RESPONSE=$(curl -s -X POST "${API_URL}/signage/direct_burial/footing/solve" \
  -H "Content-Type: application/json" \
  -d '{"footing":{"diameter_ft":3.0},"soil_psf":3000.0,"M_pole_kipft":10.0,"num_poles":1}')

if echo "$RESPONSE" | jq -e '.result.min_depth_ft' > /dev/null 2>&1; then
    echo "   ✅ PASS: Footing solve working"
else
    echo "   ❌ FAIL: Footing solve error"
    echo "$RESPONSE" | jq '.'
fi

# Test 4: Baseplate Checks
echo ""
echo "4. Testing Baseplate Checks..."
RESPONSE=$(curl -s -X POST "${API_URL}/signage/baseplate/checks" \
  -H "Content-Type: application/json" \
  -d '{"plate":{"w_in":18.0,"l_in":18.0,"t_in":0.5},"loads":{"mu_kipft":10.0,"vu_kip":2.0,"tu_kip":1.0}}')

if echo "$RESPONSE" | jq -e '.result' > /dev/null 2>&1; then
    echo "   ✅ PASS: Baseplate checks working"
else
    echo "   ❌ FAIL: Baseplate checks error"
    echo "$RESPONSE" | jq '.'
fi

# Test 5: Signcalc Health
echo ""
echo "5. Testing Signcalc Service..."
RESPONSE=$(curl -s "${SIGNCALC_URL}/healthz")

if echo "$RESPONSE" | jq -e '.status == "ok"' > /dev/null 2>&1; then
    echo "   ✅ PASS: Signcalc service healthy"
else
    echo "   ❌ FAIL: Signcalc service error"
    echo "$RESPONSE"
fi

echo ""
echo "=============================="
echo "Health Check Complete"

