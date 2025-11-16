# Architecture Overview

Complete overview of SIGN X Studio Clone system architecture.

## High-Level Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│   API        │────▶│  PostgreSQL │
│   (Browser) │     │   Service    │     │  Database   │
└─────────────┘     └──────────────┘     └─────────────┘
                            │                     │
                            │                     │
                            ▼                     ▼
                    ┌──────────────┐     ┌─────────────┐
                    │   Celery     │     │   Redis     │
                    │   Workers    │     │   Cache     │
                    └──────────────┘     └─────────────┘
                            │
                            │
                            ▼
                    ┌──────────────┐     ┌─────────────┐
                    │   MinIO      │     │ OpenSearch  │
                    │   Storage    │     │   Search    │
                    └──────────────┘     └─────────────┘
```

## Service Components

### API Service

**Technology**: FastAPI  
**Port**: 8000  
**Language**: Python 3.11

**Responsibilities**:
- HTTP request handling
- Route processing
- Response envelope formatting
- Database operations
- External service integration

**Key Features**:
- Async/await for concurrency
- Pydantic v2 for validation
- Structured logging
- Prometheus metrics
- Rate limiting

### Worker Service

**Technology**: Celery  
**Language**: Python 3.11

**Responsibilities**:
- Async task processing
- PDF report generation
- PM system dispatch
- Email notifications

**Task Types**:
- `projects.report.generate` - PDF generation
- `projects.submit.dispatch` - PM dispatch
- `projects.email.send` - Email sending

### Database (PostgreSQL)

**Version**: 15+  
**Port**: 5432

**Tables**:
- `projects` - Project metadata
- `project_payloads` - Design payloads
- `project_events` - Audit trail

**Features**:
- Async SQLAlchemy
- Alembic migrations
- JSON columns
- Full-text search (via OpenSearch)

### Cache (Redis)

**Version**: 7+  
**Port**: 6379

**Uses**:
- Celery message broker
- Task result backend
- Response caching
- Session storage

### Storage (MinIO)

**Type**: S3-compatible  
**Ports**: 9000 (API), 9001 (Console)

**Buckets**:
- `apex-uploads` - User uploads
- `artifacts` - Generated reports

**Structure**:
```
apex-uploads/
├── uploads/          # User files
└── blobs/            # Generated files (SHA256-based)
    ├── ab/
    └── cd/
```

### Search (OpenSearch)

**Version**: 2.12.0  
**Port**: 9200

**Indexes**:
- `projects` - Project search index

**Features**:
- Full-text search
- DB fallback on failure
- Automatic indexing

## Data Flow

### Request Flow

```
Client Request
    ↓
FastAPI Router
    ↓
Route Handler
    ↓
Database Query / External API
    ↓
Response Envelope
    ↓
Client Response
```

### Async Task Flow

```
API Endpoint
    ↓
Enqueue Celery Task
    ↓
Redis Queue
    ↓
Celery Worker
    ↓
Task Execution
    ↓
Result Storage (Redis)
```

## Technology Stack

### Backend

- **FastAPI** - Web framework
- **SQLAlchemy** - ORM
- **Alembic** - Migrations
- **Celery** - Task queue
- **Pydantic v2** - Validation

### Infrastructure

- **PostgreSQL** - Database
- **Redis** - Cache/Queue
- **MinIO** - Object storage
- **OpenSearch** - Search

### Monitoring

- **Prometheus** - Metrics
- **Grafana** - Dashboards
- **OpenTelemetry** - Tracing

## Design Principles

### 1. Determinism

- All calculations are deterministic
- Same inputs = same outputs
- SHA256-based caching
- Versioned constants

### 2. Traceability

- Full audit trail
- Request/response tracing
- Code version tracking
- Assumption logging

### 3. Safety

- Input validation
- Error handling
- Transaction rollbacks
- State machine guards

### 4. Scalability

- Async operations
- Horizontal scaling
- Database connection pooling
- Cache utilization

## API Architecture

### Request/Response

```
Request
  ↓
Validation (Pydantic)
  ↓
Business Logic
  ↓
Database/External Calls
  ↓
Response Envelope
  ↓
Client
```

### Envelope Structure

```python
ResponseEnvelope(
    result=...,
    assumptions=[...],
    confidence=0.95,
    trace=TraceModel(...)
)
```

## Database Schema

### Projects Table

```sql
CREATE TABLE projects (
    project_id VARCHAR(255) PRIMARY KEY,
    account_id VARCHAR(255),
    name VARCHAR(255),
    status VARCHAR(50),
    etag VARCHAR(16),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Project Payloads Table

```sql
CREATE TABLE project_payloads (
    payload_id SERIAL PRIMARY KEY,
    project_id VARCHAR(255),
    module VARCHAR(255),
    config JSONB,
    files TEXT[],
    cost_snapshot JSONB,
    sha256 VARCHAR(64),
    created_at TIMESTAMP
);
```

### Project Events Table

```sql
CREATE TABLE project_events (
    event_id SERIAL PRIMARY KEY,
    project_id VARCHAR(255),
    event_type VARCHAR(255),
    actor VARCHAR(255),
    timestamp TIMESTAMP,
    data JSONB
);
```

## Security

### Authentication

- API key via header (planned)
- JWT tokens (planned)

### Authorization

- Role-based access control (planned)
- Project-level permissions (planned)

### Data Protection

- SHA256 verification
- ETag optimistic locking
- Input sanitization
- SQL injection prevention (SQLAlchemy)

## Monitoring Architecture

### Metrics

```
Prometheus ← API Service (/metrics)
    ↓
Grafana Dashboards
    ↓
Alerting (Alertmanager)
```

### Logging

```
Structured Logs (JSON)
    ↓
stdout / OpenTelemetry
    ↓
Log Aggregation (Loki/ELK)
```

## Scalability Considerations

### Horizontal Scaling

- Stateless API service
- Multiple worker instances
- Database connection pooling
- Redis cluster support

### Vertical Scaling

- Resource limits configured
- Database query optimization
- Cache utilization
- Async task processing

## Next Steps

- [**Quick Start Guide**](quickstart.md) - Get started
- [**Deployment Guide**](../deployment/production.md) - Deploy to production
- [**Monitoring Guide**](../operations/monitoring.md) - Monitor system

