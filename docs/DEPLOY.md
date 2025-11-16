# SignX Studio - IT Deployment Guide

**Production Deployment and Administration Guide**

Version: 1.0.0
Last Updated: 2025-11-01
Audience: IT Administrators, DevOps Engineers, System Administrators

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Production Deployment](#production-deployment)
- [Configuration](#configuration)
- [Security Hardening](#security-hardening)
- [Backup and Recovery](#backup-and-recovery)
- [Monitoring](#monitoring)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)
- [Scaling](#scaling)

---

## Overview

SignX Studio is a containerized FastAPI application with PostgreSQL database, designed for internal deployment on Windows or Linux servers. This guide covers production deployment, security, and operational procedures.

### Technology Stack
- **Application:** FastAPI (Python 3.11)
- **Database:** PostgreSQL 16 with pgvector extension
- **Cache:** Redis 7
- **Container Runtime:** Docker Engine 20.10+
- **Orchestration:** Docker Compose 2.0+

### Deployment Models
1. **Single-Server Deployment** (recommended for <50 users)
2. **Multi-Server Deployment** (for high availability)
3. **Cloud Deployment** (AWS, Azure, GCP)

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                     Load Balancer                       │
│                    (nginx/Traefik)                      │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┴──────────────┐
        │                            │
┌───────▼────────┐          ┌────────▼──────┐
│   FastAPI      │          │   FastAPI     │
│   Instance 1   │          │   Instance 2  │
│   (Port 8000)  │          │   (Port 8001) │
└───────┬────────┘          └────────┬──────┘
        │                            │
        └─────────────┬──────────────┘
                      │
        ┌─────────────┴──────────────┐
        │                            │
┌───────▼────────┐          ┌────────▼──────┐
│  PostgreSQL    │          │     Redis     │
│  (Port 5432)   │          │  (Port 6379)  │
└────────────────┘          └───────────────┘
```

### Network Ports

| Service | Port | Purpose | Expose |
|---------|------|---------|--------|
| FastAPI | 8000 | Main API | Internal |
| PostgreSQL | 5432 | Database | Internal |
| Redis | 6379 | Cache/Queue | Internal |
| Nginx | 80/443 | Reverse Proxy | External |

---

## Prerequisites

### Hardware Requirements

#### Minimum (Development/Testing)
- **CPU:** 2 cores
- **RAM:** 4 GB
- **Storage:** 20 GB SSD
- **Network:** 100 Mbps

#### Recommended (Production)
- **CPU:** 4 cores (8+ for high load)
- **RAM:** 16 GB (32+ for large datasets)
- **Storage:** 100 GB SSD (RAID 10 for database)
- **Network:** 1 Gbps
- **Backup:** Separate disk/NAS for backups

### Software Requirements

- **OS:** Windows Server 2019+, Ubuntu 20.04+, RHEL 8+
- **Docker Engine:** 20.10 or later
- **Docker Compose:** 2.0 or later
- **PowerShell:** 5.1+ (Windows) or PowerShell Core 7+ (Linux)
- **Git:** 2.30+ (optional, for updates)

### Network Requirements

- Outbound HTTPS (443) for Docker image pulls
- Internal network access between containers
- Firewall rules for application ports
- DNS resolution for container hostnames

---

## Production Deployment

### Option 1: Automated Deployment (Windows)

1. **Download the deployment package:**
   ```powershell
   # Copy SignX-Studio folder to C:\Apps\
   cd C:\Apps\SignX-Studio
   ```

2. **Run the installer as Administrator:**
   ```powershell
   .\scripts\install_signx.ps1 -InstallPath "C:\Apps\SignX-Studio" -DataPath "D:\Data\SignX"
   ```

3. **Verify deployment:**
   ```powershell
   docker-compose -f docker-compose.prod.yml ps
   curl http://localhost:8000/health
   ```

### Option 2: Manual Deployment

#### Step 1: Prepare the Environment

```powershell
# Create directory structure
mkdir C:\Apps\SignX-Studio
mkdir D:\Data\SignX\postgres
mkdir D:\Backups\SignX

# Navigate to installation directory
cd C:\Apps\SignX-Studio
```

#### Step 2: Configure Environment Variables

Create `.env` file:

```bash
# Application
APP_VERSION=1.0.0
ENV=production
LOG_LEVEL=info

# Database
POSTGRES_USER=signx_prod
POSTGRES_PASSWORD=<GENERATE_SECURE_PASSWORD>
POSTGRES_DB=signx_studio
POSTGRES_PORT=5432
DB_DATA_PATH=D:/Data/SignX/postgres

# Redis
REDIS_PASSWORD=<GENERATE_SECURE_PASSWORD>
REDIS_PORT=6379

# Security
SECRET_KEY=<GENERATE_64_CHAR_KEY>
CORS_ALLOW_ORIGINS=https://signx.yourcompany.com
ALLOWED_HOSTS=signx.yourcompany.com,localhost

# API
API_PORT=8000
RATE_LIMIT_PER_MIN=120

# Monitoring (optional)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
SENTRY_TRACES_SAMPLE_RATE=0.1
```

**Generate secure passwords:**
```powershell
# Generate random password
Add-Type -AssemblyName System.Web
[System.Web.Security.Membership]::GeneratePassword(32, 8)
```

#### Step 3: Build and Start Services

```powershell
# Build Docker images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Verify services are running
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

#### Step 4: Run Database Migrations

```powershell
# Apply database schema
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Verify migration
docker-compose -f docker-compose.prod.yml exec api alembic current
```

#### Step 5: Verify Deployment

```powershell
# Health check
curl http://localhost:8000/health

# API documentation
Start-Process "http://localhost:8000/docs"

# Test calculation endpoint
curl http://localhost:8000/api/v1/calculations/health
```

---

## Configuration

### Environment Variables Reference

#### Application Settings
```bash
ENV=production                    # Environment: production, staging, dev
SERVICE_NAME=api                  # Service identifier
APP_VERSION=1.0.0                # Application version
LOG_LEVEL=info                   # Logging: debug, info, warning, error
```

#### Database Settings
```bash
DATABASE_URL=postgresql://user:pass@host:5432/db
POSTGRES_USER=signx              # Database username
POSTGRES_PASSWORD=***            # Database password (required)
POSTGRES_DB=signx_studio         # Database name
POSTGRES_PORT=5432               # Database port
```

#### Redis Settings
```bash
REDIS_URL=redis://:pass@host:6379/0
REDIS_PASSWORD=***               # Redis password (required)
REDIS_PORT=6379                  # Redis port
```

#### Security Settings
```bash
SECRET_KEY=***                   # JWT signing key (64+ chars)
CORS_ALLOW_ORIGINS=https://app.example.com
ALLOWED_HOSTS=example.com,www.example.com
RATE_LIMIT_PER_MIN=120          # API rate limit per client
```

#### Resource Limits

Edit `docker-compose.prod.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'          # Maximum CPU cores
      memory: 2G           # Maximum memory
    reservations:
      cpus: '1.0'          # Guaranteed CPU
      memory: 512M         # Guaranteed memory
```

---

## Security Hardening

### 1. Container Security

#### Enable Read-Only Root Filesystem
```yaml
services:
  api:
    read_only: true
    tmpfs:
      - /tmp:size=100M,mode=1777
```

#### Drop Unnecessary Capabilities
```yaml
services:
  api:
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
```

#### Use Non-Root User
Already configured in Dockerfile (UID 1000).

### 2. Network Security

#### Internal Network Isolation
```yaml
networks:
  internal:
    driver: bridge
    internal: true  # No external access

services:
  db:
    networks:
      - internal
```

#### TLS/SSL Configuration

Use nginx as reverse proxy:

```nginx
server {
    listen 443 ssl http2;
    server_name signx.yourcompany.com;

    ssl_certificate /etc/ssl/certs/signx.crt;
    ssl_certificate_key /etc/ssl/private/signx.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Database Security

#### Enable SSL for PostgreSQL
```yaml
services:
  db:
    command:
      - postgres
      - -c
      - ssl=on
      - -c
      - ssl_cert_file=/etc/ssl/certs/server.crt
      - -c
      - ssl_key_file=/etc/ssl/private/server.key
```

#### Restrict Access
```bash
# PostgreSQL pg_hba.conf
host    signx_studio    signx    172.20.0.0/16    scram-sha-256
```

### 4. Secrets Management

#### Use Docker Secrets
```yaml
secrets:
  db_password:
    file: ./secrets/db_password.txt

services:
  api:
    secrets:
      - db_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
```

#### Environment File Permissions
```powershell
# Windows
icacls .env /inheritance:r /grant:r "Administrators:(F)"

# Linux
chmod 600 .env
```

---

## Backup and Recovery

### Automated Backup Setup

#### Schedule Daily Backups (Windows Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task: "SignX Database Backup"
3. Trigger: Daily at 2:00 AM
4. Action: Start a program
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File C:\Apps\SignX-Studio\scripts\backup_database.ps1`

#### Backup Script Configuration

Edit `scripts/backup_database.ps1`:
```powershell
$BackupPath = "D:\Backups\SignX"
$RetentionDays = 30
$Compress = $true
$Verify = $true
```

### Manual Backup

```powershell
# Create immediate backup
.\scripts\backup_database.ps1

# Verify backup
ls D:\Backups\SignX
```

### Restore from Backup

#### Step 1: Stop the Application
```powershell
docker-compose -f docker-compose.prod.yml down
```

#### Step 2: Restore Database
```powershell
# Start only the database
docker-compose -f docker-compose.prod.yml up -d db

# Restore from backup
$backupFile = "D:\Backups\SignX\signx_backup_20251101_120000.sql.gz"

# Decompress if needed
gzip -d $backupFile

# Restore
docker exec -i signx-db psql -U signx -d signx_studio < signx_backup_20251101_120000.sql
```

#### Step 3: Restart Services
```powershell
docker-compose -f docker-compose.prod.yml up -d
```

### Backup Best Practices

1. **3-2-1 Rule:** 3 copies, 2 different media, 1 offsite
2. **Test Restores:** Quarterly restore tests
3. **Monitor Backup Size:** Alert on unusual size changes
4. **Encrypt Backups:** Use BitLocker or similar
5. **Document Recovery:** Maintain recovery procedures

---

## Monitoring

### Health Checks

#### Application Health
```powershell
# Basic health
curl http://localhost:8000/health

# Detailed status
curl http://localhost:8000/ready
```

#### Service Health
```powershell
# All services
docker-compose -f docker-compose.prod.yml ps

# Specific service
docker-compose -f docker-compose.prod.yml ps api
```

### Log Management

#### View Logs
```powershell
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f api

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 api
```

#### Export Logs
```powershell
# Export to file
docker-compose -f docker-compose.prod.yml logs > signx_logs_$(Get-Date -Format 'yyyyMMdd').txt
```

### Performance Monitoring

#### Container Stats
```powershell
# Real-time stats
docker stats

# Once
docker stats --no-stream
```

#### Database Monitoring
```powershell
# Connect to database
docker exec -it signx-db psql -U signx -d signx_studio

# Check connections
SELECT count(*) FROM pg_stat_activity;

# Table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

# Index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan;
```

### Alerting

#### Set Up Email Alerts (PowerShell)

```powershell
# Check service health and send email if down
$status = docker-compose -f docker-compose.prod.yml ps -q api
if (-not $status) {
    Send-MailMessage -To "it@company.com" `
                     -From "signx@company.com" `
                     -Subject "SignX Studio API Down" `
                     -Body "SignX Studio API is not responding" `
                     -SmtpServer "smtp.company.com"
}
```

---

## Maintenance

### Regular Maintenance Tasks

#### Weekly
- Review application logs for errors
- Check disk space
- Verify backups are running
- Review security logs

#### Monthly
- Update Docker images
- Review and optimize database
- Test backup restoration
- Review user access

#### Quarterly
- Security audit
- Performance optimization
- Capacity planning review
- Disaster recovery drill

### Updates and Upgrades

#### Update Docker Images

```powershell
# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Restart with new images
docker-compose -f docker-compose.prod.yml up -d

# Remove old images
docker image prune -a
```

#### Update Application

```powershell
# Backup database first
.\scripts\backup_database.ps1

# Stop services
docker-compose -f docker-compose.prod.yml down

# Update files
# Copy new version files

# Rebuild
docker-compose -f docker-compose.prod.yml build

# Run migrations
docker-compose -f docker-compose.prod.yml up -d db
docker-compose -f docker-compose.prod.yml run --rm api alembic upgrade head

# Start all services
docker-compose -f docker-compose.prod.yml up -d
```

### Database Maintenance

#### Vacuum and Analyze
```powershell
# Connect to database
docker exec -it signx-db psql -U signx -d signx_studio

# Run vacuum
VACUUM ANALYZE;

# Check bloat
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

#### Reindex
```sql
REINDEX DATABASE signx_studio;
```

---

## Troubleshooting

### Service Won't Start

#### Check Docker
```powershell
docker ps
docker-compose -f docker-compose.prod.yml ps
```

#### Check Logs
```powershell
docker-compose -f docker-compose.prod.yml logs api
docker-compose -f docker-compose.prod.yml logs db
```

#### Common Issues

**Port Conflict:**
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process
taskkill /PID <PID> /F
```

**Database Connection Failed:**
```powershell
# Check database is running
docker-compose -f docker-compose.prod.yml ps db

# Check database logs
docker-compose -f docker-compose.prod.yml logs db

# Restart database
docker-compose -f docker-compose.prod.yml restart db
```

**Out of Memory:**
```powershell
# Increase Docker memory limit in Docker Desktop settings
# Or reduce resource limits in docker-compose.prod.yml
```

### Performance Issues

#### High CPU Usage
```powershell
# Check container stats
docker stats

# Review API logs for slow queries
docker-compose -f docker-compose.prod.yml logs api | Select-String "slow"
```

#### Slow Database Queries
```sql
-- Enable query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;

-- View slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

### Data Issues

#### Inconsistent Data
```powershell
# Run data validation
docker-compose -f docker-compose.prod.yml exec api python -m apex.api.scripts.validate_data

# Check referential integrity
docker exec -it signx-db psql -U signx -d signx_studio -c "
  SELECT conname, conrelid::regclass AS table_name
  FROM pg_constraint
  WHERE contype = 'f'
  ORDER BY conrelid::regclass::text;
"
```

---

## Scaling

### Horizontal Scaling

#### Add API Instances

Edit `docker-compose.prod.yml`:
```yaml
services:
  api:
    deploy:
      replicas: 3  # Run 3 instances
```

#### Load Balancer Configuration

Use nginx upstream:
```nginx
upstream signx_api {
    least_conn;
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    listen 80;
    location / {
        proxy_pass http://signx_api;
    }
}
```

### Vertical Scaling

#### Increase Resources

```yaml
deploy:
  resources:
    limits:
      cpus: '8.0'
      memory: 8G
```

#### Database Tuning

```yaml
services:
  db:
    command:
      - postgres
      - -c
      - shared_buffers=2GB
      - -c
      - effective_cache_size=6GB
      - -c
      - work_mem=64MB
```

---

## Support and Resources

### Documentation
- Installation Guide: `docs/INSTALL.md`
- API Documentation: http://localhost:8000/docs
- GitHub: [Repository URL]

### Monitoring Dashboard
- Grafana: http://localhost:3001 (admin/admin)
- PostgreSQL Metrics: http://localhost:9187/metrics

### Logs Location
- Application: `docker-compose logs`
- Database: `D:\Data\SignX\postgres\log`
- Backups: `D:\Backups\SignX`

---

**For end-user installation instructions, see [INSTALL.md](INSTALL.md)**
