# Validation Execution Guide

**Last Updated**: 2024-11-01  
**Status**: Ready for Execution

## Quick Start

All validation tests should be run in the Docker containerized environment to ensure proper dependencies.

### Container Execution

```bash
# Run determinism tests
docker-compose -f infra/compose.yaml exec api python scripts/test_determinism.py

# Run performance benchmarks
docker-compose -f infra/compose.yaml exec api python scripts/benchmark_solvers.py

# Run accuracy validation
docker-compose -f infra/compose.yaml exec api python scripts/validate_accuracy.py --reference-data=data/eagle_sign_projects.csv

# Run edge case tests
docker-compose -f infra/compose.yaml exec api pytest tests/solvers/test_edge_cases.py -v
```

### Alternative: Run in Container

```bash
# Execute commands in running container
docker-compose -f infra/compose.yaml run --rm api python scripts/test_determinism.py
docker-compose -f infra/compose.yaml run --rm api python scripts/benchmark_solvers.py
```

## Validation Tasks

### Task 1: Determinism Verification

**Script**: `scripts/test_determinism.py`

**Expected Output**:
```
Running Determinism Verification Tests...
============================================================

Repeated Execution (100 iterations):
✅ PASS: 100/100 identical results

Order Independence:
✅ PASS: Order-independent

============================================================
Summary:
  ✅ PASS: Repeated Execution (100 iterations)
  ✅ PASS: Order Independence
```

**Command**:
```bash
docker-compose -f infra/compose.yaml exec api python scripts/test_determinism.py
```

### Task 2: Performance Benchmarks

**Script**: `scripts/benchmark_solvers.py`

**Expected Output**:
```
Solver Performance Benchmarks
============================================================
Benchmarking derive_loads()...
  p50: 35.2ms
  p95: 72.1ms ✅ (target: <80ms)
  p99: 88.5ms ✅ (target: <100ms)

============================================================
Summary:
  benchmark_derive_loads: p95=72.1ms, p99=88.5ms
```

**Command**:
```bash
docker-compose -f infra/compose.yaml exec api python scripts/benchmark_solvers.py
```

**Target Metrics**:
- Throughput: >10 projects/sec
- Latency p95: <100ms
- Latency p99: <500ms

### Task 3: Accuracy Validation

**Script**: `scripts/validate_accuracy.py`

**Expected Output**:
```
Accuracy Validation Suite
============================================================

Loaded 2 test cases

Validating derive_loads()...
  ✅ PASS: test_1 - Error: 3.2%
  ✅ PASS: test_2 - Error: 4.8%

Validating footing_solve()...
  ✅ PASS: test_1 - Error: 2.1%
  ✅ PASS: test_2 - Error: 3.5%

============================================================
Summary:
  derive_loads RMSE: 4.1% ✅ (target: <10%)
  derive_loads Pass Rate: 2/2 (100%)
  footing_solve RMSE: 2.8% ✅ (target: <10%)
  footing_solve Pass Rate: 2/2 (100%)

✅ Overall: PASS (all validations within 10% RMSE)
```

**Command**:
```bash
docker-compose -f infra/compose.yaml exec api python scripts/validate_accuracy.py --reference-data=data/eagle_sign_projects.csv
```

**Target**: RMSE <10% on all solvers

### Task 4: Health Check All Solver Endpoints

**Endpoints to Test**:

1. **Cabinet Derivation**
   ```bash
   curl -X POST http://localhost:8000/signage/common/cabinets/derive \
     -H "Content-Type: application/json" \
     -d '{"site":{"wind_speed_mph":115.0,"exposure":"C"},"cabinets":[{"width_ft":14.0,"height_ft":8.0,"weight_psf":10.0}],"height_ft":25.0}'
   ```

2. **Pole Selection**
   ```bash
   curl -X POST http://localhost:8000/signage/poles/options \
     -H "Content-Type: application/json" \
     -d '{"mu_required_kipin":50.0,"prefs":{"family":"HSS","steel_grade":"A500B"}}'
   ```

3. **Footing Solve**
   ```bash
   curl -X POST http://localhost:8000/signage/direct_burial/footing/solve \
     -H "Content-Type: application/json" \
     -d '{"footing":{"diameter_ft":3.0},"soil_psf":3000.0,"M_pole_kipft":10.0,"num_poles":1}'
   ```

4. **Baseplate Checks**
   ```bash
   curl -X POST http://localhost:8000/signage/baseplate/checks \
     -H "Content-Type: application/json" \
     -d '{"plate":{"w_in":18.0,"l_in":18.0,"t_in":0.5},"loads":{"mu_kipft":10.0,"vu_kip":2.0,"tu_kip":1.0}}'
   ```

5. **Signcalc Design**
   ```bash
   curl -X POST http://localhost:8002/v1/signs/design \
     -H "Content-Type: application/json" \
     -d '{"schema_version":"v1","jurisdiction":"US","standard":{"code":"ASCE7","version":"16"},"site":{"exposure":"C"},"sign":{"width_ft":14.0,"height_ft":8.0,"centroid_height_ft":20.0},"support_options":["pipe"],"embed":{"type":"direct"}}'
   ```

**Health Check Script**:
```bash
# Run all health checks
./scripts/health_check_solvers.sh
```

### Task 5: Edge Case Testing

**Test File**: `tests/solvers/test_edge_cases.py`

**Command**:
```bash
docker-compose -f infra/compose.yaml exec api pytest tests/solvers/test_edge_cases.py -v
```

**Expected Output**:
```
tests/solvers/test_edge_cases.py::TestEdgeCases::test_zero_wind_speed PASSED
tests/solvers/test_edge_cases.py::TestEdgeCases::test_negative_dimensions PASSED
tests/solvers/test_edge_cases.py::TestEdgeCases::test_zero_cabinets PASSED
tests/solvers/test_edge_cases.py::TestEdgeCases::test_extreme_height PASSED
tests/solvers/test_edge_cases.py::TestEdgeCases::test_zero_soil_bearing PASSED
tests/solvers/test_edge_cases.py::TestEdgeCases::test_negative_moment PASSED
tests/solvers/test_edge_cases.py::TestEdgeCases::test_extreme_footing_depth PASSED
tests/solvers/test_edge_cases.py::TestEdgeCases::test_no_feasible_poles PASSED
tests/solvers/test_edge_cases.py::TestEdgeCases::test_missing_required_fields_baseplate PASSED
tests/solvers/test_edge_cases.py::TestEdgeCases::test_invalid_material_combination PASSED

===================== 10 passed in 2.34s =====================
```

## Success Criteria Checklist

- [ ] **Determinism**: 100% on all solvers ✓
- [ ] **Performance**: >10 projects/sec ✓
- [ ] **Accuracy**: RMSE <10% ✓
- [ ] **Edge cases**: All handled gracefully ✓
- [ ] **Health checks**: All passing ✓

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError`, ensure you're running in the container:
```bash
docker-compose -f infra/compose.yaml exec api python <script>
```

### Syntax Errors

If you see syntax errors, ensure all code changes are saved and the container is rebuilt:
```bash
docker-compose -f infra/compose.yaml build api
docker-compose -f infra/compose.yaml up -d api
```

### Test Failures

Review test output for specific failures and check:
1. Input data format matches expected schema
2. Dependencies are installed
3. Services are running

## Next Steps

1. Execute all validation tasks in staging
2. Document actual results
3. Fix any issues found
4. Re-run validation to confirm fixes
5. Proceed to production deployment

