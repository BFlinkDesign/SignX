# Eagle Sign Analyzer User Manual

**Version 1.0**

## Quick Start

1. **Launch**: Double-click Eagle Analyzer desktop icon
2. **Load**: Drag PDF work order into window
3. **Analyze**: Click "Analyze" button
4. **Review**: Check results and warnings
5. **Export**: Save as Excel or PDF

## Understanding Results

### Labor Estimates
```
Code   Description        Recommended  Confidence
0230   CHANNEL LETTERS    12.5 hrs     HIGH (30+ samples)
```

**Confidence Levels:**
- **HIGH**: 30+ historical samples
- **MEDIUM**: 10-30 samples  
- **LOW**: 5-10 samples
- **INSUFFICIENT**: <5 samples (use with caution)

### Risk Indicators
- ✅ **LOW**: Proceed with confidence
- ⚡ **MEDIUM**: Add 10-15% contingency
- ⚠️ **HIGH**: Add 20-25% contingency
- ❌ **CRITICAL**: Review manually

## Features

### Historical Learning
System improves accuracy by remembering past jobs. After 10+ similar jobs, predictions become highly reliable.

### Cost Calculation
Automatically calculates:
- Labor costs by department
- Material requirements
- Overhead allocation (15% default)
- Total job cost

### Workflow Validation
Checks for:
- Missing work steps
- Out-of-sequence operations
- Excessive overtime

## Common Work Orders

### Channel Letters (CLLIT)
Typical workflow:
1. Layout (0200)
2. Channel fabrication (0230)
3. Electrical (0340)
4. Paint (0420)
5. Faces (0260)
6. Install (0640)

### Monument Signs (MONDF)
Typical workflow:
1. Layout (0200)
2. Structural steel (0215)
3. Electrical (0340)
4. Paint (0420)
5. Faces (0260)
6. Footings (0605)
7. Install (0650)

## Troubleshooting

**PDF won't load**
- Ensure PDF is text-based, not scanned image
- Try "Save As" in Adobe to create clean version

**Low confidence warnings**
- Process more historical jobs to build data
- Verify estimates against recent similar jobs

**Missing work codes**
- Check PDF formatting
- Ensure standard Eagle work order format

## Best Practices

1. **Build History**: Process all historical PDFs first
2. **Regular Updates**: Add completed jobs weekly
3. **Verify Outliers**: Review any estimate >20% from typical
4. **Seasonal Adjustments**: System automatically applies monthly factors

## Settings

Access via File → Settings:
- **Minimum Bid**: 4 hours (default)
- **Confidence Level**: 90% (recommended)
- **Overhead Rate**: 15% (adjustable)

## Support

- **Logs**: Check eagle_production.log
- **Backup**: Historical data in eagle_production_history.json
- **Updates**: Check monthly for accuracy improvements