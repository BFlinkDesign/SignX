# APEX Database Migrations

## Overview

This directory contains Alembic migrations for the APEX CalcuSign database schema. The database follows a deterministic, versioned schema with audit trails and material catalogs.

## Migration History

1. **001_initial_projects_schema**: Core project tables (projects, project_payloads, project_events)
2. **002_add_enums_and_indexes**: ENUM constraints and performance indexes
3. **003_add_calib_pricing_tables**: Calibration constants, pricing configs, material catalog, code references
4. **004_seed_calib_pricing_data**: Seed data for engineering constants and pricing

## Schema Summary

### Core Tables

#### `projects`
Project metadata with state machine (`draft` → `estimating` → `submitted` → `accepted/rejected`)
- **Primary Key**: `project_id` (STRING)
- **Constraints**: Status CHECK constraint
- **Indexes**: None (PK only)

#### `project_payloads`
Design payload snapshots with deterministic SHA256 hashing
- **Primary Key**: `payload_id` (AUTOINCREMENT)
- **Foreign Key**: `project_id` → `projects.project_id`
- **Indexes**: 
  - `project_id` (single)
  - `sha256` (single)
  - `(project_id, module, created_at DESC)` (composite) - **Critical for history queries**

#### `project_events`
Immutable audit log
- **Primary Key**: `event_id` (AUTOINCREMENT)
- **Foreign Key**: `project_id` → `projects.project_id`
- **Indexes**:
  - `project_id` (single)
  - `timestamp` (single)
  - `event_type` (single)

### Engineering Tables

#### `calibration_constants`
Versioned engineering constants (K factors, material properties)
- **Primary Key**: `constant_id` (AUTOINCREMENT)
- **Unique**: `(name, version)`
- **Indexes**: `name`, `version`

#### `pricing_configs`
Versioned pricing for add-ons and services
- **Primary Key**: `price_id` (AUTOINCREMENT)
- **Unique**: `(item_code, version)`
- **Indexes**: `(effective_from, effective_to)` for date range queries

#### `material_catalog`
AISC/ASTM material properties and dimensions
- **Primary Key**: `material_id` (STRING, e.g., "AISC_99_A36")
- **Indexes**: `(standard, grade)`, `shape`

#### `code_references`
Engineering code references for traceability
- **Primary Key**: `ref_id` (STRING)
- **Indexes**: `(code, section)`

## Performance Targets

All queries should complete in **<50ms** at typical load (1000 projects, 10k payloads):

- ✅ `projects` lookup: PK scan → **<1ms**
- ✅ `project_payloads` history: Composite index → **<10ms**
- ✅ `project_events` audit: Indexed timestamp → **<20ms**
- ✅ `material_catalog` lookup: PK scan → **<1ms**

## Running Migrations

### Development

```bash
cd services/api
alembic upgrade head
```

### Production

```bash
# Verify current state
alembic current

# Show pending migrations
alembic heads

# Apply migrations
alembic upgrade head

# Rollback on error
alembic downgrade -1
```

## Migration Safety

All migrations include:
- ✅ **Idempotency checks** (IF NOT EXISTS, DO NOTHING)
- ✅ **Constraints** (CHECK, FOREIGN KEY)
- ✅ **Indexes** for query performance
- ✅ **Seed data** with ON CONFLICT guards
- ✅ **Downgrade path** for rollback

## pgvector Support

The database uses `pgvector/pgvector:pg16` image. To add vector search in the future:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE material_catalog ADD COLUMN embedding vector(1536);
CREATE INDEX ON material_catalog USING ivfflat (embedding vector_cosine_ops);
```

## Coordination with Agents

- **Agent 2 (Queries)**: Uses these tables for CRUD operations
- **Agent 5 (Integrations)**: Pulls from `material_catalog` and `calibration_constants`
- **Agent 1 (Orchestration)**: Relies on `project_events` for audit trail

## Next Steps

1. Add GIN indexes for JSONB columns if JSON queries become frequent
2. Add `updated_at` triggers for automatic timestamp updates
3. Partition `project_events` by year if table grows >1M rows
4. Add `pg_trgm` extension for fuzzy text search on `projects.name`

