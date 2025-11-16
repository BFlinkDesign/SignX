# 🏗️ SignX Platform Architecture Overview

**The SignX Platform of the Sign Industry**

---

## 🎯 **High-Level Vision**

```
Customer Request → AI Analysis → Instant Quote → Accept → Production
        ↓              ↓             ↓            ↓          ↓
   (5 seconds)   (95 years)    (<5 minutes)  (automated) (automated)
```

**What SignX Platform did for metal, you're doing for signs.**

---

## 📊 **System Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                      CUSTOMER INTERFACE                          │
│  Web Form | Email | API | Mobile | Phone (future voice AI)      │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SignX Platform Core                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Registry   │  │  Event Bus   │  │  Unified API │         │
│  │  (Plugins)   │  │  (Pub/Sub)   │  │  (FastAPI)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────┬────────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
   ┌────▼────┐              ┌─────▼─────┐
   │ Modules │              │  Services │
   └────┬────┘              └─────┬─────┘
        │                         │
  ┌─────┼─────┬─────┬────────────┼──────┬─────────┐
  │     │     │     │            │      │         │
┌─▼─┐ ┌─▼─┐ ┌─▼─┐ ┌─▼──┐    ┌───▼──┐ ┌─▼───┐ ┌──▼──┐
│Eng││RAG││Wkf││Quo│    │Intel││Docs││Prod│
│Cal││   ││Flw││te │    │ML  ││PDF ││CNC │
└───┘ └───┘ └───┘ └────┘    └─────┘ └────┘ └─────┘
  ↓     ↓     ↓     ↓          ↓       ↓      ↓
┌─────────────────────────────────────────────────┐
│               Data Layer                         │
│  PostgreSQL | MinIO | Redis | Gemini RAG       │
└─────────────────────────────────────────────────┘
```

---

## 🔷 **Module Breakdown**

### **1. Engineering Module** (Your APEX CalcuSign)
**Purpose**: Structural calculations and design validation

**Capabilities:**
- Pole selection (AISC catalog)
- Foundation design (direct burial + baseplate)
- Wind load calculations (ASCE 7-22)
- Baseplate engineering checks (ACI 318)
- PDF report generation

**Status**: ✅ Production ready (migrated from existing APEX)

**API Example:**
```
POST /api/v1/engineering/pole/options
{
  "Mu_required_kip_in": 120,
  "height_ft": 20,
  "material": "steel"
}
→ Returns: Filtered pole options with strength checks
```

---

### **2. RAG Module** (Gemini File Search)
**Purpose**: Access 95 years of institutional knowledge

**Capabilities:**
- Semantic search across all historical documents
- Find similar past projects
- Installation guidance
- Permit requirements by jurisdiction
- Cost insights from historical data

**Data Sources:**
- 834 BOT TRAINING documents (Cat Scale, engineering, estimating, AI, sales)
- Future: 10,000+ historical project files
- Future: Photos, drawings, permits

**Status**: ✅ Architecture complete, ready to index

**API Example:**
```
POST /api/v1/rag/search/projects
{
  "sign_type": "monument",
  "dimensions": {"width_ft": 10, "height_ft": 4},
  "location": "Iowa"
}
→ Returns: 5 most similar projects with citations
```

**Competitive Advantage**: Competitors have ZERO historical knowledge. You have 95 years.

---

### **3. Intelligence Module** (SignX-Intel + Eagle Analyzer)
**Purpose**: ML-powered cost and labor prediction

**Capabilities:**
- Material cost estimation (XGBoost models)
- Labor hour prediction (ensemble neural networks)
- Anomaly detection (catch bad bids)
- Historical pattern analysis
- Confidence intervals (99% accuracy goal)

**Status**: 🔄 Integration in progress (merging existing SignX-Intel)

**API Example:**
```
POST /api/v1/intelligence/predict/cost
{
  "project_id": "123",
  "drivers": {
    "sign_height_ft": 25,
    "sign_area_sqft": 120,
    "foundation_type": "drilled_pier"
  }
}
→ Returns: predicted_cost, confidence, cost_drivers breakdown
```

---

### **4. Workflow Module** (EagleHub in Python)
**Purpose**: Automate quote-to-project pipeline

**Capabilities:**
- Email monitoring (Outlook "BID REQUEST" folders)
- KeyedIn CRM integration
- Automatic project creation
- File organization with naming conventions
- Activity dashboard

**Status**: 🔄 Python framework ready (converting from PowerShell)

**Workflow:**
```
Email arrives → Workflow detects "BID REQUEST"
    ↓
Extract: customer, quote#, attachments
    ↓
Create project in SignX-Studio
    ↓
Trigger RAG search for similar projects
    ↓
Trigger Intelligence cost prediction
    ↓
Trigger Quoting module
    ↓
Send instant quote email
```

---

### **5. Quoting Module** (THE KILLER FEATURE)
**Purpose**: SignX Platform-style instant quotes

**Capabilities:**
- Customer submits specs via web form
- AI analyzes requirements
- RAG finds similar projects (95-year history)
- Engineering validates structure
- Intelligence predicts cost
- Professional quote in <5 minutes

**Status**: ✅ Core API complete, web form ready to deploy

**API Example:**
```
POST /api/v1/quoting/instant
{
  "customer_name": "Valley Church",
  "project_name": "Monument Sign",
  "sign_type": "monument",
  "approximate_size": "10ft x 4ft",
  "location": "Grimes, IA"
}
→ Returns: Full quote with cost, timeline, similar projects
```

**THIS IS WHAT MAKES YOU COMPETITIVE WITH SignX Platform.**

---

### **6. Documents Module** (Future)
**Purpose**: PDF parsing and markup

**Components:**
- CatScale parser (vendor PDF extraction)
- BetterBeam (PDF markup tool, Bluebeam alternative)
- CAD automation (CorelDraw integration)
- Measurement extraction

**Status**: 📋 Planned for Phase 2

---

### **7. Production Module** (Future)
**Purpose**: Shop floor automation

**Components:**
- CNC file generation
- Material nesting optimization
- Intelligent scheduling
- Work order generation
- Quality checkpoints

**Status**: 📋 Planned for Phase 3

---

## 🔄 **Event-Driven Flow**

### **Example: Customer Quote Request**

```
1. Customer submits web form
   ↓
2. Workflow module: publishes "quote.received" event
   ↓
3. RAG module: subscribes, searches historical projects
   ↓
4. RAG module: publishes "similar_projects.found" event
   ↓
5. Intelligence module: subscribes, predicts cost
   ↓
6. Intelligence module: publishes "prediction.generated" event
   ↓
7. Engineering module: subscribes, validates structure
   ↓
8. Engineering module: publishes "validation.completed" event
   ↓
9. Quoting module: subscribes, synthesizes all data
   ↓
10. Quoting module: publishes "quote.generated" event
    ↓
11. Customer receives email with quote (<5 minutes total)
```

**Key Benefits:**
- ✅ Modules don't directly depend on each other
- ✅ Easy to add new modules without changing existing code
- ✅ Each module can be developed/tested independently
- ✅ Complete audit trail (all events logged)

---

## 💾 **Data Architecture**

### **PostgreSQL** (Primary Database)
```
projects              # Project metadata
├── id (UUID)
├── customer_name
├── location
├── status
└── created_at

project_payloads      # Design snapshots
├── id
├── project_id
├── module (engineering, quoting, etc.)
├── payload (JSONB)
└── created_at

project_events        # Audit trail
├── id
├── project_id
├── event_type
├── source_module
├── data (JSONB)
└── created_at

cost_records          # Historical costs (SignX-Intel)
├── id
├── project_id
├── total_cost
├── labor_cost
├── material_cost
├── drivers (JSONB)
└── predicted_cost
```

### **Gemini RAG** (Knowledge Base)
```
eagle_sign_master_knowledge (Corpus)
├── cat_scale/           352 documents
├── engineering/         100 documents
├── estimating/           80 documents
├── learning_ai/          50 documents
└── sales/                42 documents

Total: 834 curated documents
Cost: $10-20 one-time indexing
Queries: FREE forever
```

### **MinIO** (File Storage)
```
signx-studio/
├── projects/{id}/
│   ├── drawings/       # Customer PDFs
│   ├── photos/         # Site photos
│   ├── reports/        # Generated PDFs
│   └── cad/            # DXF/DWG files
└── templates/          # Quote templates
```

---

## 🔧 **Tech Stack Summary**

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 + TypeScript | Customer portal (future) |
| **API** | FastAPI 0.110+ | Unified REST API |
| **Database** | PostgreSQL 17 | Primary data store |
| **Cache** | Redis 7 | Session + query cache |
| **Storage** | MinIO | S3-compatible files |
| **RAG** | Gemini File Search | Historical knowledge |
| **ML** | XGBoost 2.1.4 | Cost prediction |
| **Reasoning** | Claude Sonnet 4.5 | Quote synthesis |
| **Orchestration** | LangGraph | Multi-agent workflows |
| **Deployment** | Docker Compose | Local dev |
| **Production** | Railway/Render | Cloud PaaS |

---

## 🚀 **Deployment Stages**

### **Stage 1: Local Development** (NOW)
```
docker-compose up -d
python platform/api/main.py
→ http://localhost:8000/api/docs
```

### **Stage 2: Internal Testing** (Week 2)
```
Deploy to internal server
Test with 10 internal quotes
Validate RAG accuracy
```

### **Stage 3: Beta Launch** (Week 3)
```
Deploy to public URL (quote.eaglesign.net)
Soft launch to 10 friendly customers
Gather feedback
```

### **Stage 4: Production** (Week 4)
```
Full public launch
Marketing campaign
Monitor metrics
Iterate based on usage
```

---

## 📊 **Success Metrics Dashboard**

### **Technical Metrics**
- ✅ API response time < 200ms (p95)
- ✅ RAG relevance > 80%
- ✅ Quote generation < 5 minutes
- ✅ System uptime > 99.5%

### **Business Metrics**
- ✅ Quotes/day: 50+ (Month 1)
- ✅ Conversion rate: 25%+ (Month 1)
- ✅ Customer satisfaction: 4.5+/5
- ✅ Time saved: 2.5 hours/quote

### **Financial Metrics**
- ✅ Operating cost: <$200/month
- ✅ Cost per quote: <$0.50
- ✅ ROI: >10,000% (vs hiring estimator)
- ✅ Revenue growth: 75%+ (Year 1)

---

## 🎯 **The Vision (12-Month Transformation)**

### **Today**
- Manual quotes: 2-4 hours each
- Response time: 1-3 days
- Customer base: 20-30
- Your hours: 70-80/week
- Operating cost: $60k/year estimator

### **Month 3**
- Instant quotes: 5 minutes
- Response time: Instant
- Customer base: 50+
- Your hours: 60/week
- Operating cost: $1,400/year software

### **Month 6**
- 200+ quotes generated
- 100+ new customers
- 30%+ conversion rate
- Your hours: 50/week
- Revenue up 50%

### **Month 12** (SignX Platform Transformation Complete)
- 2,000+ quotes/year
- 500+ customers (SignX Platform model)
- 2-3x industry margins
- Your hours: 40/week (same output as 80!)
- Revenue up 75%+

---

## 🏆 **Why This Will Win**

### **Your Advantages**
1. **95-year knowledge moat** - Competitors have 0 historical data
2. **Gemini free tier** - $0 marginal cost per quote
3. **First mover** - No instant sign quoting exists
4. **Production code** - SignX-Studio & SignX-Intel already work
5. **Curated data** - BOT TRAINING is gold
6. **AI acceleration** - Jules + Claude for fast development

### **The SignX Platform Parallel**
- **They did**: "Call for quote" → "Instant online pricing"
- **You're doing**: "3-day wait" → "5-minute quotes"
- **Their result**: $5M+ revenue, 500+ customers, 2-3x margins
- **Your advantage**: You have 95 years of data they didn't

---

## 📞 **Get Started**

1. **Tonight**: Get Gemini API key + generate corpus (30 min)
2. **Tomorrow**: Test instant quotes (30 min)
3. **This Week**: Deploy web form (2-3 hours)
4. **Next Week**: Launch to customers (ongoing)

**Read**: `START_HERE.md` for your 30-minute action plan

---

**The foundation is built. The moat is deep. The opportunity is massive.**

**Stop reading. Start building. Transform your business in 30 days.** 🚀

---

*Built for Eagle Sign Co. | Architecture by Brady + Claude | November 2025*

