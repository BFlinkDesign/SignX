# APEX Sign Calculation Service

Deterministic sign structure design pipeline: wind loads → member sizing → foundation → anchors → reports.

## Architecture

**Mission**: Given sign geometry, site conditions, and jurisdiction/standard, return a compliant structural design with safety factors, reports, and full traceability.

**Design Principles**:
- Deterministic calculations (no RNG; reproducible outputs)
- Standards packs with SHA256 for provenance
- Canonical envelope with confidence, assumptions, citations
- Monotonic design checks (higher loads → heavier sections, deeper embed)

## Contracts

`SignDesignRequest` includes:
- `jurisdiction`: "US" | "EU"
- `standard`: `{code: "ASCE7" | "EN1991", version: str, importance: "I"|"II"|"III"}`
- `site`: exposure, elevation, soil
- `sign`: dimensions (ft), centroid height, weight
- `support_options`: ["pipe", "W", "tube"] (ordered preference)
- `embed`: `{"type": "direct" | "baseplate"}`
- `constraints`: optional max foundation dia/embed depth

`SignDesignResponse` returns:
- `result.selected`: support section + foundation + safety factors
- `result.loads`: wind pressures/forces
- `result.reports`: blob_refs for calc.json, PDF, DXF
- `assumptions`: normalization notes, pack used
- `confidence`: 0..1 based on margins
- `trace`: {data_sha256, inputs_sha256, standards_pack_sha256, code_version}

## Standards Packs

Packs live in `apex_signcalc/packs/` and are versioned by SHA256:
- `us.asce7-16/wind.yaml`, `combos.yaml` — ASCE 7-16 wind coefficients
- `eu.en1991-1-4/wind.yaml`, `combos.yaml` — EN 1991-1-4 wind
- `materials.yaml` — steel/aluminum properties
- `anchors.yaml` — bolt patterns, edge distances
- `nddot/sequences.perf_tube.json` — fabrication sequences

## Catalogs

Member selection iterates hardcoded catalogs + AISC Excel (`info/aisc-shapes-database-v16.0_a1085.xlsx`):
- **Pipe**: ASTM A53, 36 ksi fy
- **W-shapes**: AISC v16.0 (loaded from Excel when available)
- **HSS tubes**: AISC v16.0 Square/Rectangular (loaded from Excel)

## Algorithms

### Wind Loads (ASCE 7)
```
qz = 0.00256 * Kz * Kzt * Kd * V^2 * G
Kz interpolated by exposure (B/C/D) and height from pack tables
F_sign = qz * cf * area
```

### Wind Loads (EN 1991)
```
qb = 0.5 * rho * v_b^2
q_p(z) = c_e(z) * c_{e,T} * qb
F_sign = c_s * c_d * c_f * q_p(z_e) * A_ref
```

### Member Selection
Iterate support_options families in order; for each, load catalog, check every section ascending by weight:
- Bending: `fb = M / Sx <= 0.6*fy` → IR
- Deflection: `delta ~ V*L^3/(48*E*I) <= L/120`

Return first passing section.

### Foundation (Direct Embed)
Broms-style lateral capacity (simplified):
- `dia_in = f(sqrt(M))`
- `depth_in = f(sqrt(M))`
- Respect constraints: if `max_dia` hit, deepen; if `max_embed` hit, warn
- S.F.s monotone with size: `OT_sf, BRG_sf, SLIDE_sf, UPLIFT_sf`

### Anchors/Baseplate
If `embed.type == "baseplate"`:
- Pattern: 4-anchor symmetric
- Check tension/shear per ACI-style rules
- Return schedule ref

### Rebar Schedules
Bucketed by dia/depth:
- ≥36" dia or 72" depth → #5@12"
- ≥24" dia or 48" depth → #4@12"
- Otherwise → #4@18"

### Reports
- `calc.json`: full payload with packs_sha
- `calc.pdf`: WeasyPrint HTML → PDF
- `calc.dxf`: ezdxf foundation plan/section/rebar table

## API Endpoints

- `GET /healthz` — service health
- `GET /schemas/sign-1.0.json` — request schema
- `GET /packs` — list all packs with SHA256
- `POST /v1/signs/design` — design pipeline

## Tests

```bash
# Unit tests
python -m pytest services/signcalc-service/tests/

# Via compose
make up
curl http://localhost:8002/healthz
curl http://localhost:8002/packs | jq
```

## Failure Modes

- Missing pack data → abstain with explicit missing keys
- Contradictory constraints (tiny dia + shallow embed) → 422 with reasons
- No passing section → 422 with "no passing support section"
- Catalog gaps → return alternates with coverage deficit

## Future Enhancements

- Agent-based pipeline (wind → member → foundation → anchors → report)
- Temporal hooks for stateful workflows
- Monte Carlo with seeded RNG by task_id
- AISC Table 6-1 interaction surface lookup
- Local sign ordinance hooks (setbacks, curfews)

## Citations

- ASCE 7-16: Minimum Design Loads and Associated Criteria for Buildings and Other Structures
- AISC 2022 Specification for Structural Steel Buildings
- AISC v16.0 Manual and Companion Tables
- NFPA 70 (NEC Article 600) for electric signs
- UL 48, UL 879/879A, UL 969
- EN 1991-1-4: Wind actions

