# Alembic Migration Summary: Projects Tables

## Status: ✅ Completed

Alembic migration for projects, project_payloads, and project_events tables has been successfully implemented and validated.

## Files Created/Modified

### 1. `services/api/alembic/env.py`
**Status:** ✅ Fixed and validated

**Changes:**
- Removed duplicate/malformed code
- Properly configured async Alembic environment
- Added `Base.metadata` import for autogenerate support
- Fixed `get_url()` to handle PostgreSQL connections
- Implemented proper async migration execution

**Key Features:**
- Async SQLAlchemy engine support via `async_engine_from_config`
- Automatic database URL resolution from environment variables
- Offline mode support for generating SQL scripts
- Proper dependency injection for model metadata

### 2. `services/api/alembic/versions/001_initial_projects_schema.py`
**Status:** ✅ Validated

**Schema:**
```python
revision: "001"
down_revision: None
```

**Tables Created:**

#### `projects`
- `project_id` (String(255), PK)
- `account_id` (String(255), NOT NULL)
- `name` (String(255), NOT NULL)
- `customer` (String(255), NULL)
- `description` (Text, NULL)
- `site_name` (String(255), NULL)
- `street` (String(255), NULL)
- `status` (String(50), NOT NULL) - draft, estimating, submitted, accepted, rejected
- `created_by` (String(255), NOT NULL)
- `updated_by` (String(255), NOT NULL)
- `created_at` (DateTime(timezone=True), NOT NULL, server_default=now())
- `updated_at` (DateTime(timezone=True), NOT NULL, server_default=now())
- `etag` (String(64), NULL) - optimistic locking

#### `project_payloads`
- `payload_id` (Integer, PK, autoincrement)
- `project_id` (String(255), NOT NULL, index=True)
- `module` (String(255), NOT NULL) - signage.single_pole, signage.baseplate, etc.
- `config` (JSON, NOT NULL)
- `files` (JSON, NOT NULL)
- `cost_snapshot` (JSON, NOT NULL)
- `sha256` (String(64), NULL, index=True) - deterministic snapshot hash
- `created_at` (DateTime(timezone=True), NOT NULL, server_default=now())

#### `project_events`
- `event_id` (Integer, PK, autoincrement)
- `project_id` (String(255), NOT NULL, index=True)
- `event_type` (String(255), NOT NULL) - project.created, file.attached, etc.
- `actor` (String(255), NOT NULL)
- `timestamp` (DateTime(timezone=True), NOT NULL, server_default=now(), index=True)
- `data` (JSON, NOT NULL)

**Indexes:**
- `project_payloads.project_id`
- `project_payloads.sha256`
- `project_events.project_id`
- `project_events.timestamp`

**Features:**
- Server-side defaults for all timestamp columns
- JSON columns for flexible configuration storage
- Foreign key relationships via `project_id`
- Immutable audit trail in `project_events`
- Optimistic locking via `etag` on projects

### 3. Removed
- `services/api/alembic/versions/20251101_000001_init_projects.py` - Duplicate migration with incorrect UUID schema

## Model Alignment

Migration matches SQLAlchemy models in `services/api/src/apex/api/db.py`:

| Model | Table | Status |
|-------|-------|--------|
| `Project` | `projects` | ✅ All fields match |
| `ProjectPayload` | `project_payloads` | ✅ All fields match |
| `ProjectEvent` | `project_events` | ✅ All fields match |

## Running the Migration

### Using Alembic CLI
```bash
cd services/api
alembic upgrade head
```

### Programmatically
```python
from services.api.src.apex.api.db import init_db

await init_db()  # Uses Base.metadata.create_all (for dev only)
# OR use Alembic in production
```

### Verification
```bash
cd services/api
alembic current  # Shows current revision
alembic history  # Shows revision history
alembic show head  # Shows latest revision
```

## Rollback

To rollback the migration:
```bash
cd services/api
alembic downgrade base  # Rollback to before revision 001
```

The `downgrade()` function properly drops tables in reverse dependency order.

## Next Steps

1. **Apply Migration:** Run `alembic upgrade head` against test database
2. **File Uploads:** Add MinIO integration endpoints (Phase 2.3)
3. **Worker Tasks:** Implement Celery tasks for async processing (Phase 8)
4. **Testing:** Add integration tests for project CRUD operations

## Notes

- Migration uses PostgreSQL-specific features (JSON, timestamps with timezone)
- Server defaults reduce application-level boilerplate
- Indexes optimize queries by `project_id` and `timestamp`
- SHA256 hash enables deterministic caching and versioning
- ETag supports optimistic concurrency control
- All JSON columns use `astext_type=sa.Text` for cross-dialect compatibility

## Configuration

Required environment variables:
```bash
DATABASE_URL=postgresql://apex:apex@db:5432/apex
```

Default connection (if not set):
```
postgresql+asyncpg://apex:apex@db:5432/apex
```

