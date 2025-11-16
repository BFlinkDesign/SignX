# Eagle Workflow Hub - Project Instructions for Claude

## Project Overview
Eagle Workflow Hub is a comprehensive business automation system designed for Eagle Sign Co, focusing on streamlining the quote-to-production workflow. The system integrates multiple existing platforms without disrupting current operations.

## Core System Components

### Primary Integrations
- **KeyedIn**: ERP/CRM system (read-only integration)
- **Outlook**: Primary email client for bid requests
- **Network Paths**: 
  - `\\ES-FS02\users\brady\EagleHub` (main deployment)
  - `\\ES-FS02\customers2\` (customer data)
  - `\\Brady-Z4\DncFiles\` (CNC files)
- **Design Software**: CorelDRAW, BlueBeam
- **Data Management**: Excel work order tracking

## User Context & Requirements

### User Profile
- **Multi-role professional**: Estimator, Project Manager, Production Lead, Sales
- **Current workflow time**: 15-45 minutes per quote
- **Target workflow time**: 2-5 minutes per quote
- **Preferred browser**: Chrome
- **Working primarily from**: Outlook + network drives

### Key Pain Points Addressed
1. Manual data entry across 6+ systems
2. No historical pricing reference
3. Manual file organization
4. Inconsistent quote formatting
5. Time-consuming drawing measurements
6. No pattern learning for pricing

## Technical Architecture

### PowerShell Components
```powershell
# Main scripts structure:
- Eagle-Hub-2-Engine.ps1 (automation engine)
- Setup-Eagle-Hub-2.ps1 (installation)
- Eagle-PDF-Master.ps1 (PDF processing)
```

### HTML/JavaScript Dashboard
- Single-page application in Chrome
- Tab-based interface for different roles
- Real-time activity monitoring
- Settings management with auto-learning

### Data Processing Pipeline
1. Email monitoring → "BID REQUEST" detection
2. KeyedIn historical data extraction
3. File organization with naming conventions
4. Drawing analysis (scale detection, measurements)
5. Pricing calculation with confidence intervals
6. Professional bid document generation

## Response Guidelines for Claude

### Technical Responses Should:
1. **Prioritize PowerShell** for automation tasks
2. **Use network paths** (\\ES-FS02\...) not local C:\ for production
3. **Include error handling** with Try-Catch blocks
4. **Log everything** using Write-EagleLog function
5. **Respect existing systems** - integrate, don't replace

### Code Style Requirements
```powershell
# Always use this logging format:
Write-EagleLog "Message" "TYPE" "MODULE"
# Types: PROCESS, SUCCESS, ERROR, WARNING
# Modules: OUTLOOK, KEYEDIN, PDF, FILES, DRAWING
```

### File Naming Conventions
```
{CustomerName}_{ProjectType}_{Date}-{JobNumber}-{Version}.{ext}
Example: Valley_Church_Halo_0725-39657-00.pdf
```

### Integration Approach
- **Read-only** from KeyedIn (no modifications)
- **Monitor** Outlook without disrupting email flow
- **Organize** files without moving originals
- **Generate** new documents in designated folders
- **Learn** from patterns without hard-coding rules

## Key Features to Emphasize

### Automation Capabilities
- **Email Processing**: Auto-detect bid requests with customer extraction
- **Smart Scheduling**: 30-minute standard, hourly deep scans
- **Pattern Learning**: Adapts to user behavior over time
- **Multi-mode Operation**: Switch between roles seamlessly

### Pricing Intelligence
```
Historical Analysis → Confidence Intervals → Professional Quotes
Example: "Based on 47 similar jobs: $8,347 ± 5% confidence"
```

### Drawing Standards
- AIA-compliant scaling (1/8" = 1'-0", 1/4" = 1'-0")
- Automatic scale detection from PDF text
- CorelDRAW vector analysis
- BlueBeam raster processing

## Communication Style

### When Discussing Features:
- Use **visual indicators** (emojis) for status: ✅ 📊 🔄 ⚠️ 🚀
- Provide **before/after comparisons** to show value
- Include **confidence metrics** for data-driven decisions
- Show **time savings** in concrete terms

### Example Response Format:
```
📊 Current Analysis:
- Processing time: 35 minutes → 3 minutes
- Data points analyzed: 47 similar projects
- Confidence level: 92%
- Estimated savings: $2,340/month in labor

✅ Implementation ready!
```

## Critical Success Factors

### Must-Have Features:
1. **Zero disruption** to KeyedIn operations
2. **Chrome-based** dashboard interface
3. **Network storage** at \\ES-FS02\users\brady\EagleHub
4. **Scheduled tasks** (30 min + hourly options)
5. **Settings panel** for manual control

### Performance Metrics:
- Quote generation: < 5 minutes
- Email response: < 30 seconds
- File organization: Automatic
- Pricing accuracy: ± 5% target
- System uptime: 99%+

## Development Priorities

### Phase 1 (Immediate):
- Email monitoring for bid requests
- Basic KeyedIn data extraction
- File organization automation
- Simple pricing calculations

### Phase 2 (Enhancement):
- Historical pricing analysis
- Drawing measurement automation
- Confidence interval calculations
- Pattern learning algorithms

### Phase 3 (Optimization):
- Multi-role dashboard views
- Advanced reporting
- Customer relationship tracking
- Predictive pricing models

## Error Handling & Recovery

### Standard Error Response:
```powershell
try {
    # Operation
    Write-EagleLog "✅ Operation successful" "SUCCESS" "MODULE"
}
catch {
    Write-EagleLog "❌ Error: $($_.Exception.Message)" "ERROR" "MODULE"
    # Graceful recovery
    # User notification
    # Log to file
}
```

### Fallback Strategies:
- Manual override options for all automations
- Default pricing when historical data unavailable
- Local caching for network disruptions
- Email alerts for critical failures

## Testing & Validation

### Test Scenarios:
1. Process real KeyedIn PDF exports
2. Handle malformed email subjects
3. Detect various drawing scales
4. Calculate complex sign configurations
5. Generate professional bid documents

### Success Criteria:
- Correctly extracts job numbers (format: 209-0385)
- Identifies all major sign types
- Calculates square footage accurately
- Applies markup percentages correctly
- Generates PDF bids without errors

## User Training & Support

### Documentation Requirements:
- Quick start guide with screenshots
- Troubleshooting flowchart
- Settings configuration guide
- Role-specific tutorials

### Support Features:
- Real-time activity logs
- System health monitoring
- Connection status indicators
- Manual intervention options

## Future Enhancements

### Planned Features:
- Mobile dashboard access
- Voice command integration
- AI-powered price optimization
- Automated follow-up sequences
- Integration with accounting systems

### Scalability Considerations:
- Modular architecture for easy updates
- Database migration path for growth
- Multi-user support framework
- Cloud backup capabilities

## Important Notes

### Always Remember:
1. User works in **multi-hat** capacity - don't focus only on estimating
2. **Chrome** is the required browser
3. **30-minute** and **hourly** scheduling options are essential
4. **Pattern learning** should be automatic with manual override
5. **Server path** (\\ES-FS02\users\brady\EagleHub) is production location

### Never Forget:
- This augments, doesn't replace existing systems
- KeyedIn remains the source of truth
- Outlook is the primary communication tool
- User needs flexibility to adjust everything manually
- Focus on measurable time and cost savings

## Response Checklist

When providing solutions, ensure:
- [ ] PowerShell scripts include proper error handling
- [ ] Network paths used instead of local paths
- [ ] Chrome compatibility confirmed
- [ ] Settings are adjustable via UI
- [ ] Logging implemented throughout
- [ ] Integration respects existing workflows
- [ ] Time savings clearly quantified
- [ ] Confidence levels provided for estimates
- [ ] Multi-role functionality addressed
- [ ] Pattern learning capabilities included