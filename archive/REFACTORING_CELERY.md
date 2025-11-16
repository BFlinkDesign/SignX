# Celery Configuration Consolidation Analysis

## Current State

### Celery App Definitions Found

1. **`apex/services/worker/src/apex/worker/main.py`**
   - Simple inline config
   - Broker/backend from env vars
   - Basic settings (acks_late, prefetch, visibility timeout)
   - Minimal tasks (health.ping, materials.score, dfma.analyze, stackup.calculate)

2. **`services/api/src/apex/worker/app.py`**
   - Factory function `create_celery_app()`
   - Includes task modules explicitly
   - JSON serialization
   - More comprehensive settings (timezone, max_tasks_per_child)

3. **`services/worker/src/apex/worker/app.py`**
   - Factory function `create_celery()`
   - Most comprehensive config (heartbeat, time limits, retry settings)
   - Includes BaseTask with logging hooks
   - Imports tasks module

4. **`services/worker/apex/worker/main.py`**
   - Minimal inline config
   - Simple health.ping task

### Differences

| Feature | apex/services/worker | services/api/worker | services/worker/app |
|---------|---------------------|---------------------|---------------------|
| Factory function | No | Yes | Yes |
| Task includes | No | Yes (explicit) | Yes (import) |
| Time limits | No | No | Yes (300s/270s) |
| Heartbeat | No | No | Yes |
| BaseTask class | No | No | Yes |
| Structured logging | No | No | Yes |

## Recommendations

### Option 1: Create Shared Celery Config Utility (Recommended)
- Location: `apex/packages/utils/celery_config.py`
- Provide `create_celery_app()` factory with:
  - Unified broker/backend resolution
  - Standard configuration defaults
  - Optional overrides via kwargs
  - Environment-aware settings

### Option 2: Document Configuration Patterns
- Keep separate configs for different use cases
- Document when to use which pattern:
  - Simple: inline app creation for minimal workers
  - Standard: factory function with explicit includes
  - Complex: factory with BaseTask and logging

### Option 3: Consolidate to Single Source
- Migrate all workers to use `services/worker/src/apex/worker/app.py` pattern
- Requires coordinating task registration across services

## Recommended Approach

**Phase 1**: Document current patterns and use cases (Option 2)
**Phase 2**: Create shared utility (Option 1) for new services
**Phase 3**: Gradually migrate existing services (Optional)

## Notes

- Different services have different Celery requirements
- Some need explicit task registration (includes), others use auto-discovery
- Time limits and heartbeat may not be needed for all workers
- Keep flexibility for service-specific needs

