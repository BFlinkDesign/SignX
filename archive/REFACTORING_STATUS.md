# Refactoring Status

## Completed ✅

### 1. Envelope Builder Consolidation
**Status**: ✅ Complete

**Changes**:
- Enhanced `services/api/src/apex/api/common/models.py::make_envelope()` to:
  - Auto-inject `request_id` from context if middleware is active
  - Auto-fetch `code_version` and `model_config` if not provided
  - Handle optional parameters gracefully
  
- Consolidated `apex/services/api/src/apex/api/common/utils.py::build_envelope()`:
  - Unified implementation with request_id injection
  - Backward compatible wrapper functions maintained
  
- Deprecated duplicate functions:
  - `apex/services/api/src/apex/api/main.py::envelope()` → now uses `build_envelope`
  - `apex/services/api/src/apex/api/ready.py::_envelope()` → now uses `build_envelope`

**Result**: All envelope creation now goes through unified builders:
- `services/api/` codebase uses `make_envelope()` from `common.models`
- `apex/services/api/` codebase uses `build_envelope()` from `common.utils`
- Both support automatic request_id injection and optional parameter defaults

## Pending 🔄

### 2. Merge Duplicate API Codebases
**Status**: ⚠️ Analysis Needed

**Issue**: Two separate API implementations exist:
- `services/api/src/apex/api/` - More mature, has DB integration, full route set
- `apex/services/api/src/apex/api/` - Newer scaffold, minimal routes

**Options**:
1. **Consolidate into `services/api/`**: Migrate `apex/` features to mature codebase
2. **Consolidate into `apex/services/api/`**: Migrate `services/api/` features to monorepo
3. **Keep separate**: Document that `services/api/` is legacy, `apex/services/api/` is active

**Recommendation**: Option 3 for now - keep both but clearly document which is which.

### 3. Import Path Standardization
**Status**: ⚠️ Partial

**Issues**:
- Service stubs in `apex/services/*/src/apex/*/main.py` try to import from `apex.api.*` but path resolution unclear
- Some imports work, others fail depending on PYTHONPATH

**Next Steps**:
- Create shared `packages/schemas` with `ResponseEnvelope` for cross-service use
- Update service stubs to use shared packages instead of API internals
- Document PYTHONPATH requirements

### 4. Database Models Consolidation
**Status**: ⚠️ Analysis Needed

**Found**:
- `services/api/src/apex/api/db.py` - Full SQLAlchemy models (Project, ProjectPayload, ProjectEvent)
- `apex/services/api/src/apex/api/models/__init__.py` - Minimal Project model
- `services/api/src/apex/domains/signage/db/schemas.sql` - Raw SQL schemas

**Options**:
- Keep `services/api/db.py` as source of truth for mature codebase
- Migrate models to `apex/services/api/src/apex/api/models/` if consolidating
- Extract shared models to `packages/schemas` for cross-service use

## Code Quality Improvements

### Envelope Builders
- ✅ Single source of truth per codebase
- ✅ Automatic request_id injection
- ✅ Graceful fallbacks for optional parameters
- ✅ Consistent API across both codebases

### Import Clarity
- ⚠️ Service imports need standardizing (pending shared packages)
- ✅ Envelope builders use relative imports correctly
- ⚠️ Some absolute imports may fail depending on PYTHONPATH

## Completed in This Session ✅

### 5. Service Stub Updates
**Status**: ✅ Complete

**Changes**:
- Updated all service stubs (`materials`, `dfma`, `stackup`, `standards`) to use `packages.schemas`
- Removed dependency on `apex.api.*` internals
- All services now import `ResponseEnvelope` from shared package

### 6. Shared Utilities Enhancement
**Status**: ✅ Complete

**Changes**:
- Added `build_envelope()` to `packages/utils` for standalone services
- Added `load_json()` and `load_yaml()` utilities with consistent error handling
- Enhanced `sha256_digest()` with documentation
- All utilities use shared schemas from `packages/schemas`

## Next Refactoring Priorities

1. ✅ **Extract shared schemas** - DONE (`packages/schemas`)
2. ✅ **Update service stubs** - DONE (all 4 services updated)
3. ⚠️ **Consolidate config loaders** - Partially done (pricing routes updated)
4. ⚠️ **Consolidate SHA256 functions** - Utility exists, need to update callers
5. **Document codebase structure** - which codebase is active vs legacy
6. **Create migration guide** for consolidating `services/api` into `apex/services/api`

