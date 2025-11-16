# Installation Guide

Detailed installation instructions for SIGN X Studio Clone.

## System Requirements

### Minimum

- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 10 GB free
- **OS**: Linux, macOS, or Windows (with WSL2)

### Recommended

- **CPU**: 4+ cores
- **RAM**: 8+ GB
- **Disk**: 50+ GB free (for logs, artifacts)

## Prerequisites

### Required Software

1. **Docker** (20.10+)
   ```bash
   # Install Docker Desktop
   # macOS: https://docs.docker.com/desktop/mac/install/
   # Linux: https://docs.docker.com/engine/install/
   # Windows: https://docs.docker.com/desktop/windows/install/
   ```

2. **Docker Compose** (2.0+)
   ```bash
   # Usually included with Docker Desktop
   docker compose version
   ```

3. **Python** (3.11) - For local development
   ```bash
   python --version  # Should be 3.11.x
   ```

4. **Git**
   ```bash
   git --version
   ```

### Optional Software

- **psql** - PostgreSQL client
- **redis-cli** - Redis client
- **MinIO Client (mc)** - MinIO management
- **kubectl** - Kubernetes (if using K8s)

## Installation Methods

### Method 1: Docker Compose (Recommended)

**Best for**: Development and production

#### Step 1: Clone Repository

```bash
git clone <repository-url>
cd calcusign-apex-clone
```

#### Step 2: Create Environment File

```bash
cp .env.example .env
```

Edit `.env`:
```bash
# Database
APEX_DATABASE_URL=postgresql://apex:apex@db:5432/apex

# Cache
APEX_REDIS_URL=redis://cache:6379/0

# Storage
APEX_MINIO_URL=http://object:9000
APEX_MINIO_ACCESS_KEY=minioadmin
APEX_MINIO_SECRET_KEY=minioadmin
APEX_MINIO_BUCKET=apex-uploads
```

#### Step 3: Start Services

```bash
docker compose -f infra/compose.yaml up -d
```

#### Step 4: Run Migrations

```bash
docker compose exec api python -m alembic upgrade head
```

#### Step 5: Verify Installation

```bash
curl http://localhost:8000/health
```

### Method 2: Local Development

**Best for**: Active development

#### Step 1: Clone Repository

```bash
git clone <repository-url>
cd calcusign-apex-clone
```

#### Step 2: Setup Python Environment

```bash
cd services/api
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

#### Step 3: Start Dependencies

```bash
# Start database, Redis, MinIO
docker compose -f infra/compose.yaml up -d db cache object search
```

#### Step 4: Configure Environment

```bash
export APEX_DATABASE_URL=postgresql://apex:apex@localhost:5432/apex
export APEX_REDIS_URL=redis://localhost:6379/0
export APEX_MINIO_URL=http://localhost:9000
```

#### Step 5: Run Migrations

```bash
cd services/api
alembic upgrade head
```

#### Step 6: Start API

```bash
uvicorn apex.api.main:app --reload --port 8000
```

### Method 3: Kubernetes

**Best for**: Production deployments

See [Kubernetes Deployment Guide](../deployment/kubernetes.md)

## Database Setup

### PostgreSQL Installation

#### Using Docker

```bash
docker run -d \
  --name postgres \
  -e POSTGRES_USER=apex \
  -e POSTGRES_PASSWORD=apex \
  -e POSTGRES_DB=apex \
  -p 5432:5432 \
  postgres:15-alpine
```

#### Manual Installation

**macOS:**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Linux:**
```bash
sudo apt-get install postgresql-15
sudo systemctl start postgresql
```

**Create Database:**
```bash
createdb apex
```

### Run Migrations

```bash
cd services/api
alembic upgrade head
```

### Seed Initial Data

```bash
python scripts/seed_defaults.py
```

## Redis Setup

### Using Docker

```bash
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:7-alpine
```

### Manual Installation

**macOS:**
```bash
brew install redis
brew services start redis
```

**Linux:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

## MinIO Setup

### Using Docker

```bash
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
```

### Access Console

Open http://localhost:9001
- Username: `minioadmin`
- Password: `minioadmin`

### Create Bucket

```bash
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/apex-uploads
```

## OpenSearch Setup (Optional)

### Using Docker

```bash
docker run -d \
  --name opensearch \
  -p 9200:9200 \
  -e discovery.type=single-node \
  -e plugins.security.disabled=true \
  opensearchproject/opensearch:2.12.0
```

### Verify

```bash
curl http://localhost:9200
```

## Development Setup

### Install Dependencies

```bash
# API service
cd services/api
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If exists

# Worker service
cd ../worker
pip install -r requirements.txt
```

### Setup Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

### Run Tests

```bash
# All tests
pytest

# Specific suite
pytest tests/unit/
pytest tests/service/
pytest tests/e2e/
```

## Verification

### Health Checks

```bash
# API health
curl http://localhost:8000/health | jq

# Readiness
curl http://localhost:8000/ready | jq

# Metrics
curl http://localhost:8000/metrics
```

### Service Status

```bash
# Docker Compose
docker compose ps

# Kubernetes
kubectl get pods -n apex
```

### Test API

```bash
# Create project
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{"account_id":"test","name":"Test","created_by":"test@example.com"}' | jq
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process or change port
```

### Database Connection Failed

```bash
# Check database is running
docker compose ps db

# Test connection
psql $APEX_DATABASE_URL -c "SELECT 1;"
```

### Migration Errors

```bash
# Check current revision
alembic current

# Show migration history
alembic history

# Fix migration issues
alembic downgrade -1
alembic upgrade head
```

### Service Won't Start

```bash
# Check logs
docker compose logs api
docker compose logs db

# Check environment
docker compose exec api env | grep APEX_
```

## Next Steps

- [**Quick Start Guide**](quickstart.md) - Get running quickly
- [**Architecture Overview**](architecture.md) - Understand system design
- [**Production Deployment**](../deployment/production.md) - Production setup

