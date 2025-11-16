# User Training Guide

Complete training program for end users of SIGN X Studio Clone.

## Overview

**Total Duration**: 3 hours (5 modules)  
**Format**: Instructor-led with hands-on practice  
**Prerequisites**: Basic computer skills, sign design experience

## Module 1: System Overview and Navigation (30 minutes)

### Objectives

- Understand system purpose and capabilities
- Navigate the interface
- Access help and documentation

### Content

#### 1.1 System Introduction (10 min)

**What is SIGN X Studio?**
- Modern sign design and engineering platform
- Replaces legacy CalcuSign system
- Automated calculations with confidence scoring

**Key Benefits:**
- 94% time savings per project
- Instant geometry calculations
- Automated report generation
- Full audit trail

#### 1.2 Interface Tour (15 min)

**Navigation:**
- Project list view
- Stage stepper (8 stages)
- Canvas interface
- Form inputs
- Confidence badges

**Key Elements:**
- Green badge: High confidence (≥0.9)
- Yellow badge: Medium confidence (0.7-0.89)
- Orange badge: Low confidence (0.5-0.69)
- Red badge: Very low confidence (<0.5)

#### 1.3 Help and Support (5 min)

**Resources:**
- In-app help tooltips
- Documentation: https://docs.example.com
- Support email: support@example.com
- FAQ: https://docs.example.com/kb/faq

**Practice:**
- Navigate to help section
- Search documentation
- Submit support request

## Module 2: Project Creation and Stages 1-4 (45 minutes)

### Objectives

- Create new projects
- Complete stages 1-4
- Understand real-time derive
- Interpret confidence scores

### Content

#### 2.1 Creating a Project (10 min)

**Steps:**
1. Click "New Project"
2. Fill in:
   - Project Name
   - Customer
   - Site Address
3. Click "Create"

**Hands-On:**
- Create practice project
- Verify project appears in list

#### 2.2 Stage 1: Overview (5 min)

**Content:**
- Project metadata
- Customer information
- Initial status

**Practice:**
- Edit project name
- Add customer details

#### 2.3 Stage 2: Site & Environment (10 min)

**Site Resolution:**
- Enter address
- System automatically:
  - Geocodes address
  - Fetches wind data
  - Determines exposure

**Understanding Results:**
- Wind speed (mph)
- Snow load (psf)
- Exposure category (B, C, D)
- Confidence score

**Hands-On:**
- Enter address
- Verify wind data displayed
- Check confidence badge

#### 2.4 Stage 3: Cabinet Design (15 min)

**Interactive Canvas:**
- Draw cabinet dimensions
- System automatically derives:
  - Area (sq ft)
  - Weight (lb)
  - Center of gravity

**Real-Time Updates:**
- Changes to canvas → automatic calculation (300ms debounce)
- Form inputs update automatically
- Confidence badge updates

**Warnings:**
- If warning appears: Review assumptions
- Adjust dimensions if needed

**Hands-On:**
- Draw cabinet on canvas
- Resize and observe updates
- Review derived values
- Handle warnings (if any)

#### 2.5 Stage 4: Structural Design (5 min)

**Pole Selection:**
- System filters options based on loads
- Shows recommended selection
- Displays confidence score

**Understanding Options:**
- Family (pipe, tube, W-section)
- Designation (size)
- Weight, strength properties
- Cost (if available)

**Hands-On:**
- Review pole options
- Select recommended pole
- Understand filtering

## Module 3: Foundation Design Stages 5-7 (45 minutes)

### Objectives

- Complete foundation design
- Understand design checks
- Interpret safety factors
- Handle engineering reviews

### Content

#### 3.1 Stage 5: Foundation Type Selection (5 min)

**Options:**
- Direct Burial
- Baseplate

**Decision Factors:**
- Soil conditions
- Installation method
- Cost considerations

#### 3.2 Stage 6: Direct Burial Design (20 min)

**Design Process:**
1. Enter footing diameter
2. System calculates required depth
3. Shows concrete yardage
4. Displays safety factors

**Understanding Outputs:**
- Minimum depth (ft/in)
- Concrete volume (cu yd)
- Monotonic validation (diameter↓ ⇒ depth↑)

**Engineering Review Trigger:**
- Depth >5ft: Review required
- Confidence drops to 0.5
- Warning appears

**Hands-On:**
- Enter diameter
- Observe depth calculation
- Adjust diameter, see depth change
- Handle engineering review flag

#### 3.3 Stage 7: Baseplate Design (20 min)

**Design Checks:**
- Plate thickness
- Weld strength
- Anchor tension
- Anchor shear

**Understanding Results:**
- All checks must pass for approval
- Utilization ratios shown
- Confidence based on check results

**If Checks Fail:**
- Review failing checks
- Adjust design parameters
- Request engineering review if needed

**Hands-On:**
- Enter baseplate dimensions
- Review check results
- Handle failing checks (if any)
- Request engineering review

## Module 4: Review, Submission, and Reports (30 minutes)

### Objectives

- Review complete design
- Submit project
- Generate and download reports
- Understand submission workflow

### Content

#### 4.1 Stage 8: Review (10 min)

**Review Checklist:**
- [ ] All stages complete
- [ ] Confidence score acceptable (>0.7)
- [ ] No critical warnings
- [ ] Design parameters verified
- [ ] Cost estimate reviewed

**Understanding Confidence:**
- High (≥0.9): Proceed normally
- Medium (0.7-0.89): Review assumptions
- Low (<0.7): Consider adjustments or engineering review

**Hands-On:**
- Review complete project
- Check confidence score
- Review assumptions/warnings

#### 4.2 Submission (10 min)

**Submission Process:**
1. Click "Submit Project"
2. Confirm submission (if confidence <0.8)
3. Wait for submission confirmation
4. Receive project number

**Idempotency:**
- Same submission won't create duplicate
- Safe to retry if network fails

**What Happens:**
- Project status: `estimating` → `submitted`
- PM system notified
- Email sent (if configured)
- PDF report generation queued

**Hands-On:**
- Submit practice project
- Verify submission confirmation
- Check project status updated

#### 4.3 Report Generation (10 min)

**Report Generation:**
- Automatic after submission
- Async task (may take 30 seconds)
- Cached by content SHA256

**Downloading Report:**
1. Click "Download Report"
2. Wait for generation (progress shown)
3. Download PDF when ready

**Report Contents:**
- Page 1: Cover page (project info)
- Page 2: Elevation drawing
- Page 3: Design outputs (loads, foundation, safety factors)
- Page 4: General notes

**Hands-On:**
- Generate report
- Download PDF
- Review report contents

## Module 5: Advanced Features and Troubleshooting (30 minutes)

### Objectives

- Use advanced features
- Troubleshoot common issues
- Access support resources

### Content

#### 5.1 Advanced Features (15 min)

**Multi-Cabinet Design:**
- Add multiple cabinets
- System calculates combined geometry
- Weight distribution shown

**What-If Analysis:**
- Adjust wind speed slider
- See pole height update
- Real-time recalculation

**File Uploads:**
- Upload drawings/PDFs
- Attach to project
- SHA256 verification

**Timeline View:**
- View project events
- Audit trail
- Status changes

**Hands-On:**
- Add multiple cabinets
- Use what-if sliders
- Upload a file
- View project timeline

#### 5.2 Troubleshooting (10 min)

**Common Issues:**

1. **Low Confidence Score**
   - Review assumptions
   - Check warnings
   - Adjust inputs

2. **Derive Not Updating**
   - Check internet connection
   - Verify inputs valid
   - Refresh page if needed

3. **Report Not Generating**
   - Check submission status
   - Wait 30-60 seconds
   - Contact support if >5 minutes

4. **Upload Failed**
   - Check file size (<10MB)
   - Verify file type (PDF, images)
   - Retry upload

**Support Resources:**
- Troubleshooting guide: https://docs.example.com/operations/troubleshooting
- FAQ: https://docs.example.com/kb/faq
- Support email: support@example.com

#### 5.3 Best Practices (5 min)

**Project Organization:**
- Use consistent naming: "Customer - Location - Date"
- Add customer in project metadata
- Include site address

**Data Entry:**
- Verify inputs before proceeding
- Review warnings/assumptions
- Check confidence scores

**Review Process:**
- Complete all stages before submission
- Review assumptions for low confidence
- Request engineering review if needed

**Performance:**
- Use cached responses when possible
- Batch similar projects
- Clear browser cache if issues

## Training Materials

### Practice Exercises

**Exercise 1: Basic Project**
- Create project: "Training - Main St - 2025"
- Complete all 8 stages
- Submit project
- Generate report

**Exercise 2: Multi-Cabinet**
- Create project with 2 cabinets
- Verify combined geometry
- Submit and review

**Exercise 3: Engineering Review**
- Create project with depth >5ft
- Trigger engineering review
- Request review
- Understand process

### Quiz Questions

1. What does a green confidence badge indicate?
2. How often does the canvas derive update?
3. What triggers an engineering review?
4. How do you download a report?
5. What should you do if confidence is <0.5?

### Video Resources

- [Module 1: Overview](https://youtube.com/watch?v=...) (10 min)
- [Module 2: Project Creation](https://youtube.com/watch?v=...) (15 min)
- [Module 3: Foundation Design](https://youtube.com/watch?v=...) (15 min)
- [Module 4: Submission](https://youtube.com/watch?v=...) (10 min)
- [Module 5: Advanced Features](https://youtube.com/watch?v=...) (10 min)

## Certification

### Training Completion Criteria

- [ ] Complete all 5 modules
- [ ] Pass quiz (80%+ score)
- [ ] Complete 3 practice exercises
- [ ] Submit training project successfully

### Post-Training Support

- **Week 1**: Daily check-ins
- **Week 2-4**: Weekly office hours
- **Ongoing**: Documentation and FAQs

---

**Next Steps:**
- [**Admin Training Guide**](admin-training-guide.md)
- [**Developer Onboarding**](developer-onboarding.md)

