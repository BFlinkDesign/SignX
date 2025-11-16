# Docker Compose Deployment Guide

Complete guide for deploying with Docker Compose.

## Overview

Docker Compose orchestrates all services:
- **API Service** - FastAPI application
- **Worker Service** - Celery workers
- **Database** - PostgreSQL
- **Cache** - Redis
- **Storage** - MinIO
- **Search** - OpenSearch

## Quick Start

```bash
# Clone repository
git clone <repo-url>
cd calcusign-apex-clone

# Copy environment file
cp .env.example .env

# Edit .env with your configuration

# Start all services
docker compose -f infra/compose.yaml up -d

# Check status
docker compose ps

# View logs
docker compose logs -f api
```

## Service Configuration

### API Service

**Image**: `apex-api:dev`  
**Port**: `8000`  
**Health Check**: `/ready` endpoint

**Environment Variables**:
```yaml
ENV: dev
SERVICE_NAME: api
DATABASE_URL: postgresql://apex:apex@db:5432/apex
REDIS_URL: redis://cache:6379/0
MINIO_URL: http://object:9000
```

**Resources**:
```yaml
deploy:
  resources:
    limits:
      cpus: "1.0"
      memory: "512M"
```

### Worker Service

**Image**: `apex-worker:dev`  
**Port**: None (internal)  
**Health Check**: Celery ping

**Environment Variables**:
```yaml
SERVICE_NAME: worker
REDIS_URL: redis://cache:6379/0
CELERY_BROKER_URL: redis://cache:6379/0
CELERY_RESULT_BACKEND: redis://cache:6379/1
```

### Database Service

**Image**: `postgres:15-alpine`  
**Port**: `5432`  
**Health Check**: `pg_isready`

**Volumes**:
```yaml
volumes:
  - pg_data:/var/lib/postgresql/data
```

**Environment**:
```yaml
POSTGRES_USER: apex
POSTGRES_PASSWORD: apex
POSTGRES_DB: apex
```

### Cache Service

**Image**: `redis:7-alpine`  
**Port**: `6379`  
**Health Check**: `redis-cli ping`

**Command**:
```yaml
command: ["redis-server", "--save", "", "--appendonly", "no"]
```

### Object Storage (MinIO)

**Image**: `minio/minio:latest`  
**Ports**: `9000` (API), `9001` (Console)  
**Health Check**: `/minio/health/live`

**Environment**:
```yaml
MINIO_ROOT_USER: minioadmin
MINIO_ROOT_PASSWORD: minioadmin
```

**Volumes**:
```yaml
volumes:
  - minio_data:/data
```

### Search Service (OpenSearch)

**Image**: `opensearchproject/opensearch:2.12.0`  
**Port**: `9200`  
**Health Check**: Cluster health API

**Environment**:
```yaml
discovery.type: single-node
plugins.security.disabled: "true"
OPENSEARCH_JAVA_OPTS: -Xms512m -Xmx512m
```

## Customization

### Port Mapping

Edit `infra/compose.yaml`:

```yaml
services:
  api:
    ports:
      - "8001:8000"  # Change host port
```

### Resource Limits

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: "1G"
```

### Environment Variables

**Option 1: .env file**
```bash
# .env
APEX_DATABASE_URL=postgresql://user:pass@db:5432/apex
APEX_REDIS_URL=redis://cache:6379/0
```

**Option 2: Compose file**
```yaml
services:
  api:
    environment:
      - APEX_ENV=dev
      - APEX_DATABASE_URL=postgresql://...
```

### Volume Mounts

**Development** (live code reload):
```yaml
services:
  api:
    volumes:
      - ../services/api/src:/app/src
```

**Production** (read-only):
```yaml
services:
  api:
    read_only: true
    tmpfs:
      - /tmp
```

## Health Checks

### Service Health

```bash
# Check all services
docker compose ps

# Check specific service
docker compose ps api

# Health check logs
docker compose exec api curl http://localhost:8000/health
```

### Dependency Health

Services wait for dependencies:

```yaml
depends_on:
  db:
    condition: service_healthy
  cache:
    condition: service_healthy
```

## Logs

### View Logs

```bash
# All services
docker compose logs

# Specific service
docker compose logs api

# Follow logs
docker compose logs -f api

# Last 100 lines
docker compose logs --tail=100 api
```

### Log Format

Logs are structured JSON:

```json
{
  "event": "request",
  "method": "POST",
  "path": "/projects",
  "status": 200,
  "timestamp": "2025-01-01T00:00:00Z"
}
```

## Database Operations

### Run Migrations

```bash
# Apply migrations
docker compose exec api python -m alembic upgrade head

# Check current revision
docker compose exec api python -m alembic current

# Create new migration
docker compose exec api python -m alembic revision --autogenerate -m "description"
```

### Database Backup

```bash
# Backup
docker compose exec db pg_dump -U apex apex > backup.sql

# Restore
docker compose exec -T db psql -U apex apex < backup.sql
```

### Access Database

```bash
# Via docker compose
docker compose exec db psql -U apex apex

# Via psql client
psql postgresql://apex:apex@localhost:5432/apex
```

## Redis Operations

### Access Redis

```bash
# Redis CLI
docker compose exec cache redis-cli

# Check queue depth
docker compose exec cache redis-cli LLEN celery
```

### Clear Cache

```bash
# Flush all (development only)
docker compose exec cache redis-cli FLUSHALL
```

## MinIO Operations

### Access MinIO Console

```bash
# Open in browser
open http://localhost:9001

# Login: minioadmin / minioadmin
```

### MinIO Client

```bash
# Install mc (MinIO client)
# macOS: brew install minio/stable/mc
# Linux: wget https://dl.min.io/client/mc/release/linux-amd64/mc

# Configure
mc alias set local http://localhost:9000 minioadmin minioadmin

# List buckets
mc ls local/

# List files
mc ls local/apex-uploads/
```

## Scaling Services

### Scale API

```bash
# Scale to 3 replicas
docker compose up -d --scale api=3
```

### Scale Workers

```bash
# Scale to 5 workers
docker compose up -d --scale worker=5
```

## Networking

### Service Communication

Services communicate via Docker network:

```yaml
# Service names as hostnames
DATABASE_URL: postgresql://apex:apex@db:5432/apex
REDIS_URL: redis://cache:6379/0
```

### External Access

```bash
# API
http://localhost:8000

# MinIO Console
http://localhost:9001

# OpenSearch
http://localhost:9200
```

## Development vs Production

### Development

```bash
# Use dev compose file
docker compose -f infra/compose.yaml up -d

# Features:
# - Volume mounts for live reload
# - Debug logging
# - Default credentials
```

### Production

```bash
# Use production compose file
docker compose -f docker-compose.prod.yml up -d

# Features:
# - Read-only filesystem
# - Resource limits
# - Health checks
# - Production credentials
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker compose logs api
docker compose logs db

# Check health
docker compose ps

# Restart service
docker compose restart api
```

### Port Conflicts

```bash
# Check port usage
lsof -i :8000

# Change port in compose file
ports:
  - "8001:8000"
```

### Volume Issues

```bash
# Remove volumes
docker compose down -v

# Recreate volumes
docker compose up -d
```

### Network Issues

```bash
# Recreate network
docker compose down
docker network prune
docker compose up -d
```

## Next Steps

- [**Production Deployment**](production.md) - Production setup
- [**Monitoring Guide**](../operations/monitoring.md) - Metrics setup

