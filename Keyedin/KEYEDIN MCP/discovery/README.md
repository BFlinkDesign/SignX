# KeyedIn Complete System Architecture Mapping

**Comprehensive discovery system for reverse-engineering and documenting the entire KeyedIn legacy platform.**

## 🎯 Objective

Create complete technical and strategic documentation of KeyedIn to enable:

1. **API Development Decisions** - Determine if custom API wrapper is feasible
2. **Platform Modernization** - Build feature parity requirements for replacement
3. **Automation Roadmap** - Identify and prioritize automation opportunities
4. **Knowledge Preservation** - Document tribal knowledge before it's lost

## 📋 What This System Does

### Automated Discovery
- Systematically navigates every section of KeyedIn
- Captures all CGI endpoints with parameters
- Extracts form schemas and validation rules
- Identifies business entities and relationships
- Takes screenshots for visual documentation
- Saves HTML responses for offline analysis

### Comprehensive Reports Generated

**Technical Documentation:**
- `TECHNICAL_ARCHITECTURE.md` - Complete CGI architecture, endpoints, forms, entities
- `endpoints_registry.py` - Python constants file with all discovered endpoints
- `entity_relationships.mmd` - Mermaid ERD diagram

**Strategic Documentation:**
- `API_FEASIBILITY_REPORT.md` - Type A/B/C classification with recommendations
- `AUTOMATION_ROADMAP.md` - Prioritized opportunities with ROI estimates
- `MODERNIZATION_STRATEGY.md` - Build vs buy analysis with migration plan
- `EXECUTIVE_SUMMARY.md` - High-level overview for decision-making

**Supporting Data:**
- `discovery_data/screenshots/` - Visual documentation of every section
- `discovery_data/html_captures/` - Raw HTML for offline analysis
- `discovery_data/form_schemas/` - JSON schema for every form
- `discovery_data/raw_discovery.json` - Complete structured exploration data

## 🚀 Quick Start

### Prerequisites

```bash
# Install dependencies
pip install playwright beautifulsoup4 python-dotenv

# Install Playwright browsers
playwright install chromium
```

### Setup Credentials

Create a `.env` file:

```env
KEYEDIN_BASE_URL=https://your-keyedin-instance.com
KEYEDIN_USERNAME=your_username
KEYEDIN_PASSWORD=your_password
```

### Run Discovery

**Option 1: Full Discovery (Recommended for complete analysis)**
```bash
python run_complete_discovery.py --full
```
- **Duration:** 2-4 hours unattended
- **Coverage:** Every main section + subsections (2 levels deep)
- **Output:** Complete system map

**Option 2: Quick Discovery (For rapid assessment)**
```bash
python run_complete_discovery.py --quick
```
- **Duration:** 30-60 minutes
- **Coverage:** High-priority sections only (Work Orders, CRM, Projects, Inventory, Job Cost)
- **Output:** Targeted analysis of critical business areas

**Option 3: Reports Only (From existing data)**
```bash
python run_complete_discovery.py --reports-only
```
- **Use When:** You already have discovery data and want to regenerate reports

### Custom Output Directory

```bash
python run_complete_discovery.py --full --output MyCustomDirectory
```

## 📂 Output Structure

```
KeyedIn_System_Map/
├── README.md                          # This file
├── EXECUTIVE_SUMMARY.md               # High-level strategic overview
├── TECHNICAL_ARCHITECTURE.md          # Complete technical documentation
├── API_FEASIBILITY_REPORT.md          # Type A/B/C assessment + recommendations
├── AUTOMATION_ROADMAP.md              # Prioritized opportunities with ROI
├── MODERNIZATION_STRATEGY.md          # Build vs buy analysis
├── code/
│   ├── keyedin_architecture_mapper.py # Main discovery agent
│   ├── report_generators.py           # Report generation system
│   ├── endpoints_registry.py          # Generated Python constants
│   └── database_schema.sql            # Proposed modern schema
├── diagrams/
│   ├── entity_relationships.mmd       # Mermaid ERD
│   └── system_architecture.mmd        # Architecture diagram
└── discovery_data/
    ├── screenshots/                   # Visual documentation
    │   ├── 00_logged_in_home.png
    │   ├── section_work_orders.png
    │   └── ...
    ├── html_captures/                 # Raw HTML responses
    │   ├── 00_logged_in_home.html
    │   └── ...
    ├── form_schemas/                  # JSON form definitions
    │   ├── work_orders_create_form.json
    │   └── ...
    ├── table_structures/              # Data table schemas
    └── raw_discovery.json             # Master discovery data file
```

## 🔍 What Gets Discovered

### Main Sections Explored
- CRM
- Project Management
- Estimating and Proposals
- Sales Order Entry
- Shipping Tracking
- Sales Analysis
- Purchasing
- Inventory and Parts
- Job Cost
- Material Requirements Planning
- Production (Shop Floor Control)
- Resource Scheduling
- Labor and Payroll Processing
- Accounts Payable
- Accounts Receivable
- Report Administration
- Administration
- System Management

### Data Captured Per Section
- **Navigation Structure:** Menu hierarchy and entry points
- **Endpoints:** All CGI URLs with parameters and purposes
- **Forms:** Field schemas, validation rules, defaults, options
- **Data Tables:** Headers, structures, entity attributes
- **Workflows:** Multi-step processes and data flows
- **Operations:** Available CRUD operations per entity
- **Reports:** Export formats and parameters
- **Relationships:** Links between entities and modules

## 📊 Expected Outcomes

### After Full Discovery

**Technical Insights:**
- 50-150+ discoverable endpoints cataloged
- 20-50+ form schemas documented
- 10-30+ business entities identified
- Complete CGI architecture mapped
- Session management understood
- API feasibility clearly determined

**Strategic Insights:**
- Type A/B/C architecture classification
- Clear API wrapper recommendation (build/don't build)
- Top 20 automation opportunities ranked by ROI
- Feature parity requirements for replacement
- Data migration complexity assessment
- Build vs buy recommendation with rationale

**Timeline & ROI:**
- Discovery execution: 2-4 hours
- Report generation: Automatic
- **Total investment: 1 day**
- **ROI: 400-800% in Year 1** (from automation savings)
- **Payback period: 1-2 months**

## 🎛️ Advanced Usage

### Explore Specific Section Only

```python
from keyedin_architecture_mapper import KeyedInArchitectureMapper

mapper = KeyedInArchitectureMapper("https://your-url.com", "output_dir")
await mapper.initialize_browser()
await mapper.login("username", "password")
await mapper.explore_section("Work Orders", depth=3)  # Go 3 levels deep
await mapper.save_discovery_results()
```

### Generate Custom Reports

```python
from report_generators import TechnicalArchitectureReport, APIFeasibilityReport

# Generate individual reports
tech_report = TechnicalArchitectureReport("discovery_data/raw_discovery.json", "output")
tech_report.generate()

api_report = APIFeasibilityReport("discovery_data/raw_discovery.json", "output")
api_report.generate()
```

### Extract Specific Data from Discovery

```python
import json

with open('KeyedIn_System_Map/discovery_data/raw_discovery.json', 'r') as f:
    data = json.load(f)

# Get all Work Order endpoints
wo_endpoints = [e for e in data['endpoints'] if 'work order' in e['section'].lower()]

# Get all forms in CRM section
crm_forms = [f for f in data['forms'] if f['section'] == 'CRM']

# Get discovered entities
entities = data['entities']
```

## 🔧 Customization

### Modify Discovery Depth

Edit `keyedin_architecture_mapper.py`:

```python
# Default: depth=2 (main section + 2 subsection levels)
await mapper.explore_section(section, depth=3)  # Go deeper

# Adjust wait times for slower systems
await self.page.wait_for_load_state('networkidle', timeout=60000)  # 60 sec
```

### Add Custom Collectors

Create new collectors in `collectors/` directory:

```python
class CustomDataCollector:
    def collect(self, page, section):
        # Custom data extraction logic
        pass
```

### Modify Report Templates

Edit `report_generators.py` to customize output format, sections, or analysis.

## 🛡️ Security Considerations

**Credentials:**
- Store in `.env` file (never commit to git)
- Use environment variables in production
- Consider using secrets manager for enterprise

**Discovery Process:**
- Read-only operations (no data modifications)
- Respects existing authentication/authorization
- Session cleanup after completion
- Rate-limited to avoid overwhelming the system

**API Wrapper (if built):**
- Implement input validation and sanitization
- Add rate limiting and throttling
- Use audit logging for compliance
- Encrypt credentials at rest

## 📈 Success Metrics

**Discovery Quality:**
- ✅ 90%+ of main sections explored
- ✅ 100+ endpoints documented
- ✅ All critical workflows mapped
- ✅ Clear API recommendation with rationale

**Actionable Outcomes:**
- ✅ Can make informed build vs buy decision
- ✅ Can estimate API wrapper development effort
- ✅ Can prioritize automation investments
- ✅ Can plan data migration strategy
- ✅ Can justify modernization budget

## 🐛 Troubleshooting

**Login Fails:**
```bash
# Verify credentials
echo $KEYEDIN_USERNAME
echo $KEYEDIN_BASE_URL

# Test manually in browser first
# Check for CAPTCHA or 2FA requirements
```

**Browser Timeout:**
```python
# Increase timeout in keyedin_architecture_mapper.py
await self.page.wait_for_load_state('networkidle', timeout=120000)  # 2 min
```

**Missing Sections:**
```python
# Add missing sections to main_sections list
self.main_sections.append("Your Missing Section")
```

**Incomplete Discovery:**
```python
# Run targeted rediscovery
python run_complete_discovery.py --quick
# Then merge with existing data
```

## 📞 Support

**Common Issues:**
1. **Login fails:** Check credentials, test manually, verify no CAPTCHA
2. **Sections not found:** Verify section names match navigation exactly
3. **Slow performance:** Increase timeouts, reduce depth level
4. **Missing data:** Check screenshots to verify page loaded correctly

**Logs:**
- Console output during execution
- Check `discovery_data/screenshots/` to verify what was captured
- Review `discovery_data/html_captures/` to see raw responses

## 🎯 Next Steps After Discovery

### 1. Review Reports
- Read `EXECUTIVE_SUMMARY.md` for high-level overview
- Study `API_FEASIBILITY_REPORT.md` for technical recommendation
- Analyze `AUTOMATION_ROADMAP.md` for prioritized opportunities

### 2. Make Strategic Decision
- **If Type A/B:** Proceed with API wrapper development
- **If Type C:** Continue with Playwright MCP approach
- **Either way:** Use discovery data for automation planning

### 3. Execute Automation Plan
- Start with Priority 1 quick wins
- Build API wrapper if recommended
- Extract historical data while system accessible
- Plan modernization timeline

### 4. Continuous Documentation
- Update discovery as KeyedIn changes
- Document new endpoints as discovered
- Maintain entity relationship diagram
- Track automation ROI vs. projections

## 🏆 Expected Business Value

**Immediate (0-30 days):**
- Complete system understanding
- Clear modernization path
- API feasibility determination
- Automation opportunity identification

**Short-term (1-6 months):**
- 10-20 automations deployed
- 200-400 hours saved annually
- Reduced manual errors
- Better data visibility

**Long-term (6-24 months):**
- Modern platform selection or custom build
- Complete data migration
- Legacy system phase-out
- Competitive advantage from automation

**Financial Impact:**
- **Investment:** $5,000-8,000 (Year 1 with API wrapper)
- **Return:** $32,000-55,000 annually
- **Net Benefit:** $24,000-47,000 (Year 1)
- **ROI:** 400-800%

---

## 📝 License & Usage

This system is designed for internal business use at Eagle Sign Co. for legitimate system documentation and automation purposes.

**Usage Guidelines:**
- Authorized personnel only
- Document system architecture
- Enable automation and modernization
- Respect data privacy and security
- Comply with employment agreements

---

## ✨ Credits

Designed for Eagle Sign Co. to document the KeyedIn legacy system and enable strategic modernization planning.

**Built with:**
- Playwright (browser automation)
- BeautifulSoup (HTML parsing)
- FastAPI (future API wrapper)
- Mermaid (diagrams)
- Python 3.8+

---

**Ready to map your entire KeyedIn system? Start with:**

```bash
python run_complete_discovery.py --full
```

**Questions or issues? Review the Troubleshooting section or consult the generated reports.**
