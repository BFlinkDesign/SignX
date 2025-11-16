# SignX-Studio Production Deployment Guide

**Version:** 1.0
**Last Updated:** 2025-11-02
**Target Environment:** Production (Linux/Docker)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Database Setup](#database-setup)
4. [Service Deployment](#service-deployment)
5. [Data Seeding](#data-seeding)
6. [Health Checks](#health-checks)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Docker** >= 24.0
- **Docker Compose** >= 2.20
- **PostgreSQL** >= 15 (managed or self-hosted)
- **Redis** >= 7.0 (for caching and Celery queue)
- **Python** >= 3.11 (for database seeding scripts)

### Required Access

- PostgreSQL superuser or owner privileges
- Redis connection string
- (Optional) Supabase project for authentication
- (Optional) MinIO/S3 bucket for file storage

### Hardware Requirements

**Minimum (Development/Staging):**
- 2 CPU cores
- 4GB RAM
- 20GB disk

**Recommended (Production):**
- 4 CPU cores
- 8GB RAM
- 100GB disk (SSD preferred)

---

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/SignX-Studio.git
cd SignX-Studio
```

### 2. Create Environment File

Create `.env` file in project root:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/signx_studio
DB_USER=signx_user
DB_PASSWORD=secure_password_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=signx_studio

# Redis
REDIS_URL=redis://localhost:6379/0

# API Configuration
APEX_API_PORT=8000
APEX_API_HOST=0.0.0.0
APEX_LOG_LEVEL=INFO

# Authentication (Optional - Supabase)
APEX_SUPABASE_URL=https://your-project.supabase.co
APEX_SUPABASE_KEY=your_anon_key
APEX_SUPABASE_SERVICE_KEY=your_service_role_key

# Object Storage (Optional - MinIO/S3)
MINIO_URL=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=signx-files

# Worker Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Security
SECRET_KEY=generate_secure_random_key_here_at_least_32_characters
JWT_SECRET=another_secure_random_key_for_jwt_tokens

# Rate Limiting
SIGNCALC_RATE_LIMIT=100/minute

# CORS (if needed)
APEX_CORS_ORIGINS=["https://yourdomain.com"]
```

**Security Note:** Generate secure random keys:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Required Data Files

Download AISC Shapes Database v16.0:
- Visit: https://www.aisc.org/resources/shapes-database/
- Download CSV file
- Place at: `data/aisc-shapes-v16.csv`

---

## Database Setup

### 1. Create Database

```bash
# Using psql
psql -U postgres -h localhost

postgres=# CREATE DATABASE signx_studio;
postgres=# CREATE USER signx_user WITH PASSWORD 'secure_password';
postgres=# GRANT ALL PRIVILEGES ON DATABASE signx_studio TO signx_user;
postgres=# \q
```

### 2. Install Extensions

```bash
psql -U signx_user -d signx_studio

signx_studio=# CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
signx_studio=# CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For full-text search
signx_studio=# \q
```

### 3. Run Database Migrations

```bash
cd services/api

# Install dependencies
pip install -r requirements.txt

# Run migrations
export DATABASE_URL="postgresql://signx_user:password@localhost:5432/signx_studio"
alembic upgrade head

# Verify migrations
alembic current
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Running upgrade -> rev_xxxx, initial schema
INFO  [alembic.runtime.migration] Running upgrade rev_xxxx -> rev_yyyy, add indexes
Current revision(s) for postgresql://signx_user:***@localhost:5432/signx_studio:
rev_yyyy (head)
```

### 4. Seed Default Data

```bash
# Seed calibration constants and pricing
python scripts/seed_defaults.py

# Seed AISC steel sections
export AISC_CSV_PATH="data/aisc-shapes-v16.csv"
python scripts/seed_aisc_sections.py
```

**Expected Output:**
```
Loading AISC CSV: data/aisc-shapes-v16.csv
Loaded 1247 sections
✓ Inserted 1247 pole sections into database

✓ Seeded 5 calibration constants
✓ Seeded 4 pricing items
✓ All defaults seeded successfully
```

---

## Service Deployment

### Option A: Docker Compose (Recommended)

#### 1. Build Images

```bash
cd infra
docker-compose build
```

#### 2. Start Services

```bash
docker-compose up -d
```

#### 3. Verify Services

```bash
docker-compose ps

# Expected:
# NAME                SERVICE   STATUS        PORTS
# apex-api-1          api       Up           0.0.0.0:8000->8000/tcp
# apex-worker-1       worker    Up
# postgres-1          postgres  Up           0.0.0.0:5432->5432/tcp
# redis-1             redis     Up           0.0.0.0:6379->6379/tcp
```

#### 4. View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
```

### Option B: Manual Deployment

#### 1. Install Dependencies

```bash
cd services/api
pip install -r requirements.txt
```

#### 2. Start API Server

```bash
# Production with uvicorn
uvicorn apex.api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --loop uvloop \
  --log-level info

# Or with gunicorn (recommended for production)
gunicorn apex.api.main:app \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 120 \
  --keep-alive 5 \
  --log-level info \
  --access-logfile - \
  --error-logfile -
```

#### 3. Start Celery Worker

```bash
cd services/worker
celery -A apex.worker.tasks worker \
  --loglevel=info \
  --concurrency=4 \
  --max-tasks-per-child=1000
```

---

## Health Checks

### 1. API Health

```bash
curl http://localhost:8000/health

# Expected:
# {
#   "ok": true,
#   "timestamp": "2025-11-02T12:00:00Z",
#   "version": "1.0.0"
# }
```

### 2. Readiness Check

```bash
curl http://localhost:8000/ready

# Expected (all dependencies healthy):
# {
#   "ok": true,
#   "database": "connected",
#   "redis": "connected",
#   "timestamp": "2025-11-02T12:00:00Z"
# }
```

### 3. API Documentation

Open browser to: http://localhost:8000/docs

- Verify Swagger UI loads
- Test /api/signcalc/solve/single-pole/ endpoint
- Test /api/cad/export/foundation endpoint (CAD export)
- Check rate limiting (100 req/min)

### 4. Database Connection Test

```bash
psql -U signx_user -d signx_studio -c "SELECT COUNT(*) FROM pole_sections;"

# Expected: ~1247 rows (AISC sections)
```

---

## Monitoring

### 1. Prometheus Metrics

Available at: http://localhost:8000/metrics

**Key Metrics:**
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `database_connections_active` - Active DB connections
- `celery_tasks_total` - Total Celery tasks

### 2. Structured Logging

Logs are in JSON format for easy parsing:

```json
{
  "timestamp": "2025-11-02T12:00:00.000Z",
  "level": "info",
  "event": "wind.velocity_pressure_calculated",
  "qz_psf": 24.46,
  "wind_speed_mph": 115,
  "exposure": "C"
}
```

### 3. Grafana Dashboard (Optional)

```bash
# Start Grafana
docker-compose --profile monitoring up -d

# Access: http://localhost:3000
# Login: admin/admin
```

Import dashboard from: `infra/grafana/dashboards/signx-studio.json`

---

## Data Seeding

### Required Seeds (Production)

1. **Calibration Constants**
   ```bash
   python scripts/seed_defaults.py
   ```
   - K_footing = 1.0
   - phi_bending = 0.9
   - Fexx_weld = 70.0 ksi
   - load_factor_wind = 1.6
   - soil_bearing_default_psf = 3000

2. **AISC Steel Sections**
   ```bash
   export AISC_CSV_PATH="data/aisc-shapes-v16.csv"
   python scripts/seed_aisc_sections.py
   ```
   - ~1247 HSS, Pipe, W-shape sections
   - Includes: designation, Sx, Ix, area, weight

3. **Pricing Configuration**
   ```bash
   # Already included in seed_defaults.py
   ```
   - Engineering ≤25 ft: $200
   - Engineering >25 ft: $300
   - Calc packet: $35
   - Hard copies: $30

### Optional Seeds

**Test Projects:**
```bash
python scripts/seed_test_projects.py  # For staging/testing only
```

---

## Troubleshooting

### Issue: Database Connection Refused

**Symptoms:**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server
```

**Solutions:**
1. Verify PostgreSQL is running: `systemctl status postgresql`
2. Check DATABASE_URL in .env matches PostgreSQL config
3. Verify user has connection privileges:
   ```sql
   SELECT * FROM pg_user WHERE usename = 'signx_user';
   ```
4. Check PostgreSQL logs: `/var/log/postgresql/postgresql-15-main.log`

### Issue: Migrations Fail

**Symptoms:**
```
alembic.util.exc.CommandError: Can't locate revision identified by 'xxxxx'
```

**Solutions:**
1. Verify alembic version table exists:
   ```sql
   SELECT * FROM alembic_version;
   ```
2. Reset to initial state (DESTRUCTIVE - only for development):
   ```bash
   alembic downgrade base
   alembic upgrade head
   ```
3. Check migration files in `services/api/alembic/versions/`

### Issue: AISC Section Not Found

**Symptoms:**
```
AISCDatabaseError: AISC section 'HSS8X8X1/4' not found in database
```

**Solutions:**
1. Verify seed ran successfully: `SELECT COUNT(*) FROM pole_sections;`
2. Check designation format (exact case matters): "HSS8X8X1/4" not "8x8x1/4"
3. Re-run seed script:
   ```bash
   python scripts/seed_aisc_sections.py
   ```
4. Verify CSV file downloaded: `ls -lh data/aisc-shapes-v16.csv`

### Issue: Rate Limit Errors (429)

**Symptoms:**
```
HTTP 429: Too Many Requests
```

**Solutions:**
1. This is expected behavior (100 req/min limit)
2. Increase limit in .env:
   ```bash
   SIGNCALC_RATE_LIMIT=200/minute
   ```
3. Restart API service
4. For load testing, disable temporarily (not recommended for production)

### Issue: API Slow Response

**Symptoms:**
- Requests taking > 5 seconds
- Timeout errors

**Solutions:**
1. Check database query performance:
   ```sql
   SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
   ```
2. Verify N+1 query fix (selectinload) is active
3. Check cache hit rate: inspect Redis with `redis-cli INFO stats`
4. Scale up workers:
   ```bash
   docker-compose up -d --scale worker=4
   ```

### Issue: Out of Memory

**Symptoms:**
```
docker: Error response from daemon: OCI runtime create failed: out of memory
```

**Solutions:**
1. Increase Docker memory limit: Docker Desktop → Settings → Resources
2. Reduce worker concurrency:
   ```bash
   celery -A apex.worker.tasks worker --concurrency=2
   ```
3. Scale down services if running everything locally

---

## Security Checklist

**Before Production Deployment:**

- [ ] Change all default passwords in .env
- [ ] Generate secure random SECRET_KEY (32+ characters)
- [ ] Enable HTTPS/TLS (reverse proxy with nginx/Caddy)
- [ ] Set CORS_ORIGINS to production domain only
- [ ] Enable database SSL connection
- [ ] Set up firewall rules (allow only 443, deny 8000 externally)
- [ ] Configure rate limiting (default 100/min is conservative)
- [ ] Enable Supabase RLS policies if using Supabase
- [ ] Set up backup strategy (pg_dump daily + offsite)
- [ ] Enable audit logging for all API requests
- [ ] Run security scan: `bandit -r services/api/src/`
- [ ] Run dependency check: `safety check`

---

## Backup & Recovery

### Database Backup

**Daily Backup (Cron):**
```bash
#!/bin/bash
# /etc/cron.daily/signx-backup

export PGPASSWORD="secure_password"
pg_dump -h localhost -U signx_user signx_studio | gzip > /backup/signx_$(date +\%Y\%m\%d).sql.gz

# Keep last 30 days
find /backup/ -name "signx_*.sql.gz" -mtime +30 -delete
```

**Restore from Backup:**
```bash
gunzip < /backup/signx_20251102.sql.gz | psql -h localhost -U signx_user signx_studio
```

### Application State Backup

**Redis Persistence:**
```bash
# Configure Redis AOF (Append-Only File)
# In redis.conf:
appendonly yes
appendfsync everysec
```

---

## Scaling Guide

### Horizontal Scaling

**API Service:**
```bash
# Docker Compose
docker-compose up -d --scale api=4

# Or load balancer (nginx)
upstream signx_api {
    server api1:8000;
    server api2:8000;
    server api3:8000;
    server api4:8000;
}
```

**Worker Service:**
```bash
docker-compose up -d --scale worker=8
```

### Database Scaling

**Read Replicas:**
- Configure PostgreSQL streaming replication
- Route read queries to replicas
- Keep writes on primary

**Connection Pooling:**
- Use PgBouncer for connection pooling
- Recommended: 20-50 connections per API instance

---

## Support

**Documentation:**
- API Docs: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc
- GitHub: https://github.com/your-org/SignX-Studio

**Logs:**
```bash
# API logs
docker-compose logs -f api

# Worker logs
docker-compose logs -f worker

# Database logs
tail -f /var/log/postgresql/postgresql-15-main.log
```

---

**Deployment Checklist:**

- [ ] Environment file configured (.env)
- [ ] Database created and migrated
- [ ] AISC data seeded (~1247 sections)
- [ ] Default calibration constants seeded
- [ ] Services started (docker-compose up)
- [ ] Health check passing (/health, /ready)
- [ ] API docs accessible (/docs)
- [ ] Test calculation endpoint works
- [ ] Rate limiting verified (100 req/min)
- [ ] Monitoring configured (Prometheus/Grafana)
- [ ] Backup script configured (cron)
- [ ] Security hardened (SSL, firewalls, secrets)

**New Features:**
- ✅ CAD Export (DXF, DWG, AI, CDR) for fabrication drawings
- ✅ Rebar schedule generation with material takeoff
- ✅ Anchor bolt layout detailing
- ✅ AIA standard layer compliance

**Status:** Ready for production deployment ✅

---

**Document Version:** 1.0
**Last Updated:** 2025-11-02
**Maintained By:** DevOps Team
