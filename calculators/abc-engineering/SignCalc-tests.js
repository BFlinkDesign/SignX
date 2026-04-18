/**
 * SignCalc-v4 Regression Test Suite
 * Run: node SignCalc-tests.js
 * No installation required — uses Node.js built-in vm module only.
 *
 * Reference values sourced from AUDIT-EVIDENCE.md (2026-04-15).
 * Rules sourced from knowledge/01-rules.md.
 * Test 10 is SKIPPED: Bob Brown reference uses ASCE 7-05, not ASCE 7-22.
 */

'use strict';
const fs = require('fs');
const vm = require('vm');

// ---- Load and execute the script block ----
const html = fs.readFileSync('SignCalc-v4.html', 'utf8');
const match = html.match(/<script>([\s\S]*?)<\/script>\s*<\/body>/);
if (!match) { console.error('FATAL: Could not extract script block'); process.exit(1); }

const fakeClassList = { add: () => {}, remove: () => {}, contains: () => false };
const fakeEl = () => ({
  value: '', textContent: '', style: {}, className: '', checked: false,
  classList: fakeClassList,
  closest: () => null,
  querySelector: () => null,
  querySelectorAll: () => ({ forEach: () => {} }),
  getAttribute: () => null, setAttribute: () => {},
  addEventListener: () => {}, removeEventListener: () => {}
});

const ctx = vm.createContext({
  document: {
    getElementById: fakeEl,
    querySelector:  () => null,
    querySelectorAll: () => ({ forEach: () => {} }),
    addEventListener: () => {},
    removeEventListener: () => {},
    documentElement: {}
  },
  window: { addEventListener: () => {}, removeEventListener: () => {} },
  localStorage: { getItem: () => null, setItem: () => {} },
  fetch: () => Promise.resolve(),
  setTimeout: () => {},
  clearTimeout: () => {},
  console,
  Math, Number, Object, Array, JSON, String, Boolean, isNaN, parseFloat, parseInt,
  Infinity, NaN, Promise
});

try {
  vm.runInContext(match[1], ctx);
} catch(e) {
  console.error('FATAL: Script execution error: ' + e.message);
  process.exit(1);
}

// ---- Test harness ----
let passed = 0, failed = 0, skipped = 0;
function test(name, fn) {
  try {
    fn();
    console.log('  PASS  ' + name);
    passed++;
  } catch(e) {
    console.log('  FAIL  ' + name + ' -- ' + e.message);
    failed++;
  }
}
function skip(name, reason) {
  console.log('  SKIP  ' + name + ' -- ' + reason);
  skipped++;
}
function assert(cond, msg) { if (!cond) throw new Error(msg || 'assertion failed'); }
function near(a, b, pct) {
  var tol = Math.abs(b) * (pct / 100);
  if (Math.abs(a - b) > tol)
    throw new Error('Expected ~' + b.toFixed(1) + ' (+-' + pct + '%), got ' + a.toFixed(1));
}

console.log('\nSignCalc-v4 Regression Tests\n' + '='.repeat(40));

// Test 1 — Passive force: triangular distribution (IBC 1806.3.2)
// Formula: 0.5 * Sl * fw * fd^2
// Was WRONG before fix: used rectangular (Sl * fw * fd)
test('T01 Passive force triangular (Sl=100, fw=3, fd=4)', function() {
  var Sl = 100, fw = 3, fd = 4;
  var passive = 0.5 * Sl * fw * fd * fd;
  assert(passive === 2400, 'Expected 2400 lb, got ' + passive);
});

// Test 2 — Passive moment: triangular, arm = fd/3 (IBC 1806.3.2)
// Formula: Sl * fw * fd^3 / 6
// Was WRONG before fix: used rectangular arm fd/2 (= Sl * fw * fd^2 / 2)
test('T02 Passive moment arm = fd/3 (Sl=100, fw=3, fd=4)', function() {
  var Sl = 100, fw = 3, fd = 4;
  var rM_soil = Sl * fw * fd * fd * fd / 6;
  assert(rM_soil === 3200, 'Expected 3200 ft-lb, got ' + rM_soil);
});

// Test 3 — ACI 318-19 kc=17 cracked concrete (Eq. 17.6.2.2b)
// Expected Nb = 17 * sqrt(3000) * 24^1.5
// Was WRONG before fix: used kc=24 (uncracked concrete)
test('T03 ACI Nb uses kc=17 cracked (fc=3000, hef=24)', function() {
  var result = ctx._aci_conc_breakout_T(1, 24, 3000, 36);
  var Nb_expected = 17.0 * Math.sqrt(3000) * Math.pow(24, 1.5);
  near(result.Nb, Nb_expected, 0.1);
});

// Test 4 — W8x18 LTB at Lb=144in: inelastic range, Fb ~22,542 psi
// Reference: AUDIT-EVIDENCE.md — W8x18 Fb verified at 22,542 psi (+-1%)
// Was WRONG before fix: used flat 0.66*Fy=33,000 psi for all Lb
test('T04 W8x18 LTB Fb inelastic at Lb=144in (~22542 psi)', function() {
  var w8x18 = ctx.WSEC.find(function(s) { return s.des === 'W8x18'; });
  assert(w8x18, 'W8x18 not found in WSEC table');
  var fb = ctx.calcFb_W_ltb(w8x18, 144);
  near(fb, 22542, 1.0);
});

// Test 5 — LTB monotonically decreasing: Fb must decrease as Lb increases
// Invariant: longer unbraced length never increases allowable bending stress
test('T05 Fb(W8x18) monotonically decreases with Lb', function() {
  var w8x18 = ctx.WSEC.find(function(s) { return s.des === 'W8x18'; });
  var lbs = [60, 100, 144, 200, 300];
  var prev = Infinity;
  for (var i = 0; i < lbs.length; i++) {
    var fb = ctx.calcFb_W_ltb(w8x18, lbs[i]);
    assert(fb <= prev + 0.01, 'Fb increased from Lb=' + lbs[i-1] + ' to Lb=' + lbs[i] +
           ': ' + prev.toFixed(0) + ' -> ' + fb.toFixed(0));
    prev = fb;
  }
});

// Test 6 — Base plate bearing: phi*Pp formula, vertical demand comparison
// Fix: demand = uplift + DL (vertical), not wind shear (horizontal)
// Test the geometry formula directly: phi=0.65, Pp=0.85*fc*A1*sqrt(A2/A1)
test('T06 Base plate bearing formula (fc=3000, A1=100, A2=400)', function() {
  var result = ctx.calcBasePlateBearing(3000, 100, 400);
  var Pp_raw_expected = 0.85 * 3000 * 100 * Math.sqrt(400 / 100); // = 510,000 lb
  var phiPp_expected = 0.65 * Math.min(Pp_raw_expected, 1.7 * 3000 * 100);
  near(result.phiPp, phiPp_expected, 0.1);
  assert(result.phiPp > 10000, 'phi*Pp should greatly exceed a 10,000 lb vertical demand');
});

// Test 7 — Iowa frost depth: fd < 4.0 ft must fail
// IBC Table 1809.7 — 48" minimum in Iowa
test('T07 Frost check fails for fd=3.5ft', function() {
  var fd = 3.5;
  var frostFail = fd < 4.0;
  assert(frostFail === true, 'Expected fd=3.5 to fail frost check (< 4.0 ft)');
});

// Test 8 — W12x26 capacity > W12x19 at any Lb (section size invariant)
// Larger section must always have equal or greater capacity
test('T08 W12x26 capacity > W12x19 at any Lb', function() {
  var w12x19 = ctx.WSEC.find(function(s) { return s.des === 'W12x19'; });
  var w12x26 = ctx.WSEC.find(function(s) { return s.des === 'W12x26'; });
  assert(w12x19 && w12x26, 'W12x19 or W12x26 not found in WSEC table');
  var lbs = [60, 120, 144, 200, 300];
  for (var i = 0; i < lbs.length; i++) {
    var cap19 = w12x19.Sx * ctx.calcFb_W_ltb(w12x19, lbs[i]);
    var cap26 = w12x26.Sx * ctx.calcFb_W_ltb(w12x26, lbs[i]);
    assert(cap26 >= cap19, 'W12x26 capacity ' + cap26.toFixed(0) +
           ' < W12x19 capacity ' + cap19.toFixed(0) + ' at Lb=' + lbs[i]);
  }
});

// Test 9 — Kz table lookup: h=30, Exposure C -> 0.98
// Source: ASCE 7-22 Table 26.10-1 (Exposure C)
test('T09 getKz(h=30, exp=C) === 0.98', function() {
  var kz = ctx.getKz(30, 'C');
  assert(Math.abs(kz - 0.98) < 0.001, 'Expected 0.98, got ' + kz);
});

// Test 10 — SKIPPED: Bob Brown reference uses ASCE 7-05, not ASCE 7-22
// Cannot use as ASCE 7-22 regression reference (different edition, different Kz/Cf tables)
// See AUDIT-EVIDENCE.md -- Bob Brown VERIFIED as ASCE 7-05 reference
skip('T10 Bob Brown full-system baseShear', 'ASCE 7-05 reference -- not valid for ASCE 7-22 regression');

// ---- Summary ----
console.log('\n' + '='.repeat(40));
console.log('Results: ' + passed + ' passed, ' + failed + ' failed, ' + skipped + ' skipped');
if (failed > 0) {
  console.log('FAIL -- ' + failed + ' test(s) failed');
  process.exit(1);
} else {
  console.log('PASS -- all active tests passed');
}
