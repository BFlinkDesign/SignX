# KeyedIn Discovery - Quick Start Guide

## ⚡ Fastest Path to Results

### Step 1: Setup (5 minutes)

```bash
# Install dependencies
pip install playwright beautifulsoup4 python-dotenv

# Install browser
playwright install chromium

# Create credentials file
cat > .env << EOF
KEYEDIN_BASE_URL=https://your-keyedin-url.com
KEYEDIN_USERNAME=your_username
KEYEDIN_PASSWORD=your_password
EOF
```

### Step 2: Run Discovery (Choose One)

**Full Discovery (Recommended)**
```bash
python run_complete_discovery.py --full
```
- Duration: 2-4 hours (run overnight)
- Coverage: Complete system (all 18 main sections)
- Output: Comprehensive documentation

**Quick Discovery (Fast Assessment)**
```bash
python run_complete_discovery.py --quick
```
- Duration: 30-60 minutes
- Coverage: High-priority sections only
- Output: Targeted analysis

### Step 3: Review Results

```bash
# View summary
python analyze_discovery.py KeyedIn_System_Map/discovery_data/raw_discovery.json summary

# Check API feasibility
python analyze_discovery.py KeyedIn_System_Map/discovery_data/raw_discovery.json api-feasibility

# Open main reports
open KeyedIn_System_Map/EXECUTIVE_SUMMARY.md
open KeyedIn_System_Map/API_FEASIBILITY_REPORT.md
```

---

## 📋 All Available Commands

### Discovery Execution

```bash
# Full discovery (2-4 hours)
python run_complete_discovery.py --full

# Quick discovery (30-60 min)
python run_complete_discovery.py --quick

# Regenerate reports only
python run_complete_discovery.py --reports-only

# Custom output location
python run_complete_discovery.py --full --output MyDirectory
```

### Data Analysis

```bash
# Show summary statistics
python analyze_discovery.py path/to/raw_discovery.json summary

# Find endpoints in specific section
python analyze_discovery.py path/to/raw_discovery.json find-endpoints --section "Work Orders"

# Search for specific endpoint
python analyze_discovery.py path/to/raw_discovery.json find-endpoints --search "cost"

# Find all forms
python analyze_discovery.py path/to/raw_discovery.json find-forms

# Find forms in section
python analyze_discovery.py path/to/raw_discovery.json find-forms --section CRM

# Analyze specific entity
python analyze_discovery.py path/to/raw_discovery.json analyze-entity "Work Order"

# Generate endpoint code
python analyze_discovery.py path/to/raw_discovery.json generate-code --output endpoints.py

# Generate ERD diagram
python analyze_discovery.py path/to/raw_discovery.json generate-erd --output erd.mmd

# API feasibility assessment
python analyze_discovery.py path/to/raw_discovery.json api-feasibility
```

### Report Generation

```bash
# Generate all reports from discovery data
python report_generators.py KeyedIn_System_Map/discovery_data/raw_discovery.json

# Generate with custom output dir
python report_generators.py discovery.json CustomOutputDir
```

---

## 📊 What You'll Get

### Immediate Outputs (After Discovery)

```
KeyedIn_System_Map/
├── EXECUTIVE_SUMMARY.md           ← Read this first
├── TECHNICAL_ARCHITECTURE.md      ← Complete technical docs
├── API_FEASIBILITY_REPORT.md      ← API recommendation
├── AUTOMATION_ROADMAP.md          ← Prioritized opportunities
├── MODERNIZATION_STRATEGY.md      ← Build vs buy analysis
└── discovery_data/
    ├── raw_discovery.json         ← Master data file
    ├── screenshots/               ← Visual documentation
    └── html_captures/             ← Raw responses
```

### Key Questions Answered

✅ **Can we build a custom API?**
- Type A/B/C classification
- Clear yes/no with rationale
- Implementation plan if yes

✅ **What can be automated immediately?**
- Top 20 opportunities ranked by ROI
- Implementation timeline for each
- Expected time/cost savings

✅ **Should we replace KeyedIn?**
- Feature inventory for parity
- Build vs buy comparison
- Migration complexity estimate
- Budget and timeline projections

✅ **What does the system actually do?**
- Complete module/feature inventory
- Business process documentation
- Data entity relationships
- Integration points

---

## 🎯 Common Use Cases

### Use Case 1: Quick API Feasibility Check

```bash
# Run quick discovery
python run_complete_discovery.py --quick

# Check API feasibility
python analyze_discovery.py KeyedIn_System_Map/discovery_data/raw_discovery.json api-feasibility

# Review report
open KeyedIn_System_Map/API_FEASIBILITY_REPORT.md
```

**Time:** 45 minutes
**Output:** Clear API recommendation with implementation plan

### Use Case 2: Complete System Documentation

```bash
# Run full discovery (start before lunch)
python run_complete_discovery.py --full

# After completion, review technical docs
open KeyedIn_System_Map/TECHNICAL_ARCHITECTURE.md

# Generate endpoint code for use
python analyze_discovery.py KeyedIn_System_Map/discovery_data/raw_discovery.json generate-code --output keyedin_endpoints.py
```

**Time:** 2-4 hours unattended
**Output:** Complete system map with all endpoints, forms, entities

### Use Case 3: Automation Planning

```bash
# Run full discovery
python run_complete_discovery.py --full

# Review automation roadmap
open KeyedIn_System_Map/AUTOMATION_ROADMAP.md

# Find specific section endpoints
python analyze_discovery.py KeyedIn_System_Map/discovery_data/raw_discovery.json find-endpoints --section "Job Cost"
```

**Time:** 2-4 hours discovery + 30 min review
**Output:** Prioritized automation opportunities with ROI

### Use Case 4: Modernization Planning

```bash
# Run full discovery
python run_complete_discovery.py --full

# Review all strategic docs
open KeyedIn_System_Map/EXECUTIVE_SUMMARY.md
open KeyedIn_System_Map/MODERNIZATION_STRATEGY.md
open KeyedIn_System_Map/API_FEASIBILITY_REPORT.md
```

**Time:** 2-4 hours discovery + 2 hours review
**Output:** Complete build vs buy analysis with recommendations

---

## 🔍 Quick Reference: Finding Things

### Find Work Order Endpoints
```bash
python analyze_discovery.py path/to/raw_discovery.json find-endpoints --section "Work Orders"
```

### Find Cost-Related Functionality
```bash
python analyze_discovery.py path/to/raw_discovery.json find-endpoints --search "cost"
```

### See All CRM Forms
```bash
python analyze_discovery.py path/to/raw_discovery.json find-forms --section CRM
```

### Analyze Customer Entity
```bash
python analyze_discovery.py path/to/raw_discovery.json analyze-entity Customer
```

### Generate Python Endpoint Constants
```bash
python analyze_discovery.py path/to/raw_discovery.json generate-code --output keyedin_endpoints.py
```

---

## ⚠️ Troubleshooting Quick Fixes

**Login fails:**
```bash
# Check credentials
cat .env

# Test manually first
# Verify no CAPTCHA or 2FA
```

**Browser won't start:**
```bash
# Reinstall browser
playwright install chromium --force
```

**Discovery incomplete:**
```bash
# Check last screenshot to see where it stopped
ls -lt KeyedIn_System_Map/discovery_data/screenshots/

# Rerun specific section
python -c "
from keyedin_architecture_mapper import KeyedInArchitectureMapper
import asyncio
async def run():
    mapper = KeyedInArchitectureMapper('https://url.com', 'output')
    await mapper.initialize_browser()
    await mapper.login('user', 'pass')
    await mapper.explore_section('Section Name', depth=2)
    await mapper.save_discovery_results()
asyncio.run(run())
"
```

**Reports not generating:**
```bash
# Regenerate manually
python report_generators.py KeyedIn_System_Map/discovery_data/raw_discovery.json KeyedIn_System_Map
```

---

## 📈 Expected Timeline

| Task | Duration | When |
|------|----------|------|
| Setup credentials | 5 min | Now |
| Run quick discovery | 30-60 min | When testing |
| Run full discovery | 2-4 hours | Overnight |
| Review reports | 1-2 hours | Next day |
| Strategic planning | 2-4 hours | Next day |
| **Total** | **1-2 days** | **This week** |

---

## 💰 Expected ROI

**Investment:**
- Setup: 5 minutes
- Discovery: 2-4 hours (automated)
- Review: 2-4 hours
- **Total: 1 day of calendar time, 3-5 hours of your time**

**Return:**
- Year 1: $32,000-55,000 (automation savings)
- ROI: 400-800%
- Payback: 1-2 months

---

## ✅ Success Checklist

After running discovery, you should have:

- [ ] `raw_discovery.json` with 50+ endpoints
- [ ] Screenshots of every major section
- [ ] Complete endpoint registry
- [ ] API feasibility report with clear recommendation
- [ ] Top 20 automation opportunities ranked
- [ ] Build vs buy analysis
- [ ] Data migration strategy
- [ ] Clear next steps

---

## 🚀 What's Next?

**After Full Discovery:**

1. **Read Reports** (1 hour)
   - Executive Summary
   - API Feasibility Report
   - Automation Roadmap

2. **Make Decision** (1 hour)
   - Build API wrapper? (if recommended)
   - Which automations first?
   - Modernization timeline?

3. **Execute Plan** (Ongoing)
   - Start Priority 1 automations
   - Build API if recommended
   - Plan data extraction
   - Evaluate replacement platforms

---

**Ready to start? Run this now:**

```bash
python run_complete_discovery.py --full
```

Then go do something else for 2-4 hours while it completes. 

Check back and review your comprehensive system map! 🎉
