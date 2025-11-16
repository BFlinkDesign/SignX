# SIGN X Studio Clone - Documentation

Complete documentation for the SIGN X Studio Clone platform.

## 📚 Documentation Structure

### Getting Started
- [**Quick Start Guide**](getting-started/quickstart.md) - Get up and running in 5 minutes
- [**Installation Guide**](getting-started/installation.md) - Detailed installation instructions
- [**Architecture Overview**](getting-started/architecture.md) - System architecture and design

### Usage Guides
1. [**Project Management Guide**](guides/project-management.md) - Create and manage projects
2. [**Sign Design Workflow**](guides/sign-design-workflow.md) - Complete sign design process
3. [**Foundation Design Guide**](guides/foundation-design.md) - Direct burial and baseplate design
4. [**Pricing & Estimation**](guides/pricing-estimation.md) - Cost estimation and pricing
5. [**File Management**](guides/file-management.md) - File uploads and MinIO integration
6. [**API Integration Guide**](guides/api-integration.md) - External API integration

### Reference
- [**API Endpoints Reference**](reference/api-endpoints.md) - Complete API documentation
- [**Environment Variables**](reference/environment-variables.md) - Configuration reference
- [**Response Envelope Schema**](reference/response-envelope.md) - API response format
- [**Error Codes**](reference/error-codes.md) - Error handling reference

### Deployment
- [**Production Deployment**](deployment/production.md) - Production deployment guide
- [**Docker Compose Setup**](deployment/docker-compose.md) - Container orchestration
- [**Kubernetes Deployment**](deployment/kubernetes.md) - K8s manifests and configs

### Operations
- [**Monitoring & Metrics**](operations/monitoring.md) - Prometheus metrics and monitoring
- [**Troubleshooting**](operations/troubleshooting.md) - Common issues and solutions
- [**Runbooks**](operations/runbooks.md) - Operational procedures

## 🚀 Quick Links

- **API Documentation**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

## 📖 Documentation Build

This documentation is built with MkDocs:

```bash
# Install dependencies
pip install mkdocs mkdocs-material

# Serve locally
mkdocs serve

# Build static site
mkdocs build
```

## 🤝 Contributing

See the main [README](../README.md) for contribution guidelines.

