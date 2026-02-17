# SIGNX Session State — 2026-02-17

## Current Sprint: C/D/E (Estimators + Margin Fixes + Integrations)

### Completed This Session
- [x] HSS preference fix in supports_pipe.py — select_member() now defaults to ['HSS_square', 'pipe', 'W']
- [x] POLLIT correction factors added to abc_engine.py (provisional, 461 warehouse jobs)
- [x] ALULIT correction factors added to abc_engine.py (low confidence, 31 warehouse jobs)
- [x] estimate_pylon() — Full pylon/pole estimator with crane install, deep footings, heavy structural
- [x] estimate_cabinet() — Aluminum cabinet estimator (wall/roof/pipe mount)
- [x] /api/estimate/pylon endpoint wired in app.py
- [x] /api/estimate/cabinet endpoint wired in app.py
- [x] Pylon + Cabinet tabs added to dashboard (index.html)

### Previous Session Completed (2026-02-16)
- [x] Phases 1-5 resurrection plan executed
- [x] wind_asce7.py — Full ASCE 7-22 Section 29.3 (3 loading cases)
- [x] foundation_embed.py — Broms/Hansen/Czerniak methods
- [x] anchors_baseplate.py — ACI 318-19 Chapter 17
- [x] supports_pipe.py — Full AISC 360-22 LRFD (788 lines)
- [x] sections.py — 19-section AISC catalog (pipe/W/HSS)
- [x] abc_engine.py — 4 estimators (channel letters, monument, awning, removal)
- [x] SpaceX-style dashboard with 5 tabs
- [x] All 13 API endpoints passing smoke tests
- [x] SIGNX-MASTER-SEQUENCE.md (642 lines, 10 tracks)

### Working Estimators (7 total)
| Estimator | Sign Types | Unit | Confidence | Source |
|-----------|-----------|------|------------|--------|
| estimate() | CLLIT, CLNON | PF | HIGH (442 jobs) | ABC Sections 4/10B |
| estimate_monument() | MONDF, MONSF | SF | HIGH (188 jobs) | ABC Section 2 + warehouse |
| estimate_awning() | AWNNON | SF | LOW (48 jobs) | Eagle actuals #11530/#11532 |
| estimate_removal() | All types | per-job | MODERATE | Install floor x 0.65 x 2 |
| estimate_pylon() | POLLIT | SF | MODERATE (461 jobs) | ABC Section 2 + POLLIT corrections |
| estimate_cabinet() | ALULIT, ALUNON | SF | LOW (31 jobs) | ABC Section 2 + ALULIT corrections |

### API Endpoints (15 total)
| Method | Path | Function |
|--------|------|----------|
| POST | /api/estimate | Channel letter estimation |
| POST | /api/estimate/monument | Monument estimation |
| POST | /api/estimate/awning | Awning estimation |
| POST | /api/estimate/removal | Removal estimation |
| POST | /api/estimate/pylon | Pylon/pole estimation |
| POST | /api/estimate/cabinet | Cabinet estimation |
| POST | /api/extract-pf | PDF PF extraction |
| POST | /api/structural/wind | ASCE 7-22 wind load |
| POST | /api/structural/foundation | Foundation design |
| POST | /api/structural/anchors | Anchor/baseplate design |
| POST | /api/structural/member-check | AISC 360 member check |
| POST | /api/structural/member-select | Lightest member selection |
| POST | /api/structural/full-design | Complete structural design |
| GET | /api/structural/sections | AISC section catalog |

### Dashboard Tabs (7 total)
Channel Letters | Monument | Awning | Removal | Pylon | Cabinet | Engineering

### Still Missing (Sprint C Remaining)
- [ ] Directional (DIRECT) — 162 warehouse jobs, no ABC section, needs [PROVISIONAL]
- [ ] Dimensional Letters (GEMINI) — 115 jobs, flat-rate candidate
- [ ] LED Retrofit (LED) — 53 jobs, install-focused
- [ ] Post & Panel — from Accutrack, no warehouse data yet
- [ ] Routed Face — from Accutrack
- [ ] Wireway — from Accutrack

### Sprint D: Margin Leaks
- [ ] CLLIT 0270 Misc Fab (+56.88h variance, $843K leak) — needs investigation
- [ ] Installation recalibration across all types
- [ ] OT estimation refinement
- [ ] CNC discount factor calibration

### Sprint E: Integrations
- [ ] KeyedIn ERP write-back (push estimates as work orders)
- [ ] Notion API bi-directional sync
- [ ] SignX-Intake Power Automate wiring

### Key Architecture Decisions
- **LRFD over ASD**: Code uses AISC 360-22 LRFD. Both are PE-stampable. ASD crosscheck planned for validation.
- **HSS preferred**: select_member() defaults to HSS_square > pipe > W per Eagle standard practice
- **Section modulus**: Zx (plastic) for compact yielding, Sx (elastic) for LTB. PE-valid either way.
- **Margin framework**: ABC rates = pricing, warehouse = benchmark, delta = margin indicator

### File Sizes
| File | Lines | Description |
|------|------:|-------------|
| abc_engine.py | ~2100 | 7 estimators, 51 work codes, correction factors |
| app.py | ~620 | 15 endpoints, request models, formatters |
| index.html | ~1800 | 7-tab dashboard, SpaceX-style |
| supports_pipe.py | ~790 | Full AISC 360-22 LRFD member design |
| wind_asce7.py | ~400 | ASCE 7-22 Section 29.3 |
| foundation_embed.py | ~350 | Broms/Hansen/Czerniak |
| anchors_baseplate.py | ~300 | ACI 318-19 Chapter 17 |
| sections.py | ~380 | AISC section catalog |

### Run Commands
```bash
cd C:\Users\Brady.EAGLE\Desktop\SIGNX\signx-takeoff
python app.py  # Starts on port 8765
# Open http://localhost:8765
```

### Smoke Test
```bash
curl -X POST http://localhost:8765/api/estimate/pylon -H "Content-Type: application/json" -d '{"width_ft":8,"height_ft":6,"num_faces":2,"pole_height_ft":25}'
curl -X POST http://localhost:8765/api/estimate/cabinet -H "Content-Type: application/json" -d '{"width_ft":6,"height_ft":4,"illuminated":true}'
```
