# Quick Start Guide

Get SIGN X Studio Clone running in 5 minutes.

## Prerequisites

- Docker & Docker Compose installed
- 2GB free disk space
- Ports 8000, 5432, 6379 available

## Step 1: Clone & Setup

```bash
# Clone repository
git clone <repository-url>
cd calcusign-apex-clone

# Copy environment file
cp .env.example .env
```

## Step 2: Start Services

```bash
# Start all services
docker compose up -d

# Wait for services to be healthy (about 30 seconds)
docker compose ps
```

## Step 3: Run Migrations

```bash
# Apply database migrations
docker compose exec api python -m alembic upgrade head
```

## Step 4: Verify Installation

```bash
# Health check
curl http://localhost:8000/health | jq

# Expected response:
# {
#   "result": {
#     "service": "api",
#     "status": "ok",
#     "version": "0.1.0"
#   },
#   "confidence": 1.0
# }
```

## Step 5: Create Your First Project

```bash
# Create a project
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "demo",
    "name": "My First Sign",
    "created_by": "user@example.com"
  }' | jq
```

## Next Steps

- **[Installation Guide](installation.md)** - Detailed setup instructions
- **[API Documentation](../reference/api-endpoints.md)** - Explore all endpoints
- **[Sign Design Workflow](../guides/sign-design-workflow.md)** - Complete workflow guide

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker compose logs api
docker compose logs db
docker compose logs cache

# Restart services
docker compose restart
```

### Database Connection Errors

```bash
# Verify database is running
docker compose ps db

# Check database URL
docker compose exec api env | grep DATABASE_URL
```

### Port Already in Use

Edit `docker-compose.yml` to change ports:
```yaml
ports:
  - "8001:8000"  # Change 8000 to 8001
```

## What's Next?

Once you have the API running:

1. **Explore API Docs**: http://localhost:8000/docs
2. **View Metrics**: http://localhost:8000/metrics
3. **Follow Workflow Guide**: See [Sign Design Workflow](../guides/sign-design-workflow.md)

