# Environment Variables Reference

Complete reference for all configuration environment variables.

## Variable Naming

All variables use the `APEX_` prefix. For example, `APEX_DATABASE_URL` sets the database connection.

## Core Configuration

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `APEX_ENV` | `dev` | Environment: `dev`, `test`, `prod` | No |
| `APEX_SERVICE_NAME` | `api` | Service identifier | No |
| `APEX_APP_VERSION` | `0.1.0` | Application version | No |
| `APEX_DEPLOYMENT_ID` | `dev` | Deployment identifier | No |
| `APEX_SCHEMA_VERSION` | `v1` | API schema version | No |

## Database

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `APEX_DATABASE_URL` | `postgresql://apex:apex@db:5432/apex` | PostgreSQL connection string | Yes (prod) |

**Format**: `postgresql://user:password@host:port/database`

**Example**:
```bash
APEX_DATABASE_URL=postgresql://apex:secret@localhost:5432/apex
```

## Cache & Queue

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `APEX_REDIS_URL` | `redis://cache:6379/0` | Redis connection URL | Yes (prod) |

**Format**: `redis://host:port/db` or `redis://user:password@host:port/db`

## Object Storage (MinIO)

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `APEX_MINIO_URL` | `http://object:9000` | MinIO endpoint | Yes |
| `APEX_MINIO_ACCESS_KEY` | `None` | MinIO access key | Yes (prod) |
| `APEX_MINIO_SECRET_KEY` | `None` | MinIO secret key | Yes (prod) |
| `APEX_MINIO_BUCKET` | `None` | Default bucket name | No |

## Search (OpenSearch)

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `APEX_OPENSEARCH_URL` | `http://search:9200` | OpenSearch endpoint | No |

## CORS

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `APEX_CORS_ALLOW_ORIGINS` | `[]` | Comma-separated list of allowed origins | Yes (prod) |

**Example**:
```bash
APEX_CORS_ALLOW_ORIGINS=http://localhost:3000,https://app.example.com
```

## Rate Limiting

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `APEX_RATE_LIMIT_DEFAULT` | `60/minute` | Default rate limit | No |
| `APEX_RATE_LIMIT_PER_MIN` | `None` | Override rate limit (requests per minute) | No |

**Example**:
```bash
APEX_RATE_LIMIT_PER_MIN=120  # 120 requests per minute
```

## Request Limits

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `APEX_BODY_SIZE_LIMIT_BYTES` | `256000` | Maximum request body size | No |

## Tracing

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `APEX_OTEL_EXPORTER` | `stdout` | Tracing exporter: `stdout` or `otlp` | No |
| `APEX_OTEL_ENDPOINT` | `None` | OTLP endpoint (if using otlp exporter) | No |

## Model Configuration

These appear in API response traces:

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `APEX_MODEL_PROVIDER` | `none` | LLM provider identifier | No |
| `APEX_MODEL_NAME` | `none` | Model name | No |
| `APEX_MODEL_TEMPERATURE` | `0.0` | Model temperature | No |
| `APEX_MODEL_MAX_TOKENS` | `1024` | Maximum tokens | No |
| `APEX_MODEL_SEED` | `None` | Random seed | No |

## Version Information

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `GIT_SHA` | `dev` | Git commit SHA | No |
| `GIT_DIRTY` | `false` | Git working tree dirty flag | No |
| `BUILD_ID` | `None` | CI/CD build identifier | No |

## Production Checklist

In production, ensure these are set:

- ✅ `APEX_DATABASE_URL` - Production database
- ✅ `APEX_REDIS_URL` - Production Redis
- ✅ `APEX_MINIO_ACCESS_KEY` - Production credentials
- ✅ `APEX_MINIO_SECRET_KEY` - Production credentials
- ✅ `APEX_CORS_ALLOW_ORIGINS` - Explicit allowlist
- ✅ `GIT_SHA` - Actual commit SHA (not `dev`)

## Environment File Example

```bash
# .env file
APEX_ENV=prod
APEX_DATABASE_URL=postgresql://apex:password@prod-db:5432/apex
APEX_REDIS_URL=redis://prod-redis:6379/0
APEX_MINIO_URL=https://s3.example.com
APEX_MINIO_ACCESS_KEY=minioadmin
APEX_MINIO_SECRET_KEY=minioadmin
APEX_MINIO_BUCKET=apex-prod
APEX_OPENSEARCH_URL=http://search:9200
APEX_CORS_ALLOW_ORIGINS=https://app.example.com
APEX_RATE_LIMIT_PER_MIN=100
GIT_SHA=abc123def456
GIT_DIRTY=false
BUILD_ID=build-123
```

## Validation

The application validates required environment variables on startup in production:

```bash
# Check validation errors
docker compose logs api | grep "prod_validation"
```

Validation fails fast if required variables are missing or have default values in production.

