# Alembic Migration Usage Guide

## Overview

This project uses Alembic for database schema migrations. The migrations track changes to SQLAlchemy models and provide version control for the database schema.

## Quick Start

### Initial Setup

1. **Check current revision:**
   ```bash
   cd services/api
   alembic current
   ```

2. **View migration history:**
   ```bash
   alembic history
   ```

3. **Apply all pending migrations:**
   ```bash
   alembic upgrade head
   ```

4. **Rollback to previous revision:**
   ```bash
   alembic downgrade -1
   ```

### Creating New Migrations

#### Auto-generate from Models

1. **Generate migration from model changes:**
   ```bash
   alembic revision --autogenerate -m "description of changes"
   ```

2. **Review the generated migration** in `alembic/versions/`

3. **Test the migration:**
   ```bash
   alembic upgrade head  # Apply
   alembic downgrade -1  # Rollback
   alembic upgrade head  # Re-apply
   ```

#### Manual Migration

```bash
alembic revision -m "description of changes"
```

Then edit the generated file to add `upgrade()` and `downgrade()` functions.

## Configuration

### Environment Variables

```bash
# Database connection
DATABASE_URL=postgresql://apex:apex@db:5432/apex
```

### File Structure

```
services/api/
├── alembic/
│   ├── env.py              # Alembic configuration
│   ├── script.py.mako      # Migration template
│   └── versions/           # Migration scripts
│       └── 001_initial_projects_schema.py
├── alembic.ini             # Alembic settings
└── src/apex/api/
    └── db.py               # SQLAlchemy models
```

## Migration Best Practices

### 1. Always Review Auto-Generated Migrations

```bash
alembic revision --autogenerate -m "add column"
# Review the generated file before committing
```

### 2. Test Upgrade and Downgrade

```bash
# Test upgrade
alembic upgrade head

# Test downgrade
alembic downgrade -1

# Verify data integrity
# Re-apply upgrade
alembic upgrade head
```

### 3. Use Descriptive Messages

```bash
# Good
alembic revision -m "add index to projects.created_at"
alembic revision -m "add foreign key from events to projects"

# Bad
alembic revision -m "fix db"
alembic revision -m "changes"
```

### 4. Never Modify Existing Migrations

Once a migration is applied to production, create a new migration to make changes:
```bash
# Don't edit existing migration files
# Instead, create a new one:
alembic revision --autogenerate -m "correct previous migration"
```

## Common Commands

### Status
```bash
alembic current           # Show current revision
alembic history           # Show all revisions
alembic show head         # Show latest revision
alembic heads             # Show all heads
```

### Apply Migrations
```bash
alembic upgrade head      # Apply all pending migrations
alembic upgrade +1        # Apply next migration
alembic upgrade <revision> # Apply to specific revision
```

### Rollback
```bash
alembic downgrade base    # Rollback all migrations
alembic downgrade -1      # Rollback one revision
alembic downgrade <rev>   # Rollback to specific revision
```

### Generate SQL Scripts
```bash
alembic upgrade head --sql > upgrade.sql
alembic downgrade base --sql > downgrade.sql
```

## Integration with Docker Compose

### Development

```yaml
# docker-compose.yml
services:
  api:
    command: |
      sh -c "
        alembic upgrade head &&
        uvicorn src.apex.api.main:app --host 0.0.0.0
      "
```

### Production

Use init containers or separate migration job:
```yaml
services:
  migrations:
    image: apex-api:latest
    command: alembic upgrade head
    depends_on:
      db:
        condition: service_healthy
```

## Troubleshooting

### Migration Conflicts

If multiple developers create migrations:
```bash
alembic branches     # Show branch points
alembic merge -m "merge branches" <rev1> <rev2>
```

### Stale Database

If models and database are out of sync:
```bash
# Backup first!
alembic current
alembic downgrade base
alembic upgrade head
```

### Reset Database (Development Only)

```bash
alembic downgrade base
alembic upgrade head
```

## Security Notes

1. **Never commit DATABASE_URL** with production credentials
2. **Use environment variables** for database connection
3. **Backup before downgrades** in production
4. **Test migrations** in staging before production
5. **Review SQL scripts** for destructive operations

## Related Documentation

- [SQLAlchemy Models](../src/apex/api/db.py)
- [Model Definitions](../src/apex/api/projects/models.py)
- [Migration Summary](../MIGRATION_SUMMARY.md)

## Getting Help

- Alembic Docs: https://alembic.sqlalchemy.org/
- SQLAlchemy Docs: https://docs.sqlalchemy.org/
- Project README: [README.md](../README.md)

