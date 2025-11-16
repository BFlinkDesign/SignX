# 🏗️ SignX Platform - Complete Integrated Sign Industry Solution

**Status**: ✅ **Foundation Complete** | 🚀 **Ready to Deploy** | 📦 **On GitHub**

**Repository**: https://github.com/EAGLE605/SignX

> *"The first all-in-one platform for the sign industry: instant online quoting, AI-powered automation, and 95 years of institutional knowledge at your fingertips."*

---

## 🎯 **What Is This?**

SignX is the **first all-in-one integrated platform** for the sign industry that combines:

- **Instant Online Quoting** - Customers get quotes in <5 minutes (not days)
- **Structural Engineering** - ASCE 7-22, ACI 318, AISC compliant calculations
- **AI Cost Estimation** - GPU-accelerated ML models trained on your data
- **95-Year Knowledge Base** - Every past project searchable via Gemini RAG
- **Production Automation** - Quote → Engineering → Shop Drawings → CNC

### **The Transformation**

| Before (Manual) | After (SignX) | Improvement |
|----------------|---------------|-------------|
| Quote time: 2-4 hours | 5 minutes | **96% faster** |
| Response time: 1-3 days | Instant | **99% faster** |
| Your hours: 70/week | 40/week | **43% reduction** |
| Customer base: 20-30 | 500+ | **20x growth** |
| Margins: Industry avg | 2-3x industry | **200% increase** |

---

## 📁 **Repository Structure**

```
C:\Scripts\SignX\
│
├── SignX-Studio/              # 🏠 Main platform (THIS REPO)
│   ├── platform/              # ✅ Core infrastructure
│   │   ├── registry.py        # Module plugin system
│   │   ├── events.py          # Event bus for inter-module communication
│   │   └── api/main.py        # FastAPI application with auto-discovery
│   │
│   ├── modules/               # ✅ Feature modules (instant online quoting platform-style)
│   │   ├── engineering/       # Structural calculations (APEX)
│   │   ├── intelligence/      # ML cost prediction (SignX-Intel)
│   │   ├── workflow/          # Email automation (EagleHub → Python)
│   │   ├── rag/               # Historical knowledge (Gemini File Search)
│   │   ├── quoting/           # Instant quotes (THE KILLER FEATURE)
│   │   ├── documents/         # PDF parsing (CatScale + BetterBeam)
│   │   └── production/        # CNC export, scheduling (future)
│   │
│   ├── ui/                    # React customer portal (future)
│   ├── services/              # Background workers
│   └── docs/                  # Documentation
│
├── SignX-Intel/               # 🧠 ML service (separate repo)
│   ├── models/                # Trained XGBoost models
│   ├── training/              # Training pipelines
│   └── api/                   # ML inference API
│
├── SignX-Data/                # 📦 Training data (separate repo)
│   ├── historical_projects/   # 95 years of PDFs
│   ├── cost_summaries/        # Cost data
│   └── photos/                # Installation photos
│
└── Other Tools/               # 🔧 Utilities
    ├── Benchmark/             # CatScale PDF parser
    ├── eagle_analyzer_v1/     # Labor estimation
    ├── EagleHub/              # Workflow automation (legacy)
    └── CorelDraw Macros/      # CAD automation
```

---

## 🚀 **Quick Start**

### **Prerequisites**
- [x] Python 3.12 with venv
- [x] Google Gemini subscription (you have it!)
- [ ] Gemini API key from https://aistudio.google.com (free tier: 1,500 req/day)

### **5-Minute Setup**

```powershell
# 1. Navigate to platform
cd C:\Scripts\SignX\SignX-Studio

# 2. Create virtual environment
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install google-generativeai anthropic fastapi uvicorn pydantic

# 4. Set API key
$env:GEMINI_API_KEY = "your-key-from-aistudio"

# 5. Start platform
python platform/api/main.py
```

**Visit**: http://localhost:8000/api/docs

**Success**: You see the Swagger UI with 5 modules registered

## 🔒 Security

Every push and pull request runs Semgrep (SAST), Gitleaks (secret scanning), and Safety (Python dependency audit) inside [`.github/workflows/security-scan.yml`](.github/workflows/security-scan.yml). Read [docs/SECURITY_SCANNING.md](docs/SECURITY_SCANNING.md) for local commands and policies before opening a PR so the checks stay green. VBA macros used for structural calculations remain out of scope for automation—continue to run VBDepend manually whenever you edit CorelDraw or Excel tooling.

---

## 🎯 **Key Features**

### **1. Instant Quote API** 🏆
The feature that transforms the quoting process:

```bash
curl -X POST http://localhost:8000/api/v1/quoting/instant \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Valley Church",
    "customer_email": "contact@valleychurch.org",
    "project_name": "Monument Sign",
    "location": "Grimes, IA",
    "sign_type": "monument",
    "approximate_size": "10ft x 4ft",
    "mounting_type": "ground mount",
    "lighting": "LED illuminated"
  }'
```

**Response** (in <5 seconds):
```json
{
  "quote_id": "550e8400-...",
  "estimated_cost": 8000,
  "cost_range": [6800, 9200],
  "confidence": 0.85,
  "lead_time": "4-6 weeks",
  "similar_projects": [
    {"project": "Valley Church Monument", "cost": 7850, "year": 2024}
  ],
  "valid_until": "2025-12-10T..."
}
```

### **2. Historical Knowledge Base** 📚
Via Gemini File Search RAG:

```python
# Search 95 years of projects
POST /api/v1/rag/search/projects
{
  "sign_type": "monument",
  "dimensions": {"width_ft": 10, "height_ft": 4},
  "location": "Iowa"
}

# Returns: Similar past projects with citations, costs, challenges
```

**Advantage**: Your competitors start with zero knowledge. You start with 95 years.

### **3. Module Plugin System** 🔌
Easy to extend, hard to break:

```python
# Add new module
from platform.registry import registry, ModuleDefinition

module_def = ModuleDefinition(
    name="my_module",
    version="1.0.0",
    display_name="My Module",
    api_prefix="/api/v1/my_module"
)

router = APIRouter()
registry.register(module_def, router)
```

**Result**: Module automatically appears in API docs, event bus, and module list.

### **4. Event-Driven Architecture** 📡
Modules communicate without tight coupling:

```python
# Module A publishes event
await event_bus.publish(Event(
    type="quote.accepted",
    source="quoting",
    project_id="123",
    data={"cost": 8000}
))

# Module B automatically receives it
@event_bus.subscribe("quote.accepted")
async def on_quote_accepted(event: Event):
    # Trigger production workflow
    pass
```

---

## 💰 **Business Model (instant online quoting platform Transformation)**

### **Revenue Structure**

**Current** (typical sign shop):
- 80% revenue from 5-10 customers
- High dependency, low negotiating power
- Manual processes limit scale

**Target** (instant online quoting platform model):
- 80% revenue from 500+ customers
- Resilient to single customer loss
- Automated processes enable scale

### **Operating Costs**

| Service | Monthly Cost | Annual |
|---------|-------------|--------|
| Gemini API | $0 (free tier) | $0 |
| Claude API | $60 (1k quotes) | $720 |
| Hosting | $50 (Railway) | $600 |
| Domain/SSL | $2 (Cloudflare) | $24 |
| Storage | $5 (S3) | $60 |
| **Total** | **$117/mo** | **$1,404/yr** |

**vs. Hiring estimator**: $60k/year
**Savings**: $58,596/year (97% reduction)

---

## 📊 **Tech Stack**

### **Core Platform**
- **Language**: Python 3.12
- **API Framework**: FastAPI 0.110+
- **Database**: PostgreSQL 17 (existing SignX-Studio)
- **Cache**: Redis
- **Storage**: MinIO (S3-compatible)

### **AI/ML Layer**
- **RAG**: Google Gemini File Search (multimodal, free queries)
- **Reasoning**: Claude Sonnet 4.5 (200K context, extended thinking)
- **Cost Prediction**: XGBoost 2.1.4 (GPU-accelerated)
- **Orchestration**: LangGraph (multi-agent workflows)

### **Infrastructure**
- **Deployment**: Docker Compose → Railway/Render
- **Monitoring**: Prometheus + Grafana
- **Logging**: Structured logs + Sentry
- **CI/CD**: GitHub Actions

---

## 📖 **Documentation**

### **Getting Started**
1. **[GETTING_STARTED.md](GETTING_STARTED.md)** - Start here! 30-minute setup guide
2. **[instant online quoting platform_QUICKSTART.md](SignX-Studio/instant online quoting platform_QUICKSTART.md)** - 30-day implementation plan
3. **[INTEGRATION_PLAN.md](INTEGRATION_PLAN.md)** - Complete technical roadmap

### **Technical Docs**
- **Platform Core**: `platform/README.md` (module system, events)
- **Module Development**: `modules/README.md` (how to create modules)
- **API Reference**: http://localhost:8000/api/docs (when running)

### **Business Docs**
- **instant online quoting platform Case Study**: See `INTEGRATION_PLAN.md` (instant online quoting platform comparison)
- **ROI Calculator**: See `GETTING_STARTED.md` (cost analysis)

---

## 🏆 **Success Metrics**

### **Week 1 Goals**
- [ ] Platform running locally
- [ ] 100 documents indexed in Gemini
- [ ] 5 test quotes generated
- [ ] RAG queries return relevant results (80%+ accuracy)

### **Month 1 Goals**
- [ ] Public web form deployed
- [ ] 50+ customer quotes
- [ ] 10+ quotes accepted
- [ ] $100k+ in quoted projects

### **Month 3 Goals**
- [ ] 200+ quotes generated
- [ ] 30%+ conversion rate
- [ ] 50+ new customers
- [ ] $500k+ revenue pipeline

### **Month 12 Goals** (instant online quoting platform Transformation)
- [ ] 2,000+ quotes/year
- [ ] 500+ active customers
- [ ] 2-3x industry margins
- [ ] Your working hours: 70hrs → 40hrs

---

## 🎯 **Roadmap**

### **Phase 1: Customer-Facing Automation** (Months 1-3) ✅ READY
- [x] Platform core with module system
- [x] Gemini RAG integration
- [x] Instant quote API
- [ ] Public web portal
- [ ] Email notifications

### **Phase 2: Production Automation** (Months 4-6)
- [ ] Automated work order generation
- [ ] Intelligent scheduling (AI-driven)
- [ ] Real-time capacity planning
- [ ] Automated procurement
- [ ] Digital inspection forms

### **Phase 3: Self-Service Platform** (Months 7-9)
- [ ] Customer portal (account dashboard)
- [ ] Real-time job tracking
- [ ] Document library
- [ ] Change order requests
- [ ] Digital approvals (DocuSign)

### **Phase 4: Intelligence Layer** (Months 10-12)
- [ ] Requirements agent (chat-based inquiry)
- [ ] Design agent (manufacturability review)
- [ ] Documentation agent (permits, manuals)
- [ ] Quality agent (photo inspection)
- [ ] Cost optimization agent

---

## 🤝 **Contributing**

This is your proprietary system, but here's how to extend it:

### **Adding a New Module**
1. Create `modules/my_module/__init__.py`
2. Define module with `ModuleDefinition`
3. Create API router with FastAPI
4. Subscribe to relevant events
5. Register with `registry.register()`

**Example**: See `modules/engineering/__init__.py` for reference

### **Adding an Event**
```python
# Publish event
await event_bus.publish(Event(
    type="my_module.action_completed",
    source="my_module",
    project_id=project_id,
    data={...}
))
```

**Convention**: `{module}.{action}` (e.g., `quote.generated`, `design.approved`)

---

## 📞 **Support**

### **Resources**
- **API Docs**: http://localhost:8000/api/docs (interactive Swagger)
- **Platform Health**: http://localhost:8000/api/v1/platform/health
- **Module List**: http://localhost:8000/api/v1/platform/modules

### **Tools You Have**
- **Jules** (Gemini subscription) - For coding assistance
- **Claude Code** - For architecture questions
- **Gemini API** (free tier) - 1,500 requests/day

### **Questions?**
Read the docs first, then:
1. Check `GETTING_STARTED.md` for setup issues
2. Check `INTEGRATION_PLAN.md` for technical questions
3. Check module-specific README files

---

## 📄 **License**

Proprietary - Eagle Sign Co.
All rights reserved.

---

## 🎉 **The Bottom Line**

You have:
- ✅ 95 years of project history (competitive moat)
- ✅ Production-ready engineering platform (SignX-Studio/APEX)
- ✅ ML cost prediction system (SignX-Intel)
- ✅ Plugin architecture (easy to extend)
- ✅ Instant quote API (instant online quoting platform killer feature)
- ✅ Free Gemini RAG (no marginal cost per query)

**What instant online quoting platform did**: Took metal fabrication from "call us for a quote" to "instant online pricing"

**What you're doing**: Taking sign manufacturing from "we'll get back to you in 3 days" to "here's your quote in 5 minutes"

**The opportunity**: First-mover advantage in a $30B+ industry

**Start tonight**: Get Gemini API key → Index 100 documents → Generate first quote

---

**Built for Eagle Sign Co. | Powered by 95 years of expertise + 2025 AI**

