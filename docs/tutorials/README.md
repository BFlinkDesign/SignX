# Video Tutorials

Links and scripts for SIGN X Studio Clone video tutorials.

## Available Tutorials

### 1. Project Creation to Submission (5min Walkthrough)

**Script:**

```
1. Open SIGN X Studio Clone (https://app.example.com)
2. Click "New Project"
3. Fill in:
   - Project Name: "Main Street Sign"
   - Customer: "Acme Corporation"
   - Site Address: "123 Main St, Dallas, TX"
4. Click "Next" → Stage 1 Complete

5. Stage 2: Site & Environment
   - System automatically resolves address
   - Shows: Wind speed 115 mph, Exposure C
   - Click "Next"

6. Stage 3: Cabinet Design
   - Draw cabinet on canvas: 14ft × 8ft
   - System derives: Area 112 sq ft, Weight 1120 lb
   - Shows confidence: 95% (green badge)
   - Click "Next"

7. Stage 4: Structural Design
   - System filters pole options
   - Shows recommended: 6x0.25 pipe
   - Click "Select" → "Next"

8. Stage 5: Foundation Design
   - Select direct burial
   - Diameter: 3.0 ft
   - System calculates: Depth 4.2 ft, 1.47 cu yd concrete
   - Click "Next"

9. Stage 6: Review
   - Review all selections
   - Confidence: 85%
   - Click "Submit"

10. Stage 7: Submission
    - Project status: "Submitted"
    - PDF report generating...
    - Download PDF when ready

Total time: ~5 minutes
```

**Screen Recording:**
- Resolution: 1920×1080
- Frame rate: 60fps
- Audio: Clear narration, no background noise
- Tools: OBS Studio or Loom

### 2. Canvas Derive Workflow (2min Demo)

**Script:**

```
1. Open project in cabinet design stage
2. Canvas shows current cabinet: 12ft × 6ft
3. Drag corner handle → Resize to 14ft × 8ft
4. System automatically:
   - POST /cabinets/derive (debounced 300ms)
   - Shows loading indicator
   - Updates form inputs:
     * Area: 112 sq ft
     * Weight: 1120 lb
   - Displays confidence: 95% (green)
5. If warning appears:
   - Snackbar: "Warning: Large cabinet may require additional support"
   - Confidence: 85% (yellow)
6. Adjust dimensions → System recalculates instantly
```

**Key Points:**
- Real-time updates (300ms debounce)
- Confidence indicators
- Warning handling

### 3. Report Interpretation Guide (3min)

**Script:**

```
1. Open generated PDF report
2. Page 1: Cover Page
   - Project name, site address
   - Coordinates, date
   - Standards pack SHA256

3. Page 2: Elevation Drawing
   - Support structure details
   - Foundation dimensions
   - Anchor pattern (if baseplate)

4. Page 3: Design Output
   - Wind loads table:
     * Basic wind speed: 115 mph
     * Wind force: 5000 lbf
     * Design pressure: 45.2 psf
   - Foundation design:
     * Concrete: 1.47 cu yd
     * Diameter: 36 in
     * Depth: 50.4 in
   - Safety factors:
     * Overturning: 2.1
     * Bearing: 2.5
     * Sliding: 2.3
     * Uplift: 2.0
     * Deflection: OK ✓

5. Page 4: General Notes
   - Design basis (ASCE 7-16, ACI 318)
   - Field verification requirements
   - Disclaimers
```

**Annotations:**
- Highlight key numbers
- Explain safety factors
- Point out important notes

## Recording Setup

### Tools

1. **OBS Studio** (Free, open-source)
   - Download: https://obsproject.com
   - Configuration:
     - Canvas: 1920×1080
     - Output: MP4, H.264, 60fps
     - Audio: 44.1kHz, 128kbps

2. **Loom** (Simple, cloud-hosted)
   - Browser extension
   - Automatic upload to cloud
   - Easy sharing

### Audio Setup

- Use external microphone
- Minimize background noise
- Speak clearly and at moderate pace
- Add captions for accessibility

### Post-Production

1. **Trim** unnecessary pauses
2. **Add captions** (YouTube auto-captions + manual review)
3. **Add annotations** (arrows, highlights)
4. **Export**:
   - Format: MP4 (H.264)
   - Resolution: 1920×1080
   - Bitrate: 5000 kbps

## Hosting

### YouTube

- Channel: SIGN X Studio
- Playlist: Tutorials
- Tags: #sign-design #engineering #tutorial

### Self-Hosted

- Store in MinIO: `tutorials/` bucket
- Serve via CDN
- Embed in documentation

---

**Video Links:**
- [Project Creation to Submission](https://youtube.com/watch?v=...) (Coming soon)
- [Canvas Derive Workflow](https://youtube.com/watch?v=...) (Coming soon)
- [Report Interpretation](https://youtube.com/watch?v=...) (Coming soon)

