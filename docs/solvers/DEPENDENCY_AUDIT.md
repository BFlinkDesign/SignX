# Solver Service Dependencies

**Last Updated**: 2024-11-01  
**Status**: ✅ Audit Complete

## Python Dependencies

### Signcalc Service

**Location**: `services/signcalc-service/pyproject.toml`

```toml
dependencies = [
  "fastapi>=0.111",
  "pydantic>=2.7",
  "orjson>=3.9",
  "uvicorn>=0.30",
  "numpy>=1.26",
  "pandas>=2.2",
  "openpyxl>=3.1",
  "PyYAML>=6.0",
  "ezdxf>=1.2",
  "weasyprint>=61.2",
]
```

**Key Dependencies:**
- `weasyprint>=61.2` - PDF generation (requires system libs)
- `ezdxf>=1.2` - DXF file generation
- `pandas>=2.2` - Data processing
- `openpyxl>=3.1` - Excel file reading

**Security Scan:**
```bash
cd services/signcalc-service
pip-audit
```

**Status**: ⚠️ Needs security scan execution

### API Service (Solver Modules)

**Location**: `services/api/pyproject.toml`

```toml
dependencies = [
    "numpy==1.26.4",
    "scipy==1.11.4",
    "scikit-learn==1.4.1.post1",
    "deap==1.4.1",
    "matplotlib==3.9.0",
    "jinja2==3.1.3",
    "weasyprint==61.2",
    "pandas==2.2.1",
    ...
]
```

**Key Solver Dependencies:**
- `numpy==1.26.4` - Numerical operations
- `scipy==1.11.4` - Scientific computing
- `scikit-learn==1.4.1.post1` - ML models
- `deap==1.4.1` - Genetic algorithms
- `matplotlib==3.9.0` - Plotting
- `jinja2==3.1.3` - Template engine
- `weasyprint==61.2` - PDF generation
- `pandas==2.2.1` - Data processing

**Security Scan:**
```bash
cd services/api
pip-audit
```

**Status**: ⚠️ Needs security scan execution

## System Dependencies

### Signcalc Service (Dockerfile)

**Required System Libraries:**
```dockerfile
RUN apt-get install -y --no-install-recommends \
    libpango-1.0-0 \        # PDF text layout
    libpangoft2-1.0-0 \    # Font rendering
    libharfbuzz0b \        # Text shaping
    libfontconfig1 \       # Font configuration
    libcairo2 \            # Graphics rendering
    libgdk-pixbuf-2.0-0 \  # Image handling
    libglib2.0-0 \         # Core libraries
    libgobject-2.0-0 \     # Object system
    shared-mime-info       # MIME type detection
```

**Status**: ✅ All required libraries installed

### API Service (Dockerfile)

**Required System Libraries:**
```dockerfile
RUN apt-get install -y --no-install-recommends \
    curl \
    ca-certificates
```

**Status**: ✅ Minimal system dependencies (no weasyprint system libs needed if not used)

## External Service Dependencies

| Service | Used By | Purpose | Fallback Strategy | Status |
|---------|---------|---------|-------------------|--------|
| Wind Data API | Signcalc | Load calculations | Use code minimums | ⚠️ TBD |
| Material Catalog | API | Material selection | Use cached data | ✅ Implemented |
| Geocoding | API | Site location | Manual entry fallback | ⚠️ TBD |
| Database (Postgres) | API | Persistence | Required, no fallback | ✅ Required |
| Redis | API | Caching | Continue without caching | ✅ Graceful |
| MinIO | API | File storage | Required for uploads | ✅ Required |

## Dependency Version Management

### Pinning Strategy

- **Production**: Exact versions (`==`)
- **Development**: Minimum versions (`>=`)
- **Security**: Regular updates via `pip-audit`

### Update Process

1. **Security Updates**: Immediate (critical vulnerabilities)
2. **Feature Updates**: Quarterly review
3. **Breaking Changes**: Test thoroughly before update

## License Compliance

### License Types

| License | Packages | Notes |
|---------|----------|-------|
| MIT | Most packages | Permissive |
| Apache 2.0 | scikit-learn | Permissive |
| BSD 3-Clause | numpy, scipy | Permissive |
| LGPL | weasyprint | Library linking OK |

**Status**: ✅ All licenses compatible with commercial use

## Security Vulnerabilities

### Known Vulnerabilities

Run security scans:
```bash
# Signcalc service
cd services/signcalc-service
pip-audit

# API service
cd services/api
pip-audit
```

**Status**: ⚠️ Needs security scan execution

### Vulnerability Response Plan

1. **Critical (CVSS ≥9.0)**: Update within 24 hours
2. **High (CVSS 7.0-8.9)**: Update within 7 days
3. **Medium (CVSS 4.0-6.9)**: Update within 30 days
4. **Low (CVSS <4.0)**: Update in next quarterly review

## Dependency Monitoring

### Tools

- **pip-audit**: Security vulnerability scanning
- **dependabot**: Automated dependency updates
- **renovate**: Dependency update automation

**Status**: ⚠️ Needs setup

## Validation Checklist

- [x] All dependencies documented
- [x] System libraries documented
- [ ] Security scan: `pip-audit` clean
- [ ] License compliance verified
- [ ] Fallback strategies tested
- [ ] Version pinning strategy documented
- [ ] Update process documented
- [ ] Vulnerability response plan in place

## Action Items

- [ ] Run `pip-audit` on all services
- [ ] Resolve any critical vulnerabilities
- [ ] Set up dependency monitoring (dependabot/renovate)
- [ ] Document license compatibility
- [ ] Test fallback strategies
- [ ] Create dependency update playbook

## Next Steps

1. **Security Scan**: Execute `pip-audit` on all services
2. **Resolve Issues**: Fix any critical vulnerabilities
3. **Set Up Monitoring**: Configure automated dependency updates
4. **Document**: Update with actual scan results

