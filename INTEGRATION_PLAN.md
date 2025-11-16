# SignX Studio - The modern integrated platform of the Sign Industry
## Complete Integration Roadmap

**Vision:** Build the first all-in-one platform for the sign industry that combines quoting, design, engineering, estimation, and production planning into a single integrated system.

**Inspiration:** modern integrated platform (metal fabrication) - but for signs

---

## Current State Assessment

### What's Production-Ready ✅
- **SignX-Studio/APEX**: Complete structural engineering platform (40+ endpoints)
- **SignX-Intel**: GPU-accelerated ML cost prediction service
- **Infrastructure**: Docker Compose, PostgreSQL, MinIO, Redis, monitoring

### What Needs Integration 🔄
- **EagleHub**: Workflow automation (PowerShell → needs Python rewrite)
- **CatScale**: PDF parsing (standalone → needs service integration)
- **Eagle Analyzer**: Labor estimation (desktop app → merge into SignX-Intel)
- **BetterBeam**: PDF markup (early prototype → production-ready tool)
- **CorelDraw Macros**: CAD automation (VBA → needs Python COM bridge)

### What's Missing ❌
- Unified UI with module navigation
- Plugin architecture for modules
- Event bus for inter-module communication
- End-to-end workflow automation
- Professional quote generation with AI

---

## Architecture Decision: Modular Monolith

**Choice:** Start with modular monolith, evolve to microservices later

**Why:**
- Faster development (shared code, single deployment)
- Easier to refactor module boundaries
- Lower operational complexity initially
- Can extract services later when needed

**Structure:**
```
SignX-Studio (Monolith)
├── platform/          # Core infrastructure
├── modules/           # Feature modules (loosely coupled)
├── services/          # Background workers
└── ui/                # Unified React frontend
```

Each module:
- Has its own API routes (`/api/v1/{module}/...`)
- Can depend on platform services (auth, storage, events)
- Cannot directly import from other modules (use events/APIs)
- Registers itself with the platform on startup

---

## Phase 1: Foundation (Weeks 1-2)

### Week 1: Restructure & Platform Core

#### Day 1-2: Create Monorepo Structure
**Goal:** Reorganize existing code into modular structure

```bash
# Create new structure
mkdir -p platform/{auth,storage,events,models,api}
mkdir -p modules/{engineering,intelligence,workflow,documents,quoting,production}
mkdir -p services/{worker,scheduler,notifier}
mkdir -p ui/src/{modules,platform}

# Move existing SignX-Studio code
mv services/api/* modules/engineering/api/
mv services/signcalc-service/* modules/engineering/solvers/
mv ui/* ui/src/modules/engineering/

# Move SignX-Intel
cp -r ../SignX-Intel/src/signx_intel/* modules/intelligence/

# Prep other modules
touch modules/workflow/README.md  # EagleHub rewrite
touch modules/documents/README.md # CatScale + BetterBeam
touch modules/quoting/README.md   # Quote generation
```

**Deliverable:** New directory structure with existing code migrated

#### Day 3-4: Build Platform Core

**File:** `platform/registry.py`
```python
"""
Module Registry - modern integrated platform-style plugin system
"""
from typing import Dict, List, Callable
from fastapi import FastAPI, APIRouter
from pydantic import BaseModel

class ModuleDefinition(BaseModel):
    """Define a module's capabilities"""
    name: str
    version: str
    api_prefix: str  # e.g., "/api/v1/engineering"
    ui_routes: List[str]  # e.g., ["/projects/:id/engineering"]
    events_consumed: List[str]  # e.g., ["project.created"]
    events_published: List[str]  # e.g., ["design.completed"]
    
class ModuleRegistry:
    """Central registry for all modules"""
    def __init__(self):
        self.modules: Dict[str, ModuleDefinition] = {}
        
    def register(self, module: ModuleDefinition, router: APIRouter):
        """Register a module with the platform"""
        self.modules[module.name] = module
        return router
        
    def get_module(self, name: str) -> ModuleDefinition:
        return self.modules.get(name)
        
    def list_modules(self) -> List[ModuleDefinition]:
        return list(self.modules.values())

# Global registry
registry = ModuleRegistry()
```

**File:** `platform/events.py`
```python
"""
Event Bus - Inter-module communication
"""
import asyncio
from typing import Callable, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel
import json

class Event(BaseModel):
    """Platform event"""
    type: str  # e.g., "project.created"
    source: str  # module name
    project_id: str | None = None
    data: Dict[str, Any]
    timestamp: datetime = datetime.utcnow()
    
class EventBus:
    """Pub/sub event bus for modules"""
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        
    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to an event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        
    async def publish(self, event: Event):
        """Publish event to all subscribers"""
        handlers = self.subscribers.get(event.type, [])
        # Store in DB for audit
        await self._store_event(event)
        # Notify subscribers
        await asyncio.gather(*[handler(event) for handler in handlers])
        
    async def _store_event(self, event: Event):
        """Store event in database for audit trail"""
        # TODO: Store in project_events table
        pass

# Global event bus
event_bus = EventBus()
```

**File:** `platform/api/main.py`
```python
"""
Platform API - Main entry point
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from platform.registry import registry
from platform.events import event_bus
from platform.auth import get_current_user

app = FastAPI(
    title="SignX Studio",
    description="The modern integrated platform of the Sign Industry",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Platform endpoints
@app.get("/api/v1/platform/modules")
async def list_modules():
    """List all registered modules"""
    return {"modules": registry.list_modules()}

@app.get("/api/v1/platform/health")
async def health_check():
    """Platform health check"""
    return {
        "status": "healthy",
        "modules": len(registry.modules),
        "version": "2.0.0"
    }

# Module registration happens in their __init__.py
# Each module imports registry and calls registry.register()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Deliverable:** Platform core with module registry and event bus

#### Day 5: Update Engineering Module

**File:** `modules/engineering/__init__.py`
```python
"""
Engineering Module - Structural calculations (APEX CalcuSign)
"""
from fastapi import APIRouter
from platform.registry import registry, ModuleDefinition
from platform.events import event_bus, Event

# Module definition
module_def = ModuleDefinition(
    name="engineering",
    version="1.0.0",
    api_prefix="/api/v1/engineering",
    ui_routes=[
        "/projects/:id/engineering",
        "/projects/:id/engineering/pole",
        "/projects/:id/engineering/foundation"
    ],
    events_consumed=["project.created", "design.updated"],
    events_published=["calculations.completed", "design.approved"]
)

# API router
router = APIRouter(prefix="/api/v1/engineering", tags=["engineering"])

# Import existing endpoints
from .api.routes import pole, foundation, baseplate, reports

router.include_router(pole.router)
router.include_router(foundation.router)
router.include_router(baseplate.router)
router.include_router(reports.router)

# Event handlers
async def on_project_created(event: Event):
    """When a project is created, initialize engineering defaults"""
    project_id = event.project_id
    # TODO: Create default engineering record
    print(f"Engineering module: Project {project_id} created")

# Subscribe to events
event_bus.subscribe("project.created", on_project_created)

# Register with platform
registry.register(module_def, router)
```

**Deliverable:** Engineering module using plugin architecture

### Week 2: Intelligence Module Integration

#### Day 1-2: Migrate SignX-Intel as Module

**File:** `modules/intelligence/__init__.py`
```python
"""
Intelligence Module - ML-powered cost/labor prediction
"""
from fastapi import APIRouter
from platform.registry import registry, ModuleDefinition
from platform.events import event_bus, Event

module_def = ModuleDefinition(
    name="intelligence",
    version="1.0.0",
    api_prefix="/api/v1/intelligence",
    ui_routes=["/projects/:id/intelligence"],
    events_consumed=["design.completed", "project.submitted"],
    events_published=["prediction.generated", "model.trained"]
)

router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])

# Cost prediction endpoint
@router.post("/predict/cost")
async def predict_cost(drivers: dict, project_id: str):
    """Predict project cost using ML models"""
    from .cost_prediction import CostPredictor
    predictor = CostPredictor()
    result = await predictor.predict(drivers)
    
    # Publish event
    await event_bus.publish(Event(
        type="prediction.generated",
        source="intelligence",
        project_id=project_id,
        data={"predicted_cost": result["cost"], "confidence": result["confidence"]}
    ))
    
    return result

# Labor estimation endpoint (merged from Eagle Analyzer)
@router.post("/predict/labor")
async def predict_labor(work_codes: list, project_id: str):
    """Predict labor hours using ML models"""
    from .labor_estimation import LaborPredictor
    predictor = LaborPredictor()
    result = await predictor.predict(work_codes)
    return result

# Event handler: Auto-predict when design completes
async def on_design_completed(event: Event):
    """Automatically generate cost prediction when design is done"""
    project_id = event.project_id
    drivers = event.data.get("drivers", {})
    # Trigger prediction
    await predict_cost(drivers, project_id)

event_bus.subscribe("design.completed", on_design_completed)

registry.register(module_def, router)
```

**Deliverable:** SignX-Intel running as platform module

#### Day 3-5: Workflow Module (EagleHub Rewrite)

**File:** `modules/workflow/__init__.py`
```python
"""
Workflow Module - Quote automation (EagleHub in Python)
"""
from fastapi import APIRouter, BackgroundTasks
from platform.registry import registry, ModuleDefinition
from platform.events import event_bus, Event

module_def = ModuleDefinition(
    name="workflow",
    version="1.0.0",
    api_prefix="/api/v1/workflow",
    ui_routes=["/workflow/dashboard"],
    events_consumed=[],
    events_published=["quote.received", "file.organized", "keyedin.updated"]
)

router = APIRouter(prefix="/api/v1/workflow", tags=["workflow"])

@router.post("/monitor/email")
async def trigger_email_check(background_tasks: BackgroundTasks):
    """Manual trigger for email monitoring (also runs on schedule)"""
    from .email_monitor import check_bid_requests
    background_tasks.add_task(check_bid_requests)
    return {"status": "monitoring"}

@router.get("/activity")
async def get_recent_activity():
    """Dashboard: Recent workflow activity"""
    from .activity import get_recent_events
    return await get_recent_events(limit=50)

registry.register(module_def, router)
```

**File:** `modules/workflow/email_monitor.py`
```python
"""
Email monitoring - Replaces EagleHub PowerShell script
"""
import asyncio
from exchangelib import Credentials, Account, Configuration, DELEGATE
from platform.events import event_bus, Event
from platform.storage import upload_file
import re

async def check_bid_requests():
    """Check Outlook for new bid requests"""
    # Connect to Outlook
    credentials = Credentials(username='brady@eaglesign.net', password='...')
    config = Configuration(server='outlook.office365.com', credentials=credentials)
    account = Account(primary_smtp_address='brady@eaglesign.net', config=config, 
                     autodiscover=False, access_type=DELEGATE)
    
    # Check BID REQUEST folders
    folders = ['BID REQUEST/Jeff', 'BID REQUEST/Joe', 'BID REQUEST/Rich', 'BID REQUEST/Mike E']
    
    for folder_path in folders:
        folder = account.inbox / folder_path
        for item in folder.filter(is_read=False).order_by('-datetime_received')[:10]:
            # Extract quote number from subject
            match = re.search(r'(\d{5})', item.subject)
            if match:
                quote_num = match.group(1)
                
                # Download attachments
                attachments = []
                for attachment in item.attachments:
                    if attachment.name.endswith('.pdf'):
                        file_url = await upload_file(
                            content=attachment.content,
                            filename=attachment.name,
                            project_id=quote_num
                        )
                        attachments.append(file_url)
                
                # Publish event
                await event_bus.publish(Event(
                    type="quote.received",
                    source="workflow",
                    project_id=quote_num,
                    data={
                        "salesperson": folder_path.split('/')[-1],
                        "subject": item.subject,
                        "attachments": attachments
                    }
                ))
                
                # Mark as read
                item.is_read = True
                item.save()
```

**Deliverable:** Email monitoring working in Python

---

## Phase 2: Module Integration (Weeks 3-4)

### Week 3: Documents Module

**Goal:** Integrate CatScale parser and BetterBeam

**File:** `modules/documents/__init__.py`
```python
"""
Documents Module - PDF parsing, markup, and CAD integration
"""
from fastapi import APIRouter, UploadFile, File
from platform.registry import registry, ModuleDefinition

module_def = ModuleDefinition(
    name="documents",
    version="1.0.0",
    api_prefix="/api/v1/documents",
    ui_routes=["/documents/:id/markup"],
    events_consumed=["quote.received"],
    events_published=["pdf.parsed", "measurements.extracted"]
)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

@router.post("/parse/vendor-pdf")
async def parse_vendor_pdf(file: UploadFile = File(...)):
    """Parse vendor PDF (CatScale)"""
    from .catscale_parser import parse_catscale_pdf
    result = await parse_catscale_pdf(file)
    return result

@router.post("/extract/measurements")
async def extract_measurements(pdf_url: str, scale: str):
    """Extract measurements from PDF"""
    from .measurement_extractor import extract_from_pdf
    measurements = await extract_from_pdf(pdf_url, scale)
    return measurements

# Event handler: Auto-parse PDFs when quote received
async def on_quote_received(event: Event):
    """Automatically parse vendor PDFs"""
    for attachment_url in event.data.get("attachments", []):
        if "nagle" in attachment_url.lower():
            # Nagle = always vendor PDF, parse it
            await parse_vendor_pdf(attachment_url)

event_bus.subscribe("quote.received", on_quote_received)

registry.register(module_def, router)
```

### Week 4: Quoting Module

**File:** `modules/quoting/__init__.py`
```python
"""
Quoting Module - Professional quote generation
"""
from fastapi import APIRouter
from platform.registry import registry, ModuleDefinition
from platform.events import event_bus, Event

module_def = ModuleDefinition(
    name="quoting",
    version="1.0.0",
    api_prefix="/api/v1/quoting",
    ui_routes=["/projects/:id/quote"],
    events_consumed=["prediction.generated", "calculations.completed"],
    events_published=["quote.generated", "quote.sent"]
)

router = APIRouter(prefix="/api/v1/quoting", tags=["quoting"])

@router.post("/generate")
async def generate_quote(project_id: str):
    """Generate professional quote PDF"""
    from .quote_generator import QuoteGenerator
    
    # Gather data from all modules
    project = await get_project(project_id)
    engineering = await get_engineering_data(project_id)  # from engineering module
    cost_prediction = await get_prediction(project_id)    # from intelligence module
    
    # Generate quote
    generator = QuoteGenerator()
    quote_pdf = await generator.generate(
        project=project,
        engineering=engineering,
        pricing=cost_prediction
    )
    
    # Publish event
    await event_bus.publish(Event(
        type="quote.generated",
        source="quoting",
        project_id=project_id,
        data={"quote_url": quote_pdf}
    ))
    
    return {"quote_url": quote_pdf}

registry.register(module_def, router)
```

---

## Phase 3: Unified UI (Weeks 5-6)

### UI Architecture

**File:** `ui/src/App.tsx`
```typescript
/**
 * SignX Studio - Unified UI
 * modern integrated platform-style navigation with module tabs
 */
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppBar, Tabs, Tab, Box } from '@mui/material';
import { ModuleRegistry } from './platform/ModuleRegistry';

// Import module UIs
import EngineeringModule from './modules/engineering';
import QuotingModule from './modules/quoting';
import WorkflowModule from './modules/workflow';
import DocumentsModule from './modules/documents';

function App() {
  const [currentModule, setCurrentModule] = React.useState('workflow');
  
  return (
    <BrowserRouter>
      {/* Top navigation - modern integrated platform style */}
      <AppBar position="static">
        <Tabs value={currentModule} onChange={(e, v) => setCurrentModule(v)}>
          <Tab label="Workflow" value="workflow" />
          <Tab label="Quoting" value="quoting" />
          <Tab label="Engineering" value="engineering" />
          <Tab label="Documents" value="documents" />
        </Tabs>
      </AppBar>
      
      {/* Module content */}
      <Box sx={{ p: 3 }}>
        <Routes>
          <Route path="/workflow/*" element={<WorkflowModule />} />
          <Route path="/quoting/*" element={<QuotingModule />} />
          <Route path="/engineering/*" element={<EngineeringModule />} />
          <Route path="/documents/*" element={<DocumentsModule />} />
        </Routes>
      </Box>
    </BrowserRouter>
  );
}

export default App;
```

**File:** `ui/src/modules/workflow/Dashboard.tsx`
```typescript
/**
 * Workflow Dashboard - Replaces EagleHub HTML dashboard
 */
import React from 'react';
import { Card, CardContent, Typography, List, ListItem } from '@mui/material';
import { useQuery } from '@tanstack/react-query';

export default function WorkflowDashboard() {
  const { data: activity } = useQuery({
    queryKey: ['workflow-activity'],
    queryFn: () => fetch('/api/v1/workflow/activity').then(r => r.json()),
    refetchInterval: 5000 // Auto-refresh every 5 seconds
  });
  
  return (
    <div>
      <Typography variant="h4">Workflow Activity</Typography>
      
      <Card sx={{ mt: 2 }}>
        <CardContent>
          <Typography variant="h6">Recent Quotes</Typography>
          <List>
            {activity?.recent_quotes?.map(quote => (
              <ListItem key={quote.id}>
                <Typography>
                  {quote.quote_number} - {quote.customer} - {quote.status}
                </Typography>
              </ListItem>
            ))}
          </List>
        </CardContent>
      </Card>
      
      <Card sx={{ mt: 2 }}>
        <CardContent>
          <Typography variant="h6">Email Monitoring</Typography>
          <Typography>
            Last check: {activity?.last_email_check}
          </Typography>
          <Typography>
            Pending: {activity?.pending_quotes} quotes
          </Typography>
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## Phase 4: End-to-End Workflow (Weeks 7-8)

### Complete Pipeline

```
1. Email arrives → Workflow module detects
2. Quote created → Event published
3. PDF attached → Documents module parses
4. Measurements extracted → Design populated
5. User reviews/edits design → Engineering module calculates
6. Calculations complete → Intelligence module predicts cost
7. Cost prediction ready → Quoting module generates proposal
8. Quote approved → KeyedIn updated
9. Order placed → Production module activated (future)
```

**File:** `platform/workflows/quote_to_cash.py`
```python
"""
Quote-to-Cash Workflow - The complete pipeline
"""
from platform.events import event_bus, Event

class QuoteToCashWorkflow:
    """Orchestrates the complete workflow"""
    
    def __init__(self):
        # Subscribe to events
        event_bus.subscribe("quote.received", self.on_quote_received)
        event_bus.subscribe("pdf.parsed", self.on_pdf_parsed)
        event_bus.subscribe("measurements.extracted", self.on_measurements_extracted)
        event_bus.subscribe("calculations.completed", self.on_calculations_completed)
        event_bus.subscribe("prediction.generated", self.on_prediction_generated)
    
    async def on_quote_received(self, event: Event):
        """Step 1: New quote email received"""
        print(f"🎯 New quote: {event.project_id}")
        # Create project in database
        # Workflow module already did this
        
    async def on_pdf_parsed(self, event: Event):
        """Step 2: PDF parsed successfully"""
        print(f"📄 PDF parsed: {event.project_id}")
        # If this was a vendor PDF, we now have line items
        
    async def on_measurements_extracted(self, event: Event):
        """Step 3: Measurements extracted from drawing"""
        print(f"📐 Measurements ready: {event.project_id}")
        # Trigger engineering calculations
        await event_bus.publish(Event(
            type="design.updated",
            source="workflow-orchestrator",
            project_id=event.project_id,
            data=event.data
        ))
        
    async def on_calculations_completed(self, event: Event):
        """Step 4: Engineering calculations done"""
        print(f"🔧 Engineering complete: {event.project_id}")
        # Already triggers intelligence module via event subscription
        
    async def on_prediction_generated(self, event: Event):
        """Step 5: Cost prediction ready"""
        print(f"💰 Cost predicted: {event.project_id}")
        # User can now generate quote
        print(f"   ✅ Ready for quote generation!")

# Initialize workflow orchestrator
workflow = QuoteToCashWorkflow()
```

---

## Success Metrics (modern integrated platform-style)

### Time Savings
| Task | Before | After | Savings |
|------|--------|-------|---------|
| **Quote Creation** | 35 min | 2 min | 94% |
| **Design Takeoff** | 30 min | 5 min | 83% |
| **Engineering** | 60 min | 10 min | 83% |
| **Cost Estimation** | 20 min | 30 sec | 97% |
| **Quote Generation** | 15 min | 1 min | 93% |
| **Total Pipeline** | 160 min | 18 min | **89%** |

### ROI Calculation
- **Projects/year:** 500
- **Time saved/project:** 142 minutes
- **Total hours saved:** 1,183 hours
- **Cost savings @ $100/hr:** $118,300/year
- **Development cost:** ~$50k (400 hours)
- **Payback period:** 5 months

---

## Next Steps

1. **Create the monorepo structure** (I can do this now)
2. **Build platform core** (registry + events)
3. **Migrate engineering module** to use plugin architecture
4. **Integrate SignX-Intel** as intelligence module
5. **Rewrite EagleHub** in Python as workflow module
6. **Build unified UI** with module navigation

**Ready to start?** I'll begin by creating the new monorepo structure and platform core.

