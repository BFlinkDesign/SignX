# SIGN X Studio Clone

**Deterministic, test-first, containerized sign design and engineering platform.**

## Welcome

SIGN X Studio Clone is a complete sign design and engineering platform that provides deterministic calculations, end-to-end workflows, and production-ready deployment.

## Quick Navigation

### 🚀 Get Started

- [**Quick Start**](getting-started/quickstart.md) - Get running in 5 minutes
- [**Installation**](getting-started/installation.md) - Detailed setup guide
- [**Architecture**](getting-started/architecture.md) - System design overview

### 📖 Usage Guides

- [**Project Management**](guides/project-management.md) - Create and manage projects
- [**Sign Design Workflow**](guides/sign-design-workflow.md) - Complete design process
- [**Foundation Design**](guides/foundation-design.md) - Direct burial and baseplate
- [**Pricing & Estimation**](guides/pricing-estimation.md) - Cost calculations
- [**File Management**](guides/file-management.md) - File uploads

### 📚 Reference

- [**API Endpoints**](reference/api-endpoints.md) - Complete API reference
- [**Environment Variables**](reference/environment-variables.md) - Configuration
- [**Response Envelope**](reference/response-envelope.md) - API response format

### 🚢 Deployment

- [**Production Deployment**](deployment/production.md) - Production guide
- [**Docker Compose**](deployment/docker-compose.md) - Container setup
- [**Kubernetes**](deployment/kubernetes.md) - K8s deployment

### 🔧 Operations

- [**Monitoring**](operations/monitoring.md) - Prometheus metrics
- [**Troubleshooting**](operations/troubleshooting.md) - Common issues
- [**Runbooks**](operations/runbooks.md) - Operational procedures

## Key Features

✅ **Deterministic Calculations** - Reproducible engineering calculations  
✅ **Complete Workflow** - Project creation to PDF generation  
✅ **Production Ready** - Containerized, tested, monitored  
✅ **Full Traceability** - Audit trails and response envelopes  
✅ **Scalable** - Async tasks with Celery workers  

## API Quick Reference

```bash
# Health check
curl http://localhost:8000/health

# Create project
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{"account_id": "demo", "name": "My Sign", "created_by": "user@example.com"}'

# List projects
curl http://localhost:8000/projects
```

## Getting Help

- **Documentation**: Browse the guides above
- **API Docs**: http://localhost:8000/docs (when running)
- **Issues**: Open a GitHub issue
- **Discussions**: Use GitHub Discussions

---

**Version**: 0.1.0 | **Status**: ✅ Production Ready

