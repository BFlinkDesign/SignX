# Solver Versioning and Compatibility

**Last Updated**: 2024-11-01  
**Status**: ✅ Strategy Documented

## Overview

Version tracking ensures reproducibility, backward compatibility, and audit trail integrity for all solver calculations.

## Version Tracking

Every calculation must include version information in the trace:

```json
{
  "trace": {
    "solver_versions": {
      "derive_loads": "1.2.0",
      "filter_poles": "1.1.0",
      "footing_solve": "1.3.0",
      "baseplate_checks": "1.2.0"
    },
    "constants_version": {
      "footing_calibration_k": "v1",
      "soil_bearing_multiplier": "v1"
    },
    "algorithm_version": {
      "pareto_optimization": "v2",
      "genetic_algorithm": "v1"
    },
    "code_version": {
      "git_sha": "abc123",
      "dirty": false,
      "build_id": "build-20241101"
    }
  }
}
```

## Version Components

### 1. Solver Function Versions

**Tracking**: `services/api/src/apex/domains/signage/solver_versioning.py`

**Current Versions:**
```python
_SOLVER_VERSIONS = {
    "derive_loads": "1.2.0",
    "filter_poles": "1.1.0",
    "footing_solve": "1.3.0",
    "baseplate_checks": "1.2.0",
    "baseplate_auto_solve": "1.0.0",
    "pareto_optimize_poles": "1.0.0",
    "baseplate_optimize_ga": "1.0.0",
    ...
}
```

**Versioning Scheme**: `MAJOR.MINOR.PATCH`
- **MAJOR**: Breaking changes (incompatible outputs)
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### 2. Constants Versions

**Tracking**: Database table `calibration_constants`

**Versioned Constants:**
- `footing_calibration_k` (v1, v2, ...)
- `soil_bearing_multiplier` (v1, v2, ...)
- `safety_factor_base` (v1, v2, ...)

**Effective Dates**: Track when each version was active

### 3. Algorithm Versions

**Tracking**: Code comments and documentation

**Versioned Algorithms:**
- `pareto_optimization`: v1 (NSGA-II), v2 (enhanced)
- `genetic_algorithm`: v1 (basic), v2 (adaptive)

### 4. Code Versions

**Tracking**: Git SHA, build ID

**Components:**
- Git SHA (short hash)
- Dirty flag (uncommitted changes)
- Build ID (CI/CD build identifier)

## Backward Compatibility

### Principles

1. **Old designs must remain reproducible**
   - Pin solver versions in database
   - Store full version information with each calculation
   - Re-run old calculations with original versions

2. **Version Pinning in Database**
   ```sql
   -- Store solver versions with each payload
   ALTER TABLE project_payloads ADD COLUMN solver_versions JSONB;
   
   -- Example:
   {
     "derive_loads": "1.2.0",
     "filter_poles": "1.1.0",
     ...
   }
   ```

3. **Migration Paths Documented**
   - How to upgrade designs from old versions
   - What changed between versions
   - Breaking changes clearly marked

### Compatibility Matrix

| Solver Version | Constants Version | Compatibility | Tested |
|---------------|-------------------|---------------|--------|
| v1.0.0 | ACI-318-2019 | ✅ Compatible | ⚠️ PENDING |
| v1.1.0 | ACI-318-2019 | ✅ Compatible | ⚠️ PENDING |
| v1.1.0 | ACI-318-2025 | ⚠️ Needs Testing | ⚠️ PENDING |
| v1.2.0 | ACI-318-2019 | ✅ Compatible | ⚠️ PENDING |
| v1.3.0 | ACI-318-2019 | ✅ Compatible | ⚠️ PENDING |

## Version Migration

### Upgrading Designs

**Process:**
1. Load design with old versions
2. Check compatibility with new versions
3. Re-run calculations with new versions
4. Compare results (should be identical or improved)
5. Update design with new versions

**Migration Script:**
```bash
# Migrate design from v1.0 to v1.1
python scripts/migrate_design.py \
  --from=v1.0 \
  --to=v1.1 \
  --design-id=12345 \
  --dry-run
```

**Status**: ⚠️ Migration script needs creation

### Breaking Changes

**Documentation Required:**
- What changed
- Why changed
- Impact on existing designs
- Migration instructions

**Example:**
```
## derive_loads v1.1.0 → v1.2.0

**Breaking Change**: Exposure factor interpolation changed
- Old: Linear interpolation
- New: Cubic spline interpolation
- Impact: Slight differences in wind loads (<2%)
- Migration: Re-run calculations, verify results
```

## Version Testing

### Test Matrix

| From Version | To Version | Test Result | Notes |
|--------------|------------|-------------|-------|
| v1.0.0 | v1.1.0 | ⚠️ PENDING | Needs testing |
| v1.1.0 | v1.2.0 | ⚠️ PENDING | Needs testing |
| v1.2.0 | v1.3.0 | ⚠️ PENDING | Needs testing |

### Test Process

1. Load test designs with old versions
2. Re-run with new versions
3. Compare outputs (should match or improve)
4. Document any differences

## Version Management

### Git Tagging

```bash
# Tag solver version releases
git tag solver-v1.2.0
git push --tags
```

### Release Notes

Each version should have release notes:
- **CHANGELOG.md**: Full change log
- **Migration Guide**: How to upgrade
- **Breaking Changes**: Clearly marked

## Signcalc Service Versioning

**Version Tracking**: `services/signcalc-service/main.py`

```python
app = FastAPI(title="APEX Sign Calculation Service", version="0.1.0")
```

**Schema Version**: `SCHEMA_VERSION = "v1"`

**Standards Pack Versioning**: SHA256 hashes
- Track which pack version was used
- Reproducible calculations

## Recommendations

1. ✅ **Track Versions**: All calculations include version info
2. ✅ **Pin Versions**: Store versions with each payload
3. ⚠️ **Test Compatibility**: Verify backward compatibility
4. ⚠️ **Migration Paths**: Document upgrade procedures
5. ⚠️ **Release Notes**: Document all changes

## Action Items

- [x] Document versioning strategy
- [x] Implement version tracking in code
- [ ] Create version compatibility test matrix
- [ ] Create migration scripts
- [ ] Test backward compatibility
- [ ] Document breaking changes
- [ ] Set up version release process

## Next Steps

1. **Test Compatibility**: Run compatibility matrix tests
2. **Create Migration Tools**: Build migration scripts
3. **Document Changes**: Update CHANGELOG for each version
4. **Automate**: Set up version tracking in CI/CD

