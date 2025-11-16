# Glossary

Complete glossary of terms for SIGN X Studio Clone.

## Technical Terms

### Envelope

A standardized API response format that includes:
- `data`: The actual response data
- `assumptions`: Warnings, notes, or conditions
- `confidence`: Confidence score (0.0-1.0)
- `trace`: Complete audit trail
- `content_sha256`: Deterministic hash of response

### Confidence Score

A numeric value (0.0-1.0) indicating system confidence in calculations:
- **0.9-1.0**: High confidence (green badge)
- **0.7-0.89**: Medium confidence (yellow badge)
- **0.5-0.69**: Low confidence (orange badge)
- **<0.5**: Very low confidence (red badge, review required)

### Content SHA256

SHA256 hash of the response content (rounded to 3 decimals, deterministic). Used for:
- Response caching
- Change detection
- Verification

### ETag

Entity tag used for optimistic locking. Prevents concurrent update conflicts:
- GET requests return current ETag
- PUT requests require `If-Match` header with ETag
- Returns 412 if ETag doesn't match

### Idempotency

Property ensuring repeated requests have the same effect. Used to prevent duplicate submissions:
- Include `Idempotency-Key` header
- Same key returns cached response
- TTL: 24 hours

### Deterministic

Guarantee that same inputs produce same outputs:
- All floats rounded to 3 decimals
- Lists sorted deterministically (seeded)
- Content SHA256 for verification

## Engineering Terms

### ASCE 7-16

American Society of Civil Engineers Standard 7-16 (Minimum Design Loads). Used for:
- Wind speed determination
- Load combinations
- Design procedures

### AISC 360-16

American Institute of Steel Construction Specification 360-16. Used for:
- Steel member design
- Connection design
- Structural analysis

### ACI 318

American Concrete Institute Building Code 318. Used for:
- Concrete design
- Anchor design
- Foundation design

### Baseplate

A steel plate connecting a pole to a foundation:
- Distributes loads to foundation
- Provides connection for anchors
- Sized based on moment and loads

### Direct Burial

Foundation type where footing is buried directly in ground:
- No visible baseplate
- Simpler installation
- Suitable for good soil conditions

### Footing

Concrete foundation element supporting the structure:
- Circular (cylindrical) shape
- Sized based on loads and soil
- Depth calculated to satisfy design requirements

### Safety Factor

Ratio of capacity to demand:
- **Overturning**: Moment capacity / Applied moment
- **Bearing**: Soil capacity / Applied pressure
- **Sliding**: Friction / Applied shear
- Target: ≥2.0 for all factors

### Overturning

Tendency of structure to rotate about base:
- Resisted by foundation weight and soil
- Safety factor: ≥2.0

### Bearing Capacity

Maximum pressure soil can support:
- Based on soil properties
- Safety factor: ≥2.0

### Sliding

Horizontal movement of structure:
- Resisted by friction
- Safety factor: ≥2.0

### Uplift

Upward force on foundation:
- Resisted by foundation weight
- Safety factor: ≥2.0

### Exposure Category

Wind exposure classification (B, C, D):
- **B**: Suburban, wooded areas
- **C**: Open terrain, grasslands
- **D**: Waterfront, hurricane-prone

### Wind Speed

Basic wind speed in mph:
- Determined from ASCE 7-16 maps
- Varies by location
- Used in load calculations

## System Terms

### Project

A sign design project containing:
- Project metadata (name, customer, site)
- Design parameters (cabinet, pole, foundation)
- Status (draft, estimating, submitted, accepted, rejected)

### Stage

One of 8 steps in the project workflow:
1. Overview
2. Site & Environment
3. Cabinet Design
4. Structural Design
5. Foundation Type
6. Foundation Design (Direct Burial)
7. Baseplate Design
8. Review & Submit

### Derive

Automatic calculation of geometry:
- Cabinet dimensions → Area, weight, center of gravity
- Updates in real-time (300ms debounce)
- Confidence scored

### Submission

Process of submitting project for review:
- Changes status: `estimating` → `submitted`
- Triggers report generation
- Notifies PM system (if integrated)

### Payload

Complete design snapshot:
- All design parameters
- SHA256 hash for verification
- Stored for audit trail

### Constants Version

Version tracking for calculation packs:
- Format: "pricing:v1:abc123,exposure:v1:def456"
- SHA256 of each pack
- Included in Envelope trace

## Acronyms

### RTO (Recovery Time Objective)

Maximum acceptable downtime:
- **Target**: <4 hours
- Time to restore service after failure

### RPO (Recovery Point Objective)

Maximum acceptable data loss:
- **Target**: <15 minutes
- Data restored to point within 15 minutes of failure

### SLA (Service Level Agreement)

Agreement defining service levels:
- Uptime targets (99.9%)
- Response times (<4 hours for P1)
- Resolution times (<24 hours for P1)

### SLO (Service Level Objective)

Internal target for service level:
- More aggressive than SLA
- Used for internal measurement

### MTTR (Mean Time To Recovery)

Average time to recover from failure:
- **Target**: <4 hours
- Measures incident response speed

### MTTF (Mean Time To Failure)

Average time between failures:
- **Target**: >720 hours (30 days)
- Measures system reliability

### P0/P1/P2/P3

Priority levels for incidents:
- **P0**: Critical (system down)
- **P1**: High (major feature broken)
- **P2**: Medium (minor issue)
- **P3**: Low (enhancement)

### API (Application Programming Interface)

Interface for programmatic access:
- REST API with JSON responses
- Authentication via API keys or JWT
- Rate limited (100 req/min)

### PDF (Portable Document Format)

Report format:
- 4-page engineering reports
- Deterministic (same inputs → same PDF)
- SHA256 verified

---

**More Terms:**
- [**FAQ**](frequently-asked-questions.md) - Common questions
- [**Best Practices**](best-practices.md) - Usage guidelines

