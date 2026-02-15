# SignX/APEX - Master Implementation Plan

**Version:** 1.0.0
**Created:** 2026-01-22
**Status:** Comprehensive Plan for 100% Functional System

---

## Executive Summary

This document consolidates the complete implementation plan for transforming SignX/APEX from its current ~50% complete state to a fully functional, PE-stampable structural engineering calculation system.

### Current State Assessment

| Module | Completeness | Production Ready |
|--------|-------------|------------------|
| ASCE 7-22 Wind | 95% | ✅ |
| Single Pole Analysis | 80% | ⚠️ |
| Monument Analysis | 70% | ❌ |
| Cantilever Analysis | 60% | ❌ |
| Foundation/Embedment | 40% | ❌ |
| Anchors/Baseplate | 20% | ❌ |
| BOM Generation | 30% | ❌ |
| Agent Services | 20% | ❌ |
| Frontend | 5% | ❌ |
| Database/API Structure | 90% | ✅ |

**Total Estimated Completeness: ~50%**

---

## Plan Documents Created

### 1. Backend Engineering Plan
**Location:** `docs/backend/BACKEND_IMPLEMENTATION_PLAN.md`

Covers:
- Engineering calculation modules (Foundation, Anchor, Baseplate, Rebar, Combined Stress, Seismic)
- API routes completion status and requirements
- Data services (AISC v16, materials, soil, wind/seismic maps)
- Agent services implementation
- Integration points (geocoding, wind lookup, seismic data, CAD export)

### 2. Frontend Application Plan
**Location:** `docs/frontend/FRONTEND_IMPLEMENTATION_PLAN.md`

Covers:
- Technology stack (React 18+, TypeScript, MUI, Zustand, TanStack Query)
- Application architecture with folder structure
- Component hierarchy and routing strategy
- Sign Configuration Wizard (7 steps detailed)
- Results visualization components
- Real-time features (live calculations, WebSocket)
- Accessibility (WCAG 2.1 AA)

### 3. Testing Strategy
**Location:** `docs/testing/COMPREHENSIVE_TESTING_PLAN.md`

Covers:
- Unit tests for all engineering calculations
- Expected values from code examples (ASCE, AISC, ACI, IBC)
- Real-world validation cases with hand calculations
- Integration, contract, regression tests
- Performance tests (<100ms latency target)
- Security tests (OWASP coverage)
- Simulation/Monte Carlo analysis

**Reference Cases:** `tests/fixtures/reference_cases.json` (50 test cases)

### 4. Database Architecture
**Location:** `docs/database/DATABASE_ARCHITECTURE_PLAN.md`

Migrations created:
- `013_add_wind_seismic_soil_tables.py`
- `014_add_anchor_catalog.py`
- `015_add_calculation_archive.py`
- `016_add_bom_pricing_tables.py`
- `017_add_user_organization_tables.py`

New tables:
- `wind_speed_maps`, `seismic_parameters`, `soil_classifications`
- `anchor_catalog`, `anchor_adjustment_factors`
- `calculation_archive`, `calculation_inputs`
- `bom_items`, `labor_rates`, `supplier_quotes`
- `user_profiles`, `organizations`, `organization_members`

### 5. Infrastructure Plan
**Location:** `docs/infrastructure/INFRASTRUCTURE_PLAN.md`

Created:
- Kubernetes Helm charts (`infra/helm/apex/`)
- CI/CD pipeline (`.github/workflows/ci-cd-full.yml`)
- Production Docker Compose (`infra/compose.production.yaml`)
- Monitoring (Prometheus, Grafana, Loki, Alertmanager)
- Backup scripts and DR runbooks

### 6. Security Architecture
**Location:** `docs/security/SECURITY_ARCHITECTURE.md`

Covers:
- Authentication (OAuth 2.0 PKCE, MFA)
- Authorization (RBAC with 6 roles)
- API security (rate limiting, input validation, request signing)
- Data security (encryption, PII handling)
- Audit and compliance (PE stamp tracking)
- OWASP Top 10 mitigations

---

## Implementation Phases

### Phase 1: Core Engineering (Weeks 1-4)

**Priority:** P0 - Safety Critical

| Task | File | Status |
|------|------|--------|
| Foundation design with Broms method | `apex_signcalc/foundation_broms.py` | New |
| ACI 318-19 anchor design | `apex_signcalc/anchor_aci318.py` | New |
| AISC Design Guide 1 baseplate | `apex_signcalc/baseplate_aisc.py` | New |
| AISC 360-22 combined stress | `apex_signcalc/combined_stress_aisc.py` | New |
| Fix single_pole_solver syntax error | `domains/signage/single_pole_solver.py:20` | Fix |
| Remove hardcoded section fallbacks | `domains/signage/solvers.py:86-126` | Fix |

### Phase 2: Data Infrastructure (Weeks 2-3)

| Task | Migration | Records |
|------|-----------|---------|
| Full AISC v16 shapes database | seed_aisc_shapes.py | ~2,500 |
| Wind speed maps (ASCE 7-22) | 013_wind_seismic_soil | ~500 cities |
| Seismic parameters (USGS) | 013_wind_seismic_soil | ~500 cities |
| Soil parameters | 013_wind_seismic_soil | 15 types |
| Anchor catalog | 014_anchor_catalog | ~100 products |

### Phase 3: API Completion (Weeks 4-5)

| Endpoint | Route File | Status |
|----------|------------|--------|
| POST /foundation/broms-analysis | routes/foundation.py | New |
| POST /foundation/spread-footing | routes/foundation.py | New |
| POST /anchors/design | routes/anchors.py | New |
| POST /anchors/verify | routes/anchors.py | New |
| POST /seismic/component-forces | routes/seismic.py | New |
| GET /seismic/site-data/{lat}/{lon} | routes/seismic.py | New |
| Complete BOM with costing | routes/bom.py | Enhance |

### Phase 4: Frontend Application (Weeks 5-8)

| Week | Deliverable |
|------|-------------|
| 5-6 | Project scaffolding, auth, dashboard |
| 6-7 | Sign wizard steps 1-4 |
| 7-8 | Sign wizard steps 5-7, results viewer |
| 8 | BOM, CAD export, reports |

### Phase 5: Agent Services (Weeks 6-8)

| Agent | Current | Target |
|-------|---------|--------|
| agent_signs | Placeholder | Full BOM, electrical, compliance |
| agent_materials | Synthesized data | Real material database |
| agent_cad | FreeCAD only | DXF, STEP, PDF export |
| agent_dfma | Basic rules | Full DFMA analysis |
| agent_compliance | IP check only | IBC, NEC, MUTCD, ADA |

### Phase 6: Testing & Quality (Weeks 8-10)

| Test Type | Target Coverage | Key Areas |
|-----------|-----------------|-----------|
| Unit | 100% engineering | Wind, foundation, anchors |
| Integration | 90% routes | All POST endpoints |
| Contract | 100% | Envelope, OpenAPI |
| E2E | Critical paths | Wizard → results → export |
| Performance | <100ms p95 | Calculation endpoints |

### Phase 7: Infrastructure & Security (Weeks 10-12)

| Task | Priority |
|------|----------|
| Kubernetes deployment | High |
| CI/CD pipeline | High |
| Monitoring setup | Medium |
| Security hardening | High |
| Backup/DR procedures | Medium |

---

## Critical Fixes Required

### P0 - Must Fix Before Any Deployment

1. **Syntax Error** - `single_pole_solver.py:20-21`
   ```python
   # BROKEN:
   from apex.domains.signage.asce7_wind import (
   import logging  # <-- SYNTAX ERROR

   # FIX: Move import to separate line
   ```

2. **Placeholder Anchor Design** - `anchors_baseplate.py:7`
   - Returns static hardcoded values regardless of input
   - Must implement ACI 318-19 Chapter 17

3. **Hardcoded Section Fallbacks** - `solvers.py:86-126`
   - `_get_section_properties_sync` returns fake "reasonable defaults"
   - Production must query AISC database or fail

4. **Placeholder Rebar** - `rebar_schedules.py`
   - Only 3 hardcoded options
   - Must implement ACI 318-19 flexural design

---

## Engineering Code References

All calculations must include proper code citations:

| Standard | Version | Modules Using |
|----------|---------|---------------|
| ASCE 7 | 2022 | Wind, Seismic |
| AISC 360 | 2022 | Steel design |
| AISC DG1 | 2nd Ed | Baseplate |
| ACI 318 | 2019 | Anchors, Concrete |
| IBC | 2024 | Foundations, Load combos |

---

## Success Criteria

### Functional Completeness
- [ ] All sign types analyzed (monument, pylon, cantilever)
- [ ] Wind loads per ASCE 7-22 with code references
- [ ] Foundation design with SF >= 1.5 for OT
- [ ] Anchor design per ACI 318-19 Chapter 17
- [ ] Baseplate design per AISC DG1
- [ ] BOM generation with pricing
- [ ] CAD export (DXF minimum)
- [ ] PDF calculation report

### Engineering Accuracy
- [ ] Determinism verified (1000x run test)
- [ ] Hand calculations match code output
- [ ] All safety factors computed correctly
- [ ] Code section references on all outputs

### PE Stamp Readiness
- [ ] Complete audit trail
- [ ] Assumptions list on every calculation
- [ ] Code version SHA in envelope
- [ ] 7-year data retention configured
- [ ] PE signature block in reports

---

## File Manifest

### Documentation Created
```
docs/
├── MASTER_IMPLEMENTATION_PLAN.md (this file)
├── backend/BACKEND_IMPLEMENTATION_PLAN.md
├── frontend/FRONTEND_IMPLEMENTATION_PLAN.md
├── testing/COMPREHENSIVE_TESTING_PLAN.md
├── database/DATABASE_ARCHITECTURE_PLAN.md
├── infrastructure/INFRASTRUCTURE_PLAN.md
├── security/SECURITY_ARCHITECTURE.md
├── security/SECURITY_POLICY.md
├── security/DEPLOYMENT_SECURITY_CHECKLIST.md
└── runbooks/
    ├── BACKUP_PROCEDURES.md
    └── DISASTER_RECOVERY.md
```

### Infrastructure Created
```
infra/
├── helm/apex/ (complete Helm chart)
├── compose.production.yaml
├── nginx/nginx.conf
├── monitoring/
│   ├── alertmanager/alertmanager.yml
│   ├── loki/loki.yml
│   └── promtail/promtail.yml
├── security/
│   ├── pod-security-standards.yaml
│   ├── external-secrets.yaml
│   └── vault-policy.hcl
└── scripts/backup-postgres.sh
```

### Migrations Created
```
services/api/alembic/versions/
├── 013_add_wind_seismic_soil_tables.py
├── 014_add_anchor_catalog.py
├── 015_add_calculation_archive.py
├── 016_add_bom_pricing_tables.py
└── 017_add_user_organization_tables.py
```

### Test Fixtures
```
tests/fixtures/reference_cases.json (50 test cases)
```

### CI/CD
```
.github/workflows/ci-cd-full.yml (10-stage pipeline)
```

---

## Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Core Engineering | 4 weeks | None |
| Data Infrastructure | 2 weeks | Phase 1 |
| API Completion | 2 weeks | Phase 1, 2 |
| Frontend | 4 weeks | Phase 3 |
| Agent Services | 3 weeks | Phase 2, 3 |
| Testing | 3 weeks | Phase 4, 5 |
| Infrastructure | 2 weeks | Phase 6 |

**Total: 12-16 weeks for full completion**

---

## Next Steps

1. **Immediate** (This Week)
   - Fix single_pole_solver.py syntax error
   - Run database migrations
   - Seed AISC shapes database

2. **Week 1-2**
   - Implement foundation_broms.py
   - Implement anchor_aci318.py
   - Create first frontend scaffold

3. **Week 3-4**
   - Complete baseplate design
   - Integrate USGS seismic API
   - Build sign wizard steps 1-4

4. **Ongoing**
   - Write tests as each module is completed
   - PE engineer review of calculation outputs
   - Security scanning in CI/CD
