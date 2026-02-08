# SignX: The AI Operating System for Signage
## "Lego Builder" Architecture Plan (Revised: Autonomous & PWA)

**Vision:** A completely autonomous operating system. The goal is **Zero-Click Operations**. The system should infer status, route work, and notify humans only when physical intervention is required.

**Delivery:** A **Progressive Web App (PWA)**. Installs on any device (Shop Tablet, Install Phone, Desktop) and works offline.

---

## 1. Core Architecture: The "Main Engine" (Orchestrator)

The **Main Engine** is the brain. It doesn't do the math or weld the steel; it knows which module does. It uses an Agentic Workflow (powered by Gemini) to break down user requests into sub-tasks.

### 1.1 The "Brain" (AI Orchestrator)
*   **Role:** Intent classification, task delegation, and context management.
*   **Input:** Natural language (e.g., "I need a 20ft pylon for Starbucks in Austin. Quote it, engineer it, and schedule the install.")
*   **Output:** A coordinated execution plan across modules.
*   **Tech:** LangChain / Semantic Kernel + Gemini 1.5 Pro.

### 1.2 The "Memory" (Central Context)
*   **Role:** Shared state for the entire lifecycle of a job.
*   **Components:**
    *   **Project Graph:** A knowledge graph linking Client -> Site -> Design -> Engineering -> Quote -> Job -> Invoice.
    *   **Vector Store:** RAG for historical data (past quotes, engineering specs, emails).

---

## 2. The Modules ("Lego Blocks")

Each module is a self-contained service with a clear API. The Frontend (`SignX-Studio`) visualizes these as interactive blocks.

### 🧱 Block A: Engineering (The "APEX" Solver)
*   **Status:** **Active** (Existing `services/api`).
*   **Function:** Structural analysis, code compliance (ASCE/IBC), optimization.
*   **Expansion:** Add "Generative Design" – AI suggests 3 valid designs based on site constraints.

### 🧱 Block B: Cost & Estimation (The "Ledger")
*   **Status:** **Primitive** (YAML files).
*   **Goal:** A dynamic cost engine.
*   **Sub-Modules:**
    *   **Material Database:** Real-time pricing (Steel, Aluminum, LEDs, Vinyl).
    *   **Labor Engine:** Shop rates, install crew rates, travel time calculators.
    *   **Margin Manager:** Dynamic markup rules based on client tier and job complexity.

### 🧱 Block C: Sales & CRM (The "Front Office")
*   **Status:** **Partial** (KeyedIn integration).
*   **Goal:** Automated sales pipeline.
*   **Features:**
    *   **Lead Gen:** Scrape permits/new business filings.
    *   **Proposal Builder:** AI generates PDF proposals with renders and specs.
    *   **Contract Management:** DocuSign integration.

### 🧱 Block D: Job Shop (The "Autonomous Factory")
*   **Status:** **Missing**.
*   **Goal:** Zero-click manufacturing execution. **NO MANUAL KANBAN.**
*   **Automation Strategy:**
    *   **Passive Triggers:** 
        *   "Material Ordered" -> Triggered automatically when Quote is signed.
        *   "Fabrication Started" -> Triggered when CNC/Cut files are downloaded.
    *   **QR Travelers:** Parts have QR codes. A single scan by a worker (or machine vision) updates status.
    *   **Inventory:** Deducts materials automatically based on BOM when fabrication starts.

### 🧱 Block E: Field Services (The "Install PWA")
*   **Status:** **Missing**.
*   **Goal:** Offline-capable PWA for crews.
*   **Features:**
    *   **Smart Dispatch:** AI routes crews based on GPS and job readiness.
    *   **Augmented Reality (AR):** Hold phone up to see where the sign goes (using the Engineering coordinates).
    *   **One-Tap Closeout:** Take a photo -> AI verifies it matches the proof -> Invoice sent automatically.

---

## 3. The Frontend: SignX Studio ("Lego Builder" Interface)

The UI should feel like a CAD/Design tool, not a spreadsheet.

*   **Canvas View:** The central workspace where users "build" the job.
    *   Drag a "Site" block onto the canvas.
    *   Snap a "Pylon Sign" block onto the Site.
    *   Connect a "Quote" block to the Sign.
*   **Visualizers:**
    *   **3D Viewer:** WebGL (Three.js/React-Three-Fiber) preview of the sign.
    *   **Map View:** Satellite view of the install site (Google Maps API).
*   **Tech Stack:** Next.js, React Flow (for the node/block editor), Tailwind CSS.

---

## 4. Implementation Roadmap

### Phase 1: The Foundation (Weeks 1-4)
1.  **Initialize SignX Studio:** Set up the Next.js frontend with the "Canvas" UI concept.
2.  **Cost Database Upgrade:** Migrate `pricing.yaml` to a Postgres schema (`materials`, `labor`, `overheads`).
3.  **AI Orchestrator V1:** Build a simple agent that can route "Quote this" to the Engineering + Cost blocks.

### Phase 2: The Sales Machine (Weeks 5-8)
1.  **Proposal Generator:** Create a PDF engine that combines Engineering + Cost data into a client-ready document.
2.  **CRM Sync:** Deepen the KeyedIn integration to sync contacts and pipeline stages.

### Phase 3: The Shop Floor (Weeks 9-12)
1.  **Job Board:** Build the Kanban view for manufacturing status.
2.  **Inventory:** Basic material tracking and deduction.

### Phase 4: Field & Finish (Weeks 13+)
1.  **Mobile Web App:** For install crews to view job details and upload photos.
2.  **Analytics:** Dashboards for profitability and efficiency.

---

## 5. Immediate Next Steps (Action Plan)

1.  **PWA Configuration:** Configure `SignX-Studio` as an offline-capable PWA.
2.  **Design the Data Model:** Create the SQL schema for the **Cost Database**.
3.  **Prototype the Canvas:** Implement a basic React Flow interface to demonstrate the "Lego" concept.
