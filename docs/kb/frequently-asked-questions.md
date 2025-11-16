# Frequently Asked Questions (FAQ)

50+ common questions and answers for SIGN X Studio Clone.

## Getting Started

### Q1: What is SIGN X Studio Clone?

**A:** SIGN X Studio Clone is a modern sign design and engineering platform that replaces the legacy CalcuSign system. It provides automated calculations, instant geometry derivations, and automated PDF report generation.

### Q2: How do I access the system?

**A:** Access the system at https://app.example.com. Log in with your email and password, or use your API key for programmatic access.

### Q3: What browsers are supported?

**A:** Supported browsers:
- Chrome/Edge (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)

### Q4: Do I need special software installed?

**A:** No. SIGN X Studio is a web-based application. You only need a modern web browser.

## Projects

### Q5: How do I create a new project?

**A:** Click "New Project" button, fill in the project name, customer, and site address, then click "Create". The project will be created in draft status.

### Q6: Can I delete a project?

**A:** Projects cannot be deleted, but you can archive them. Contact support if you need to delete a project for compliance reasons (GDPR).

### Q7: How do I share a project with others?

**A:** Projects are tied to your account. Contact your administrator to grant access to other users.

### Q8: Can I duplicate a project?

**A:** Not directly, but you can create a new project and manually copy the design parameters.

### Q9: What is the maximum number of projects?

**A:** There's no hard limit. Storage costs scale with usage. Contact support if you need to archive old projects.

## Site & Environment

### Q10: How does site resolution work?

**A:** Enter the site address, and the system automatically:
- Geocodes the address (lat/lon)
- Fetches wind speed data (ASCE 7-16)
- Determines exposure category
- Calculates snow load

### Q11: What if geocoding fails?

**A:** The system will use default values with a warning. You can manually override wind speed and exposure if needed.

### Q12: Can I manually enter wind data?

**A:** Yes. After site resolution, you can edit the wind speed and exposure values manually.

### Q13: How accurate is the wind data?

**A:** Wind data comes from ASCE 7-16 maps (primary) or OpenWeatherMap (fallback). Accuracy depends on location, but typically within 5-10% of measured values.

## Cabinet Design

### Q14: How do I draw a cabinet on the canvas?

**A:** Click and drag on the canvas to create a rectangle. Drag corners to resize. The system automatically calculates area, weight, and center of gravity.

### Q15: Can I add multiple cabinets?

**A:** Yes. Click "Add Cabinet" to create multiple cabinets. The system calculates combined geometry.

### Q16: How often does the derive update?

**A:** The derive updates automatically after 300ms of inactivity (debounced) when you modify the canvas.

### Q17: What if the derive doesn't update?

**A:** Check your internet connection, verify inputs are valid, and refresh the page if needed. Contact support if the issue persists.

### Q18: What are the cabinet dimension limits?

**A:** 
- Width: 5-30 feet
- Height: 2-20 feet
- Depth: 6-24 inches

## Structural Design

### Q19: How does pole selection work?

**A:** The system automatically filters pole options based on:
- Load requirements (moment)
- Height constraints
- Material preferences
- Safety factor requirements

### Q20: What if no poles are found?

**A:** Check the assumptions for warnings. Common causes:
- Loads too high
- Height constraint too restrictive
- Material constraint

Adjust inputs or request engineering review.

### Q21: What is the recommended pole?

**A:** The system recommends the pole with the best combination of:
- Lowest weight
- Lowest cost
- Adequate safety factor

### Q22: Can I manually select a pole?

**A:** Yes. Review the options list and select any feasible pole.

## Foundation Design

### Q23: What's the difference between direct burial and baseplate?

**A:**
- **Direct Burial**: Footing buried in ground, no visible base
- **Baseplate**: Visible baseplate with anchors

Choose based on soil conditions and installation requirements.

### Q24: How is footing depth calculated?

**A:** The system uses ACI 318 design procedures with soil bearing capacity. Depth is calculated to satisfy:
- Overturning resistance
- Bearing capacity
- Sliding resistance
- Uplift resistance

### Q25: What if depth >5 feet?

**A:** Depths >5 feet require engineering review. The system will:
- Set confidence to 0.5
- Add warning: "Engineering review required"
- Flag for manual review

### Q26: What is concrete yardage based on?

**A:** Concrete yardage is calculated from:
- Footing diameter
- Minimum depth
- Number of poles

Formula: `π × (diameter/2)² × depth × num_poles / 27`

### Q27: What are baseplate checks?

**A:** Baseplate checks validate:
- Plate thickness (bending capacity)
- Weld strength
- Anchor tension capacity
- Anchor shear capacity

All checks must pass for approval.

### Q28: What if a check fails?

**A:** Review the failing check details:
- Utilization ratio
- Required vs. provided capacity
- Alternatives in trace data

Adjust design or request engineering review.

## Reports

### Q29: How do I generate a report?

**A:** Submit the project, and the report is automatically generated. Click "Download Report" when ready (typically 30-60 seconds).

### Q30: What's included in the report?

**A:** The PDF report includes:
- Page 1: Cover page (project info, site)
- Page 2: Elevation drawing
- Page 3: Design outputs (loads, foundation, safety factors)
- Page 4: General notes

### Q31: How long does report generation take?

**A:** Typically 30-60 seconds. If >5 minutes, check task status or contact support.

### Q32: Can I regenerate a report?

**A:** Yes. Reports are cached by content SHA256, so identical projects produce the same report instantly.

### Q33: What is the report format?

**A:** PDF format, 4 pages, optimized for printing.

## Confidence & Warnings

### Q34: What is a confidence score?

**A:** Confidence score (0.0-1.0) indicates how confident the system is in the calculation:
- 0.9-1.0: High (green) - Proceed normally
- 0.7-0.89: Medium (yellow) - Review assumptions
- 0.5-0.69: Low (orange) - Consider adjustments
- <0.5: Very Low (red) - Engineering review required

### Q35: What causes low confidence?

**A:** Common causes:
- Engineering review required (depth >5ft)
- Unusual configuration
- Warnings in assumptions
- Abstain conditions

### Q36: Should I proceed with low confidence?

**A:** Review the assumptions first. If confidence <0.5, request engineering review. Otherwise, proceed with caution.

### Q37: What are assumptions?

**A:** Assumptions are notes, warnings, or conditions in the calculation:
- Defaults used
- Warnings (e.g., "Pole height >40ft is uncommon")
- Review requirements
- Abstain conditions

## File Management

### Q38: What file types can I upload?

**A:** Supported types:
- PDF documents
- Images (JPG, PNG)
- DXF files (CAD)

Maximum size: 10MB per file.

### Q39: How do I upload a file?

**A:**
1. Click "Upload File"
2. Select file
3. System generates presigned URL
4. File uploads directly to storage
5. File attached to project

### Q40: What if upload fails?

**A:** Common causes:
- File too large (>10MB)
- Invalid file type
- Presigned URL expired

Reduce file size, verify file type, or request new URL.

### Q41: Are files secure?

**A:** Yes. Files are:
- Encrypted at rest
- Access-controlled
- SHA256 verified
- Stored in secure object storage

## Troubleshooting

### Q42: System is slow - what should I do?

**A:**
1. Check internet connection
2. Clear browser cache
3. Try different browser
4. Check system status page
5. Contact support if persists

### Q43: Getting errors - what's wrong?

**A:**
1. Review error message
2. Check assumptions/warnings
3. Verify inputs valid
4. Check system status
5. Contact support with error details

### Q44: Can't submit project - why?

**A:** Common causes:
- Missing required fields
- Low confidence (<0.5) requires review
- Network error

Review project completeness and try again.

### Q45: Report not generating - help?

**A:**
1. Wait 30-60 seconds (normal)
2. Check task status
3. Verify submission successful
4. Retry if failed
5. Contact support if >5 minutes

## Technical

### Q46: What is an Envelope response?

**A:** Envelope is the standardized API response format containing:
- Data (actual response)
- Assumptions (warnings)
- Confidence (0.0-1.0)
- Trace (complete audit trail)
- Content SHA256 (deterministic hash)

### Q47: What is content_sha256?

**A:** SHA256 hash of the response content (rounded, deterministic). Used for:
- Response caching
- Change detection
- Verification

### Q48: What is idempotency?

**A:** Idempotency ensures repeated requests have the same effect. Include `Idempotency-Key` header to prevent duplicate submissions.

### Q49: How do API keys work?

**A:** API keys authenticate API requests:
- Generate key in admin panel
- Include in header: `X-Apex-Key: your-key`
- Keys can be rotated or revoked

### Q50: What are rate limits?

**A:** Default limits:
- 100 requests/minute per user
- 10 requests/second burst

Rate limit headers included in responses.

---

**Can't find your answer?**
- Check [Troubleshooting Guide](../operations/troubleshooting.md)
- Review [API Reference](../api/api-reference.md)
- Contact support: support@example.com

