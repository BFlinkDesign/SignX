# PDF Cost Summary Template Guide

This guide explains the expected PDF format for automatic cost extraction.

## Recommended PDF Template

For best extraction results, your PDF cost summaries should include these labeled fields:

### Project Information
```
Project #: ES-2024-1234
Project Name: Main Street Monument Sign
Customer: Acme Corporation
Job #: J-5678
Quote Date: 10/15/2024
Completion Date: 11/30/2024 (if available)
```

### Design Specifications
```
DESIGN SPECIFICATIONS
Total Height: 20 ft
Sign Area: 60 sq.ft
Sign Width: 10 ft (optional)
Sign Height: 6 ft (optional)
```

### Wind & Environmental Loads
```
WIND LOADS
Wind Speed: 115 mph
Exposure Category: C
Importance Factor: 1.0
Snow Load: 0 psf (optional)
```

### Structural Design
```
STRUCTURAL DESIGN
Pole Type: Round HSS
Pole Size: 8 inches
Steel Grade: A500B
Pole Wall Thickness: 0.25 in (optional)
Foundation: Direct Burial
Embedment Depth: 8 ft
Concrete: 10 CY
Soil Bearing: 3000 psf (optional)
```

### Cost Breakdown
```
COST BREAKDOWN
Material Cost: $5,250.00
Labor Cost: $3,800.00
Engineering Cost: $450.00
Permit Fees: $125.00
Markup: 15% (optional)

TOTAL COST: $9,625.00
```

### Optional Fields
```
ADDITIONAL INFORMATION
Location: Des Moines, IA 50309
PE Approved: Yes
PE Engineer: John Smith, PE
Bid Won: Yes (optional)
Actual Cost at Completion: $9,800.00 (optional)
```

## Extraction Pattern Customization

If your PDFs use different labels, update the regex patterns in `services/ml/pdf_extractor.py`:

```python
# Example: If you use "Job Number:" instead of "Job #:"
job_number = self._extract_field_regex(
    r"Job\s*Number\s*[:]?\s*([A-Z0-9-]+)",  # Update this pattern
    text
)
```

## Tips for Best Results

1. **Use consistent templates** - Same layout across all PDFs
2. **Clear labels** - Use "Material Cost:" not "Materials:"
3. **Standard units** - Always specify units (ft, sqft, mph, etc.)
4. **Decimal precision** - Include cents for costs ($1,234.56)
5. **Date formats** - Use MM/DD/YYYY or YYYY-MM-DD
6. **No scans** - PDFs should be text-based, not scanned images

## Handling Variations

If your PDFs vary, the extractor will:
- Use defaults for missing fields
- Log warnings for failed extractions
- Generate quality report showing issues

Review `reports/extraction_report.json` after extraction to see what worked and what needs adjustment.

## Example PDFs

Place sample PDFs in subdirectories:
```
data/pdfs/cost_summaries/
├── 2020/
│   ├── ES-2020-001.pdf
│   └── ES-2020-002.pdf
├── 2021/
│   └── ...
└── 2024/
    └── ...
```

The extraction script will recursively process all PDFs.

## Validation After Extraction

After running `scripts/extract_pdfs.py`, check:

1. **Extraction count**: Did most PDFs extract successfully?
2. **Completeness**: Is data >90% complete?
3. **Cost range**: Are min/max costs reasonable?
4. **Outliers**: Review flagged outliers for data entry errors
5. **Date range**: Covers multiple years for better training?

Target: 100+ successfully extracted projects for good model performance.

