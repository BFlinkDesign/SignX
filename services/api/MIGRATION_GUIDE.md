# Migration Guide

## Quick Start

```bash
# 1. Start database
docker compose -f ../../infra/compose.yaml up -d db

# 2. Run migrations
cd services/api
alembic upgrade head

# 3. Verify
alembic current
# Should show: 004 (head)

# 4. Test DDL
python migrations/test_ddl.py
```

## Migration Commands

```bash
# View current version
alembic current

# View history
alembic history

# Upgrade to latest
alembic upgrade head

# Upgrade to specific version
alembic upgrade 002

# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade 001

# Create new migration
alembic revision --autogenerate -m "description"

# Create manual migration
alembic revision -m "description"
```

## Schema State

After running all migrations:

```sql
-- Core tables
\dt projects
\dt project_payloads  
\dt project_events

-- Engineering tables
\dt calibration_constants
\dt pricing_configs
\dt material_catalog
\dt code_references

-- Check indexes
\d+ projects
\d+ project_payloads
\d+ project_events

-- Verify constraints
SELECT conname, contype FROM pg_constraint WHERE conrelid = 'projects'::regclass;
```

## Seed Data Verification

```sql
-- Check calibration constants
SELECT name, version, value, unit FROM calibration_constants;

-- Check pricing
SELECT item_code, version, price_usd FROM pricing_configs;

-- Check materials
SELECT material_id, standard, grade, shape FROM material_catalog LIMIT 5;

-- Check code refs
SELECT ref_id, code, section, title FROM code_references LIMIT 5;
```

## Performance Testing

```bash
# Run performance validation
python migrations/test_ddl.py

# Expected output:
# ✅ All tables created
# ✅ Constraints enforced
# ✅ Indexes created: XX found
# ✅ Seed data loaded
# ✅ PK lookup: <1ms
# ✅ Composite index query: <10ms
# ✅ All DDL tests passed!
```

## Troubleshooting

### Migration fails with "relation already exists"
```bash
# Rebuild from scratch
alembic downgrade base
alembic upgrade head
```

### Index already exists error
The migration uses `if_not_exists=True` but some Postgres versions don't support it in `CREATE INDEX`. Use manual SQL if needed:

```sql
CREATE INDEX IF NOT EXISTS ix_name ON table_name (columns);
```

### Seed data duplicates
Seed migrations use `ON CONFLICT DO NOTHING`, so re-running is safe.

### Performance degradation
Check if indexes are being used:

```sql
EXPLAIN ANALYZE SELECT * FROM project_payloads 
WHERE project_id = 'x' AND module = 'y' 
ORDER BY created_at DESC LIMIT 10;
```

Should show: `Index Scan using ix_project_payloads_project_module_created`

